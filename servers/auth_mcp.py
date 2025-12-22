"""Run with: cd servers && uvicorn auth_mcp:app --host 0.0.0.0 --port 8000"""

import logging
import os
import uuid
from datetime import date
from enum import Enum
from typing import Annotated

import httpx
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
from msal import ConfidentialClientApplication, TokenCache
from opentelemetry.instrumentation.starlette import StarletteInstrumentor
from rich.console import Console
from rich.logging import RichHandler
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

# Configure OpenTelemetry exporters based on OPENTELEMETRY_PLATFORM env var
opentelemetry_platform = os.getenv("OPENTELEMETRY_PLATFORM", "none").lower()
if opentelemetry_platform == "appinsights" and os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    logger.info("Setting up Azure Monitor instrumentation")
    configure_azure_monitor()
elif opentelemetry_platform == "logfire" and os.getenv("LOGFIRE_TOKEN"):
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
    KEYCLOAK_REALM_URL = os.environ["KEYCLOAK_REALM_URL"]
    if RUNNING_IN_PRODUCTION:
        keycloak_base_url = os.environ["KEYCLOAK_MCP_SERVER_BASE_URL"]
    else:
        keycloak_base_url = "http://localhost:8000"

    keycloak_audience = os.getenv("KEYCLOAK_MCP_SERVER_AUDIENCE") or "mcp-server"

    auth = KeycloakAuthProvider(
        realm_url=KEYCLOAK_REALM_URL,
        base_url=keycloak_base_url,
        required_scopes=["openid", "mcp:access"],
        audience=keycloak_audience,
    )
    logger.info(
        "Using Keycloak DCR auth for server %s and realm %s (audience=%s)",
        keycloak_base_url,
        KEYCLOAK_REALM_URL,
        keycloak_audience,
    )
else:
    logger.error("No authentication configured for MCP server, exiting.")
    raise SystemExit(1)

confidential_client = ConfidentialClientApplication(
    client_id=os.environ["ENTRA_PROXY_AZURE_CLIENT_ID"],
    client_credential=os.environ["ENTRA_PROXY_AZURE_CLIENT_SECRET"],
    authority=f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}",
    token_cache=TokenCache(),
)


async def check_user_in_group(graph_token: str, group_id: str) -> bool:
    """Check if the authenticated user is a member of the specified group (including transitive membership)."""
    async with httpx.AsyncClient() as client:
        url = (
            "https://graph.microsoft.com/v1.0/me/transitiveMemberOf/microsoft.graph.group"
            f"?$filter=id eq '{group_id}'&$count=true"
        )
        response = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {graph_token}",
                "ConsistencyLevel": "eventual",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("@odata.count", 0) > 0


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

        expense_summary = f"Expense data ({len(expenses_data)} entries):\n\n"
        for expense in expenses_data:
            expense_summary += (
                f"Date: {expense.get('date', 'N/A')}, "
                f"Amount: ${expense.get('amount', 0)}, "
                f"Category: {expense.get('category', 'N/A')}, "
                f"Description: {expense.get('description', 'N/A')}, "
                f"Payment: {expense.get('payment_method', 'N/A')}\n"
            )

        return expense_summary

    except Exception as e:
        logger.error(f"Error reading expenses: {str(e)}")
        return f"Error: Unable to retrieve expense data - {str(e)}"


@mcp.tool
async def get_expense_stats(ctx: Context):
    """Get a statistical summary of expenses (count per category) for all users.
    Only accessible to users in the authorized admin group.
    """
    access_token = get_access_token()
    if not access_token:
        return "Error: Authentication required"

    auth_token = access_token.token
    try:
        graph_resource_access_token = confidential_client.acquire_token_on_behalf_of(
            user_assertion=auth_token, scopes=["https://graph.microsoft.com/.default"]
        )
        if "error" in graph_resource_access_token:
            return "Error: Unable to obtain Graph API access token for authorization check"

        graph_auth_token = graph_resource_access_token["access_token"]

        # Check for the specific admin group ID using transitive membership
        admin_group_id = os.environ.get("ENTRA_ADMIN_GROUP_ID", "")
        if not admin_group_id:
            return "Error: Admin group ID not configured. Set ENTRA_ADMIN_GROUP_ID environment variable."
        is_admin = await check_user_in_group(graph_auth_token, admin_group_id)

        if not is_admin:
            return "Error: Unauthorized. You do not have permission to access expense statistics."

        # Query Cosmos DB for stats across all users
        # We fetch categories and aggregate in Python to avoid cross-partition GROUP BY limitations
        query = "SELECT c.category FROM c"
        stats = {}
        async for item in cosmos_container.query_items(query=query):
            category = item.get("category", "Unknown")
            stats[category] = stats.get(category, 0) + 1

        if not stats:
            return "No expense data found to summarize."

        summary = "Expense Statistics (Count per Category):\n"
        for category, count in stats.items():
            summary += f"- Category {category}: {count} expenses\n"

        return summary

    except Exception as e:
        logger.error(f"Error retrieving expense stats: {str(e)}")
        return f"Error: Unable to retrieve expense statistics - {str(e)}"


@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request):
    """Health check endpoint for service availability."""
    return JSONResponse({"status": "healthy", "service": "mcp-server"})


# Configure Starlette middleware for OpenTelemetry
# We must do this *after* defining all the MCP server routes
app = mcp.http_app()
StarletteInstrumentor.instrument_app(app)
