"""LangChain MCP Tool Filtering Example

Demonstrates how to filter MCP tools to create safe, focused agents.
Shows filtering for read-only research agent using GitHub MCP server.
"""

import asyncio
import os

import azure.identity
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

load_dotenv(override=True)

# Configure model
API_HOST = os.getenv("API_HOST", "github")
if API_HOST == "azure":
    token_provider = azure.identity.get_bearer_token_provider(
        azure.identity.DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    model = ChatOpenAI(
        model=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"] + "/openai/v1/",
        api_key=token_provider,
    )
elif API_HOST == "github":
    model = ChatOpenAI(
        model=os.getenv("GITHUB_MODEL", "gpt-4o"),
        base_url="https://models.inference.ai.azure.com",
        api_key=SecretStr(os.environ["GITHUB_TOKEN"]),
    )
elif API_HOST == "ollama":
    model = ChatOpenAI(
        model=os.environ.get("OLLAMA_MODEL", "llama3.1"),
        base_url=os.environ.get("OLLAMA_ENDPOINT", "http://localhost:11434/v1"),
        api_key=SecretStr("none"),
    )

console = Console()


async def main():
    """Create a safe research agent with filtered read-only tools"""
    console.print("\n[bold white on blue] LangChain Tool Filtering Demo [/bold white on blue]\n")

    console.print(
        Panel.fit(
            "[bold cyan]GitHub Research Agent (Read-Only)[/bold cyan]\nFiltered to only safe search tools",
            border_style="cyan",
        )
    )

    mcp_client = MultiServerMCPClient(
        {
            "github": {
                "url": "https://api.githubcopilot.com/mcp/",
                "transport": "streamable_http",
                "headers": {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"},
            }
        }
    )

    # Get all tools and show what we're filtering out
    all_tools = await mcp_client.get_tools()

    console.print(f"[dim]Total tools available: {len(all_tools)}[/dim]\n")

    # Filter to ONLY read operations
    safe_tool_names = ["search_repositories", "search_code", "search_issues"]
    filtered_tools = [t for t in all_tools if t.name in safe_tool_names]

    console.print("[bold cyan]Filtered Tools (read-only):[/bold cyan]")
    for tool in filtered_tools:
        console.print(f"  ✓ {tool.name}")
    console.print()

    # Create agent with filtered tools
    agent = create_agent(
        model,
        tools=filtered_tools,
        prompt="You help users research GitHub repositories. Search and analyze information.",
    )

    query = "Find 5 popular Python MCP server repositories and describe in a bulleted list."
    rprint(f"[bold]Query:[/bold] {query}\n")

    try:
        result = await agent.ainvoke({"messages": [HumanMessage(content=query)]})
        rprint(f"[bold green]Result:[/bold green]\n{result['messages'][-1].content}\n")
    except Exception as e:
        rprint(f"[bold red]Error:[/bold red] {str(e)}\n")


if __name__ == "__main__":
    asyncio.run(main())
