import logging
import os
import uuid
from datetime import date
from enum import Enum
from typing import Annotated

from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential, ManagedIdentityCredential
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger("ExpensesMCP")


def require_env_var(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        logger.error(f"Missing required environment variable: {name}")
        exit(1)
    return value


# Cosmos DB configuration from environment variables
AZURE_COSMOSDB_ACCOUNT = require_env_var("AZURE_COSMOSDB_ACCOUNT")
AZURE_COSMOSDB_DATABASE = require_env_var("AZURE_COSMOSDB_DATABASE")
AZURE_COSMOSDB_CONTAINER = require_env_var("AZURE_COSMOSDB_CONTAINER")
RUNNING_IN_PRODUCTION = os.getenv("RUNNING_IN_PRODUCTION", "false").lower() == "true"
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")

# Keycloak authentication configuration
KEYCLOAK_REALM_URL = require_env_var(
    "KEYCLOAK_REALM_URL"
)  # e.g., https://routeconfig.<env>.azurecontainerapps.io/auth/realms/mcp
MCP_SERVER_BASE_URL = require_env_var("MCP_SERVER_BASE_URL")  # e.g., https://routeconfig.<env>.azurecontainerapps.io
MCP_SERVER_AUDIENCE = os.getenv("MCP_SERVER_AUDIENCE", "mcp-server")

# Configure Keycloak JWT verification
token_verifier = JWTVerifier(
    jwks_uri=f"{KEYCLOAK_REALM_URL}/protocol/openid-connect/certs",
    issuer=KEYCLOAK_REALM_URL,
    audience=MCP_SERVER_AUDIENCE,
)

# Configure RemoteAuthProvider for DCR support
auth = RemoteAuthProvider(
    token_verifier=token_verifier,
    authorization_servers=[AnyHttpUrl(KEYCLOAK_REALM_URL)],
    base_url=MCP_SERVER_BASE_URL,
)
logger.info(f"Keycloak auth configured: realm={KEYCLOAK_REALM_URL}, audience={MCP_SERVER_AUDIENCE}")

# Configure Cosmos DB client and container
if RUNNING_IN_PRODUCTION and AZURE_CLIENT_ID:
    credential = ManagedIdentityCredential(client_id=AZURE_CLIENT_ID)
else:
    credential = DefaultAzureCredential()

cosmos_client = CosmosClient(
    url=f"https://{AZURE_COSMOSDB_ACCOUNT}.documents.azure.com:443/",
    credential=credential,
)
cosmos_db = cosmos_client.get_database_client(AZURE_COSMOSDB_DATABASE)
cosmos_container = cosmos_db.get_container_client(AZURE_COSMOSDB_CONTAINER)
logger.info(f"Connected to Cosmos DB: {AZURE_COSMOSDB_ACCOUNT}")

mcp = FastMCP("Expenses Tracker", auth=auth)


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
async def add_expense(
    date: Annotated[date, "Date of the expense in YYYY-MM-DD format"],
    amount: Annotated[float, "Positive numeric amount of the expense"],
    category: Annotated[Category, "Category label"],
    description: Annotated[str, "Human-readable description of the expense"],
    payment_method: Annotated[PaymentMethod, "Payment method used"],
):
    """Add a new expense to Cosmos DB."""
    if amount <= 0:
        return "Error: Amount must be positive"

    date_iso = date.isoformat()
    logger.info(f"Adding expense: ${amount} for {description} on {date_iso}")

    try:
        expense_id = str(uuid.uuid4())
        expense_item = {
            "id": expense_id,
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


@mcp.resource("resource://expenses")
async def get_expenses_data():
    """Get raw expense data from Cosmos DB."""
    logger.info("Expenses data accessed")

    try:
        query = "SELECT * FROM c ORDER BY c.date DESC"
        expenses_data = []

        async for item in cosmos_container.query_items(query=query, enable_cross_partition_query=True):
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


@mcp.prompt
def analyze_spending_prompt(
    category: str | None = None, start_date: str | None = None, end_date: str | None = None
) -> str:
    """Generate a prompt to analyze spending patterns with optional filters."""

    filters = []
    if category:
        filters.append(f"Category: {category}")
    if start_date:
        filters.append(f"From: {start_date}")
    if end_date:
        filters.append(f"To: {end_date}")

    filter_text = f" ({', '.join(filters)})" if filters else ""

    return f"""
    Please analyze my spending patterns{filter_text} and provide:

    1. Total spending breakdown by category
    2. Average daily/weekly spending
    3. Most expensive single transaction
    4. Payment method distribution
    5. Spending trends or unusual patterns
    6. Recommendations for budget optimization

    Use the expense data to generate actionable insights.
    """


# ASGI application for uvicorn
http_app = mcp.http_app()


# Wrapper ASGI app to add health endpoint for Container Apps probes
async def app(scope, receive, send):
    if scope["type"] == "http" and scope["path"] == "/health":
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [[b"content-type", b"application/json"]],
        })
        await send({
            "type": "http.response.body",
            "body": b'{"status": "healthy"}',
        })
        return
    await http_app(scope, receive, send)


if __name__ == "__main__":
    logger.info("MCP Expenses server starting (HTTP mode on port 8000)")
    mcp.run(transport="http", host="0.0.0.0", port=8000)
