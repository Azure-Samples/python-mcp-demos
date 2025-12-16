"""Run with: cd servers && uvicorn auth_mcp:app --host 0.0.0.0 --port 8000"""

import base64
import json
import logging
import os
import uuid
from datetime import date
from enum import Enum
from typing import Annotated

import logfire
from azure.core.settings import settings
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from cosmosdb_store import CosmosDBStore
from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from fastmcp.server.auth.providers.azure import AzureProvider
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import Middleware, MiddlewareContext
from key_value.aio.stores.memory import MemoryStore
from keycloak_provider import KeycloakAuthProvider
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from rich.console import Console
from rich.logging import RichHandler
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from opentelemetry_middleware import OpenTelemetryMiddleware

RUNNING_IN_PRODUCTION = os.getenv("RUNNING_IN_PRODUCTION", "false").lower() == "true"

if not RUNNING_IN_PRODUCTION:
    load_dotenv(override=True)

logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    handlers=[
        RichHandler(
            console=Console(stderr=True),
            show_path=False,
            show_level=False,
            rich_tracebacks=True,
        )
    ],
)
logger = logging.getLogger("ExpensesMCP")
logger.setLevel(logging.INFO)

# Configure Azure SDK OpenTelemetry to use OTEL
settings.tracing_implementation = "opentelemetry"

# Configure OpenTelemetry exporters (App Insights or Logfire)
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    logger.info("Setting up Azure Monitor instrumentation")
    configure_azure_monitor()
elif os.getenv("LOGFIRE_PROJECT_NAME"):
    logger.info("Setting up Logfire instrumentation")
    logfire.configure(service_name="expenses-mcp", send_to_logfire=True)

# Configure Cosmos DB client
if RUNNING_IN_PRODUCTION:
    azure_credential = ManagedIdentityCredential(client_id=os.environ["AZURE_CLIENT_ID"])
    logger.info("Using Managed Identity Credential for Azure authentication")
else:
    azure_credential = DefaultAzureCredential()
    logger.info("Using Default Azure Credential for Azure authentication")
cosmos_client = CosmosClient(
    url=f"https://{os.environ['AZURE_COSMOSDB_ACCOUNT']}.documents.azure.com:443/",
    credential=azure_credential,
)
cosmos_db = cosmos_client.get_database_client(os.environ["AZURE_COSMOSDB_DATABASE"])
cosmos_container = cosmos_db.get_container_client(os.environ["AZURE_COSMOSDB_USER_CONTAINER"])

# Configure authentication provider
auth = None
mcp_auth_provider = os.getenv("MCP_AUTH_PROVIDER", "none").lower()
if mcp_auth_provider == "entra_proxy":
    # Azure/Entra ID authentication using AzureProvider
    # When running locally, always use localhost for base URL (OAuth redirects need to match)
    oauth_client_store = None
    if RUNNING_IN_PRODUCTION:
        oauth_container = cosmos_db.get_container_client(os.environ["AZURE_COSMOSDB_OAUTH_CONTAINER"])
        oauth_client_store = CosmosDBStore(container=oauth_container, default_collection="oauth-clients")
        entra_base_url = os.environ["ENTRA_PROXY_MCP_SERVER_BASE_URL"]
    else:
        oauth_client_store = MemoryStore()
        entra_base_url = "http://localhost:8000"
    auth = AzureProvider(
        client_id=os.environ["ENTRA_PROXY_AZURE_CLIENT_ID"],
        client_secret=os.environ["ENTRA_PROXY_AZURE_CLIENT_SECRET"],
        tenant_id=os.environ["AZURE_TENANT_ID"],
        base_url=entra_base_url,
        required_scopes=["mcp-access"],
        client_storage=oauth_client_store,
    )
    logger.info(
        "Using Entra OAuth Proxy for server %s and %s storage", entra_base_url, type(oauth_client_store).__name__
    )
elif mcp_auth_provider == "keycloak":
    # Keycloak authentication using KeycloakAuthProvider with DCR support
    # This enables VS Code and other MCP clients to dynamically register and authenticate
    KEYCLOAK_REALM_URL = os.environ["KEYCLOAK_REALM_URL"]
    KEYCLOAK_TOKEN_ISSUER = os.getenv("KEYCLOAK_TOKEN_ISSUER", KEYCLOAK_REALM_URL)
    # Use KEYCLOAK_MCP_SERVER_BASE_URL if provided, otherwise default based on environment
    keycloak_base_url = os.getenv("KEYCLOAK_MCP_SERVER_BASE_URL")
    if not keycloak_base_url:
        keycloak_base_url = "http://localhost:8000" if not RUNNING_IN_PRODUCTION else None
    if not keycloak_base_url:
        raise ValueError("KEYCLOAK_MCP_SERVER_BASE_URL must be set in production")
    auth = KeycloakAuthProvider(
        realm_url=KEYCLOAK_REALM_URL,
        base_url=keycloak_base_url,
        required_scopes=[],
        # Audience should match the value in Keycloak's mcp:tools scope
        # Default to the base_url for local dev
        audience=None,
    )
    logger.info("Using Keycloak DCR auth for server %s and realm %s", keycloak_base_url, KEYCLOAK_REALM_URL)
else:
    logger.error("No authentication configured for MCP server, exiting.")
    raise SystemExit(1)


# Middleware to populate user_id in per-request context state
class UserAuthMiddleware(Middleware):
    def _get_user_id(self):
        token = get_access_token()
        if not (token and hasattr(token, "claims")):
            return None
        # Return 'oid' claim if present (for Entra), otherwise fallback to 'sub' (for KeyCloak)
        return token.claims.get("oid", token.claims.get("sub"))

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        user_id = self._get_user_id()
        if context.fastmcp_context is not None:
            context.fastmcp_context.set_state("user_id", user_id)
        return await call_next(context)

    async def on_read_resource(self, context: MiddlewareContext, call_next):
        user_id = self._get_user_id()
        if context.fastmcp_context is not None:
            context.fastmcp_context.set_state("user_id", user_id)
        return await call_next(context)


# Create the MCP server
mcp = FastMCP("Expenses Tracker", auth=auth, middleware=[OpenTelemetryMiddleware("ExpensesMCP"), UserAuthMiddleware()])

"""Expense tracking MCP server with authentication and Cosmos DB storage."""


class PaymentMethod(Enum):
    AMEX = "amex"
    VISA = "visa"
    CASH = "cash"


class Category(Enum):
    FOOD = "food"
    TRANSPORT = "transport"
    ENTERTAINMENT = "entertainment"
    SHOPPING = "shopping"
    GADGET = "gadget"
    OTHER = "other"


@mcp.tool
async def add_user_expense(
    date: Annotated[date, "Date of the expense in YYYY-MM-DD format"],
    amount: Annotated[float, "Positive numeric amount of the expense"],
    category: Annotated[Category, "Category label"],
    description: Annotated[str, "Human-readable description of the expense"],
    payment_method: Annotated[PaymentMethod, "Payment method used"],
    ctx: Context,
):
    """Add a new expense to Cosmos DB."""
    if amount <= 0:
        return "Error: Amount must be positive"

    date_iso = date.isoformat()
    logger.info(f"Adding expense: ${amount} for {description} on {date_iso}")

    try:
        # Read user_id stored by middleware
        user_id = ctx.get_state("user_id")
        if not user_id:
            return "Error: Authentication required (no user_id present)"
        expense_id = str(uuid.uuid4())
        expense_item = {
            "id": expense_id,
            "user_id": user_id,
            "date": date_iso,
            "amount": amount,
            "category": category.value,
            "description": description,
            "payment_method": payment_method.value,
        }
        await cosmos_container.create_item(body=expense_item)
        return f"Successfully added expense: ${amount} for {description} on {date_iso}"

    except Exception as e:
        logger.error(f"Error adding expense: {str(e)}")
        return f"Error: Unable to add expense - {str(e)}"


@mcp.tool
async def get_user_expenses(ctx: Context):
    """Get the authenticated user's expense data from Cosmos DB."""

    try:
        user_id = ctx.get_state("user_id")
        if not user_id:
            return "Error: Authentication required (no user_id present)"
        query = "SELECT * FROM c WHERE c.user_id = @uid ORDER BY c.date DESC"
        parameters = [{"name": "@uid", "value": user_id}]
        expenses_data = []

        async for item in cosmos_container.query_items(query=query, parameters=parameters, partition_key=user_id):
            expenses_data.append(item)

        if not expenses_data:
            return "No expenses found."

        csv_content = f"Expense data ({len(expenses_data)} entries):\n\n"
        for expense in expenses_data:
            csv_content += (
                f"Date: {expense.get('date', 'N/A')}, "
                f"Amount: ${expense.get('amount', 0)}, "
                f"Category: {expense.get('category', 'N/A')}, "
                f"Description: {expense.get('description', 'N/A')}, "
                f"Payment: {expense.get('payment_method', 'N/A')}\n"
            )

        return csv_content

    except Exception as e:
        logger.error(f"Error reading expenses: {str(e)}")
        return f"Error: Unable to retrieve expense data - {str(e)}"


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request):
    """Health check endpoint for service availability."""
    return JSONResponse({"status": "healthy", "service": "mcp-server"})


# Debug middleware to log token claims before auth
class TokenDebugMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                parts = token.split(".")
                payload = parts[1]
                payload += "=" * (4 - len(payload) % 4)
                claims = json.loads(base64.urlsafe_b64decode(payload))
                logger.info("=== TOKEN DEBUG ===")
                logger.info(f"ALL CLAIMS: {claims}")
                logger.info("===================")
            except Exception as e:
                logger.error(f"Token decode error: {e}")
        return await call_next(request)


# Configure Starlette middleware for OpenTelemetry
# We must do this *after* defining all the MCP server routes
app = mcp.http_app()
app.add_middleware(TokenDebugMiddleware)
StarletteInstrumentor.instrument_app(app)
