"""LangChain + Tavily MCP Example

Creates a simple research agent that uses the Tavily MCP server
to search the web and answer questions with relevant links.
"""

import asyncio
import logging
import os

import azure.identity
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger("langchainv1_tavily")
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv(override=True)

api_host = os.getenv("API_HOST", "github")

if api_host == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    model = ChatOpenAI(
        model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1/",
        api_key=token_provider,
    )
elif api_host == "github":
    model = ChatOpenAI(
        model=os.getenv("GITHUB_MODEL", "gpt-4o"),
        base_url="https://models.inference.ai.azure.com",
        api_key=SecretStr(os.environ["GITHUB_TOKEN"]),
    )
elif api_host == "ollama":
    model = ChatOpenAI(
        model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key=SecretStr(os.environ.get("OLLAMA_API_KEY", "none")),
    )
else:
    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))


async def run_agent() -> None:
    """Run a Tavily-backed research agent via MCP tools."""
    tavily_key = os.environ["TAVILY_API_KEY"]
    client = MultiServerMCPClient(
        {
            "tavily": {
                "url": "https://mcp.tavily.com/mcp/",
                "transport": "streamable_http",
                "headers": {"Authorization": f"Bearer {tavily_key}"},
            }
        }
    )

    # Fetch available tools and create the agent
    tools = await client.get_tools()
    agent = create_agent(model, tools, prompt="You search the web and include relevant links in answers.")

    query = "What's new in Python 3.14? Include relevant links."
    response = await agent.ainvoke({"messages": [HumanMessage(content=query)]})

    final_response = response["messages"][-1].content
    print(final_response)


def main() -> None:
    asyncio.run(run_agent())


if __name__ == "__main__":
    main()
