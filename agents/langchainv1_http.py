import asyncio
import logging
import os
from datetime import datetime

import azure.identity
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)
logger = logging.getLogger("itinerario_lang")

# Load environment variables
load_dotenv(override=True)

# Constants
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp/")

# Configure language model based on API_HOST
API_HOST = os.getenv("API_HOST", "github")

if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default"
    )
    base_model = ChatOpenAI(
        model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1/",
        api_key=token_provider,
    )
elif API_HOST == "github":
    base_model = ChatOpenAI(
        model=os.getenv("GITHUB_MODEL", "gpt-4o"),
        base_url="https://models.inference.ai.azure.com",
        api_key=SecretStr(os.environ["GITHUB_TOKEN"]),
    )
elif API_HOST == "ollama":
    base_model = ChatOpenAI(
        model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key=SecretStr(os.environ["OLLAMA_API_KEY"]),
    )
else:
    base_model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))


async def run_agent() -> None:
    """
    Run the agent to process expense-related queries using MCP tools.
    """
    # Initialize MCP client
    client = MultiServerMCPClient(
        {
            "expenses": {
                "url": MCP_SERVER_URL,
                "transport": "streamable_http",
            }
        }
    )

    # Get tools and create agent
    tools = await client.get_tools()
    agent = create_agent(base_model, tools)

    # Prepare query with context
    today = datetime.now().strftime("%Y-%m-%d")
    user_query = "yesterday I bought a laptop for $1200 using my visa."

    # Invoke agent
    response = await agent.ainvoke({
        "messages": [
            SystemMessage(content=f"Today's date is {today}."),
            HumanMessage(content=user_query)
        ]
    })
    
    # Display result
    final_response = response["messages"][-1].content
    print(final_response)


def main() -> None:
    """Main entry point for the application."""
    asyncio.run(run_agent())


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    main()
