from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime

from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from rich import print
from rich.logging import RichHandler

try:
    from keycloak_auth import get_auth_headers
except ImportError:
    from agents.keycloak_auth import get_auth_headers

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("agentframework_mcp_http")

# Configure constants and client based on environment
RUNNING_IN_PRODUCTION = os.getenv("RUNNING_IN_PRODUCTION", "false").lower() == "true"

if not RUNNING_IN_PRODUCTION:
    load_dotenv(override=True)

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp/")

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

# Optional: Keycloak authentication (set KEYCLOAK_REALM_URL to enable)
KEYCLOAK_REALM_URL = os.getenv("KEYCLOAK_REALM_URL")


# --- Main Agent Logic ---


async def http_mcp_example() -> None:
    """
    Demonstrate MCP integration with the Expenses MCP server.

    If KEYCLOAK_REALM_URL is set, authenticates via OAuth (DCR + client credentials).
    Otherwise, connects without authentication.
    """
    # Get auth headers if Keycloak is configured
    headers = await get_auth_headers(KEYCLOAK_REALM_URL, client_name_prefix="agentframework")
    if headers:
        logger.info(f"🔐 Auth enabled - connecting to {MCP_SERVER_URL} with Bearer token")
    else:
        logger.info(f"📡 No auth - connecting to {MCP_SERVER_URL}")

    async with (
        MCPStreamableHTTPTool(name="Expenses MCP Server", url=MCP_SERVER_URL, headers=headers) as mcp_server,
        ChatAgent(
            chat_client=client,
            name="Expenses Agent",
            instructions=f"You help users to log expenses. Today's date is {datetime.now().strftime('%Y-%m-%d')}.",
        ) as agent,
    ):
        user_query = "yesterday I bought a laptop for $1200 using my visa."
        result = await agent.run(user_query, tools=mcp_server)
        print(result)

        # Keep the worker alive in production
        while RUNNING_IN_PRODUCTION:
            await asyncio.sleep(60)
            logger.info("Worker still running...")


if __name__ == "__main__":
    asyncio.run(http_mcp_example())
