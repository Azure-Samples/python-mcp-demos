# Python MCP Demo

A demonstration project showcasing Model Context Protocol (MCP) implementations using FastMCP, with examples of stdio, HTTP transports, and integration with LangChain and Agent Framework.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Python Scripts](#python-scripts)
- [MCP Server Configuration](#mcp-server-configuration)
- [Debugging](#debugging)

## Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/)
- API access to one of the following:
  - GitHub Models (GitHub token)
  - Azure OpenAI (Azure credentials)
  - Ollama (local installation)
  - OpenAI API (API key)

## Setup

1. Install dependencies using `uv`:

   ```bash
   uv sync
   ```

2. Copy `.env-sample` to `.env` and configure your environment variables:

   ```bash
   cp .env-sample .env
   ```

3. Edit `.env` with your API credentials. Choose one of the following providers by setting `API_HOST`:
   - `github` - GitHub Models (requires `GITHUB_TOKEN`)
   - `azure` - Azure OpenAI (requires Azure credentials)
   - `ollama` - Local Ollama instance
   - `openai` - OpenAI API (requires `OPENAI_API_KEY`)

## Python Scripts

Run any script with: `uv run <script_path>`

- **servers/basic_mcp_http.py** - MCP server with HTTP transport on port 8000
- **servers/basic_mcp_stdio.py** - MCP server with stdio transport for VS Code integration
- **agents/langchainv1_http.py** - LangChain agent with MCP integration
- **agents/langchainv1_github.py** - LangChain tool filtering demo with GitHub MCP (requires `GITHUB_TOKEN`)
- **agents/agentframework_learn.py** - Microsoft Agent Framework integration with MCP
- **agents/agentframework_http.py** - Microsoft Agent Framework integration with local Expenses MCP server

## MCP Server Configuration

### Using with MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a developer tool for testing and debugging MCP servers.

> **Note:** While HTTP servers can technically work with port forwarding in Codespaces/Dev Containers, the setup for MCP Inspector and debugger attachment is not straightforward. For the best development experience with full debugging capabilities, we recommend running this project locally.

**For stdio servers:**

```bash
npx @modelcontextprotocol/inspector uv run servers/basic_mcp_stdio.py
```

**For HTTP servers:**

1. Start the HTTP server:

   ```bash
   uv run servers/basic_mcp_http.py
   ```

2. In another terminal, run the inspector:

   ```bash
   npx @modelcontextprotocol/inspector http://localhost:8000/mcp
   ```

The inspector provides a web interface to:

- View available tools, resources, and prompts
- Test tool invocations with custom parameters
- Inspect server responses and errors
- Debug server communication

### Using with GitHub Copilot

The `.vscode/mcp.json` file configures MCP servers for GitHub Copilot integration:

**Available Servers:**

- **expenses-mcp**: stdio transport server for production use
- **expenses-mcp-debug**: stdio server with debugpy on port 5678
- **expenses-mcp-http**: HTTP transport server at `http://localhost:8000/mcp`. You must start this server manually with `uv run servers/basic_mcp_http.py` before using it.

**Switching Servers:**

Configure which server GitHub Copilot uses by opening the Chat panel, selecting the tools icon, and choosing the desired MCP server from the list.

![Servers selection dialog](readme_serverselect.png)

**Example input**

Use a query like this to test the expenses MCP server:

```
Log expense for 50 bucks of pizza on my amex today
```

![Example GitHub Copilot Chat Input](readme_samplequery.png)

## Debugging

The `.vscode/launch.json` provides one debug configuration:

**Attach to MCP Server (stdio)**: Attaches to server started via `expenses-mcp-debug` in `mcp.json`

To debug an MCP server with GitHub Copilot Chat:

1. Set breakpoints in the MCP server code in `servers/basic_mcp_stdio.py`
1. Start the debug server via `mcp.json` configuration by selecting `expenses-mcp-debug`
1. Press `Cmd+Shift+D` to open Run and Debug
1. Select "Attach to MCP Server (stdio)" configuration
1. Press `F5` or the play button to start the debugger
1. Select the expenses-mcp-debug server in GitHub Copilot Chat tools
1. Use GitHub Copilot Chat to trigger the MCP tools
1. Debugger pauses at breakpoints