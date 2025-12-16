from __future__ import annotations

import asyncio
import logging
import os

from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from rich import print
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("learn_mcp_lang")

# Load environment variables
load_dotenv(override=True)

# Constants
LEARN_MCP_URL = "https://learn.microsoft.com/api/mcp"

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


async def http_mcp_example() -> None:
    """
    Demonstrate MCP integration with Microsoft Learn documentation.

    Creates an agent that can answer questions about Microsoft documentation
    using the Microsoft Learn MCP server.
    """
    async with (
        MCPStreamableHTTPTool(name="Microsoft Learn MCP", url=LEARN_MCP_URL) as mcp_server,
        ChatAgent(
            chat_client=client,
            name="DocsAgent",
            instructions="You help with Microsoft documentation questions.",
        ) as agent,
    ):
        query = "How to create an Azure storage account using az cli?"
        result = await agent.run(query, tools=mcp_server)
        print(result)


if __name__ == "__main__":
    asyncio.run(http_mcp_example())
