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
logger = logging.getLogger("agentframework_tavily")
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv(override=True)

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


async def http_mcp_example():
    """
    Creates an agent that can search the web using the Tavily MCP server.
    """

    tavily_key = os.environ["TAVILY_API_KEY"]
    headers = {"Authorization": f"Bearer {tavily_key}"}
    async with (
        MCPStreamableHTTPTool(name="Tavily MCP", url="https://mcp.tavily.com/mcp/", headers=headers) as mcp_server,
        ChatAgent(
            chat_client=client,
            name="WebSearchAgent",
            instructions="You search the web with Tavily and provide concise answers with links.",
        ) as agent,
    ):
        query = "What's new in Python 3.14? Include relevant links."
        result = await agent.run(query, tools=mcp_server)
        print(result)


if __name__ == "__main__":
    asyncio.run(http_mcp_example())
