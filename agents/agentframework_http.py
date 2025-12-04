from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

import httpx
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from rich import print
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("agentframework_mcp_http")

# Load environment variables
load_dotenv(override=True)

# Constants
RUNNING_IN_PRODUCTION = os.getenv("RUNNING_IN_PRODUCTION", "false").lower() == "true"
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp/")

# Optional: Keycloak authentication (set KEYCLOAK_REALM_URL to enable)
KEYCLOAK_REALM_URL = os.getenv("KEYCLOAK_REALM_URL")

# Configure chat client based on API_HOST
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    client = AzureOpenAIChatClient(
        credential=DefaultAzureCredential(),
        deployment_name=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        api_version=os.environ.get("AZURE_OPENAI_VERSION"),
    )
elif API_HOST == "github":
    client = OpenAIChatClient(
        base_url="https://models.github.ai/inference",
        api_key=os.environ["GITHUB_TOKEN"],
        model_id=os.getenv("GITHUB_MODEL", "openai/gpt-4o"),
    )
elif API_HOST == "ollama":
    client = OpenAIChatClient(
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key="none",
        model_id=os.environ.get("OLLAMA_MODEL", "llama3.1:latest"),
    )
else:
    client = OpenAIChatClient(
        api_key=os.environ.get("OPENAI_API_KEY"), model_id=os.environ.get("OPENAI_MODEL", "gpt-4o")
    )


# --- Keycloak Authentication Helpers (only used if KEYCLOAK_REALM_URL is set) ---


async def register_client_via_dcr() -> tuple[str, str]:
    """Register a new client dynamically using Keycloak's DCR endpoint."""
    dcr_url = f"{KEYCLOAK_REALM_URL}/clients-registrations/openid-connect"
    logger.info("📝 Registering client via DCR...")

    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            dcr_url,
            json={
                "client_name": f"agent-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "grant_types": ["client_credentials"],
                "token_endpoint_auth_method": "client_secret_basic",
            },
            headers={"Content-Type": "application/json"},
        )
        if response.status_code not in (200, 201):
            raise RuntimeError(f"DCR registration failed: {response.status_code} - {response.text}")

        data = response.json()
        logger.info(f"✅ Registered client: {data['client_id'][:20]}...")
        return data["client_id"], data["client_secret"]


async def get_keycloak_token(client_id: str, client_secret: str) -> str:
    """Get an access token from Keycloak using client_credentials grant."""
    token_url = f"{KEYCLOAK_REALM_URL}/protocol/openid-connect/token"
    logger.info("🔑 Getting access token from Keycloak...")

    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if response.status_code != 200:
            raise RuntimeError(f"Token request failed: {response.status_code} - {response.text}")

        token_data = response.json()
        logger.info(f"✅ Got access token (expires in {token_data.get('expires_in', '?')}s)")
        return token_data["access_token"]


async def get_auth_headers() -> dict[str, str] | None:
    """Get authorization headers if Keycloak is configured, otherwise return None."""
    if not KEYCLOAK_REALM_URL:
        return None

    client_id, client_secret = await register_client_via_dcr()
    access_token = await get_keycloak_token(client_id, client_secret)
    return {"Authorization": f"Bearer {access_token}"}


# --- Main Agent Logic ---


async def http_mcp_example() -> None:
    """
    Demonstrate MCP integration with the Expenses MCP server.

    If KEYCLOAK_REALM_URL is set, authenticates via OAuth (DCR + client credentials).
    Otherwise, connects without authentication.
    """
    # Get auth headers if Keycloak is configured
    headers = await get_auth_headers()
    if headers:
        logger.info(f"🔐 Auth enabled - connecting to {MCP_SERVER_URL} with Bearer token")
    else:
        logger.info(f"📡 No auth - connecting to {MCP_SERVER_URL}")

    async with (
        MCPStreamableHTTPTool(name="Expenses MCP Server", url=MCP_SERVER_URL, headers=headers) as mcp_server,
        ChatAgent(
            chat_client=client,
            name="Expenses Agent",
            instructions="You help users to log expenses.",
        ) as agent,
    ):
        today = datetime.now().strftime("%Y-%m-%d")
        user_query = "yesterday I bought a laptop for $1200 using my visa."
        result = await agent.run(f"Today's date is {today}. {user_query}", tools=mcp_server)
        print(result)

        # Keep the worker alive in production
        while RUNNING_IN_PRODUCTION:
            await asyncio.sleep(60)
            logger.info("Worker still running...")


if __name__ == "__main__":
    asyncio.run(http_mcp_example())
