# Python MCP Demo

A demonstration project showcasing Model Context Protocol (MCP) implementations using FastMCP, with examples of stdio and HTTP transports, integration with LangChain and Agent Framework, and deployment to Azure Container Apps.

## Table of Contents

- [Getting started](#getting-started)
  - [GitHub Codespaces](#github-codespaces)
  - [VS Code Dev Containers](#vs-code-dev-containers)
  - [Local environment](#local-environment)
- [Run local MCP servers](#run-local-mcp-servers)
  - [Use with GitHub Copilot](#use-with-github-copilot)
  - [Debug with VS Code](#debug-with-vs-code)
  - [Inspect with MCP inspector](#inspect-with-mcp-inspector)
  - [View traces with Aspire Dashboard](#view-traces-with-aspire-dashboard)
- [Run local Agents <-> MCP](#run-local-agents---mcp)
- [Deploy to Azure](#deploy-to-azure)
- [Deploy to Azure with private networking](#deploy-to-azure-with-private-networking)
- [Deploy to Azure with Keycloak authentication](#deploy-to-azure-with-keycloak-authentication)
- [Deploy to Azure with Entra OAuth Proxy](#deploy-to-azure-with-entra-oauth-proxy)

## Getting started

You have a few options for setting up this project. The quickest way to get started is GitHub Codespaces, since it will setup all the tools for you, but you can also set it up locally.

### GitHub Codespaces

You can run this project virtually by using GitHub Codespaces. Click the button to open a web-based VS Code instance in your browser:

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/pamelafox/python-mcp-demo)

Once the Codespace is open, open a terminal window and continue with the deployment steps.

### VS Code Dev Containers

A related option is VS Code Dev Containers, which will open the project in your local VS Code using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Start Docker Desktop (install it if not already installed)
2. Open the project: [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/pamelafox/python-mcp-demo)
3. In the VS Code window that opens, once the project files show up (this may take several minutes), open a terminal window.
4. Continue with the deployment steps.

### Local environment

If you're not using one of the above options, then you'll need to:

1. Make sure the following tools are installed:
   - [Azure Developer CLI (azd)](https://aka.ms/install-azd)
   - [Python 3.13+](https://www.python.org/downloads/)
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - [Git](https://git-scm.com/downloads)

2. Clone the repository and open the project folder.

3. Create a [Python virtual environment](https://docs.python.org/3/tutorial/venv.html#creating-virtual-environments) and activate it.

4. Install the dependencies:

   ```bash
   uv sync
   ```

5. Copy `.env-sample` to `.env` and configure your environment variables:

   ```bash
   cp .env-sample .env
   ```

6. Edit `.env` with your API credentials. Choose one of the following providers by setting `API_HOST`:
   - `github` - GitHub Models (requires `GITHUB_TOKEN`)
   - `azure` - Azure OpenAI (requires Azure credentials)
   - `ollama` - Local Ollama instance
   - `openai` - OpenAI API (requires `OPENAI_API_KEY`)

## Run local MCP servers

This project includes MCP servers in the [`servers/`](servers/) directory:

| File | Description |
|------|-------------|
| [servers/basic_mcp_stdio.py](servers/basic_mcp_stdio.py) | MCP server with stdio transport for VS Code integration |
| [servers/basic_mcp_http.py](servers/basic_mcp_http.py) | MCP server with HTTP transport on port 8000 |
| [servers/deployed_mcp.py](servers/deployed_mcp.py) | MCP server for Azure deployment with Cosmos DB and optional Keycloak auth |

The local servers (`basic_mcp_stdio.py` and `basic_mcp_http.py`) implement an "Expenses Tracker" with a tool to add expenses to a CSV file.

### Use with GitHub Copilot

The `.vscode/mcp.json` file configures MCP servers for GitHub Copilot integration:

**Available Servers:**

- **expenses-mcp**: stdio transport server for production use
- **expenses-mcp-debug**: stdio server with debugpy on port 5678
- **expenses-mcp-http**: HTTP transport server at `http://localhost:8000/mcp`. You must start this server manually with `uv run servers/basic_mcp_http.py` before using it.

**Switching Servers:**

Configure which server GitHub Copilot uses by opening the Chat panel, selecting the tools icon, and choosing the desired MCP server from the list.

![Servers selection dialog](readme_serverselect.png)

**Example input:**

Use a query like this to test the expenses MCP server:

```text
Log expense for 50 bucks of pizza on my amex today
```

![Example GitHub Copilot Chat Input](readme_samplequery.png)

### Debug with VS Code

The `.vscode/launch.json` provides a debug configuration to attach to an MCP server.

**To debug an MCP server with GitHub Copilot Chat:**

1. Set breakpoints in the MCP server code in `servers/basic_mcp_stdio.py`
2. Start the debug server via `mcp.json` configuration by selecting `expenses-mcp-debug`
3. Press `Cmd+Shift+D` to open Run and Debug
4. Select "Attach to MCP Server (stdio)" configuration
5. Press `F5` or the play button to start the debugger
6. Select the "expenses-mcp-debug" server in GitHub Copilot Chat tools
7. Use GitHub Copilot Chat to trigger the MCP tools
8. Debugger pauses at breakpoints

### Inspect with MCP inspector

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

### View traces with Aspire Dashboard

You can use the [.NET Aspire Dashboard](https://learn.microsoft.com/dotnet/aspire/fundamentals/dashboard/standalone) to view OpenTelemetry traces, metrics, and logs from the MCP server.

> **Note:** Aspire Dashboard integration is only configured for the HTTP server (`basic_mcp_http.py`).

1. Start the Aspire Dashboard:

   ```bash
   docker run --rm -d -p 18888:18888 -p 4317:18889 --name aspire-dashboard \
       mcr.microsoft.com/dotnet/aspire-dashboard:latest
   ```

   > The Aspire Dashboard exposes its OTLP endpoint on container port 18889. The mapping `-p 4317:18889` makes it available on the host's standard OTLP port 4317.

   Get the dashboard URL and login token from the container logs:

   ```bash
   docker logs aspire-dashboard 2>&1 | grep "Login to the dashboard"
   ```

2. Enable OpenTelemetry by adding this to your `.env` file:

   ```bash
   OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
   ```

3. Start the HTTP server:

   ```bash
   uv run servers/basic_mcp_http.py
   ```

4. View the dashboard at: http://localhost:18888

---

## Run local Agents <-> MCP

This project includes example agents in the [`agents/`](agents/) directory that demonstrate how to connect AI agents to MCP servers:

| File | Description |
|------|-------------|
| [agents/agentframework_learn.py](agents/agentframework_learn.py) | Microsoft Agent Framework integration with MCP |
| [agents/agentframework_http.py](agents/agentframework_http.py) | Microsoft Agent Framework integration with local Expenses MCP server |
| [agents/langchainv1_http.py](agents/langchainv1_http.py) | LangChain agent with MCP integration |
| [agents/langchainv1_github.py](agents/langchainv1_github.py) | LangChain tool filtering demo with GitHub MCP (requires `GITHUB_TOKEN`) |

**To run an agent:**

1. First start the HTTP MCP server:

   ```bash
   uv run servers/basic_mcp_http.py
   ```

2. In another terminal, run an agent:

   ```bash
   uv run agents/agentframework_http.py
   ```

The agents will connect to the MCP server and allow you to interact with the expense tracking tools through a chat interface.

---

## Deploy to Azure

This project can be deployed to Azure Container Apps using the Azure Developer CLI (azd). The deployment provisions:

- **Azure Container Apps** - Hosts both the MCP server and agent
- **Azure OpenAI** - Provides the LLM for the agent
- **Azure Cosmos DB** - Stores expenses data
- **Azure Container Registry** - Stores container images
- **Log Analytics** - Monitoring and diagnostics

### Azure account setup

1. Sign up for a [free Azure account](https://azure.microsoft.com/free/) and create an Azure Subscription.
2. Check that you have the necessary permissions:
   - Your Azure account must have `Microsoft.Authorization/roleAssignments/write` permissions, such as [Role Based Access Control Administrator](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#role-based-access-control-administrator-preview), [User Access Administrator](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#user-access-administrator), or [Owner](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles#owner).
   - Your Azure account also needs `Microsoft.Resources/deployments/write` permissions on the subscription level.

### Deploying with azd

1. Login to Azure:

   ```bash
   azd auth login
   ```

   For GitHub Codespaces users, if the previous command fails, try:

   ```bash
   azd auth login --use-device-code
   ```

2. Create a new azd environment:

   ```bash
   azd env new
   ```

   This will create a folder inside `.azure` with the name of your environment.

3. Provision and deploy the resources:

   ```bash
   azd up
   ```

   It will prompt you to select a subscription and location. This will take several minutes to complete.

4. Once deployment is complete, a `.env` file will be created with the necessary environment variables to run the agents locally against the deployed resources.

### Costs

Pricing varies per region and usage, so it isn't possible to predict exact costs for your usage.

You can try the [Azure pricing calculator](https://azure.com/e/3987c81282c84410b491d28094030c9a) for the resources:

- **Azure OpenAI Service**: S0 tier, GPT-4o-mini model. Pricing is based on token count. [Pricing](https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/)
- **Azure Container Apps**: Consumption tier. [Pricing](https://azure.microsoft.com/pricing/details/container-apps/)
- **Azure Container Registry**: Standard tier. [Pricing](https://azure.microsoft.com/pricing/details/container-registry/)
- **Azure Cosmos DB**: Serverless tier. [Pricing](https://azure.microsoft.com/pricing/details/cosmos-db/)
- **Log Analytics** (Optional): Pay-as-you-go tier. Costs based on data ingested. [Pricing](https://azure.microsoft.com/pricing/details/monitor/)

⚠️ To avoid unnecessary costs, remember to take down your app if it's no longer in use, either by deleting the resource group in the Portal or running `azd down`.

### Use deployed MCP server with GitHub Copilot

The URL of the deployed MCP server is available in the azd environment variable `MCP_SERVER_URL`, and is written to the `.env` file created after deployment.

1. To avoid conflicts, stop the MCP servers from `mcp.json` and disable the expense MCP servers in GitHub Copilot Chat tools.
2. Select "MCP: Add Server" from the VS Code Command Palette
3. Select "HTTP" as the server type
4. Enter the URL of the MCP server, based on the `MCP_SERVER_URL` environment variable.
5. Enable the MCP server in GitHub Copilot Chat tools and test it with an expense tracking query:

   ```text
   Log expense for 75 dollars of office supplies on my visa last Friday
   ```

### Running the server locally

After deployment sets up the required Azure resources (Cosmos DB, Application Insights), you can also run the MCP server locally against those resources:

```bash
# Run the MCP server
cd servers && uvicorn deployed_mcp:app --host 0.0.0.0 --port 8000
```

### Viewing traces in Azure Application Insights

By default, OpenTelemetry tracing is enabled for the deployed MCP server, sending traces to Azure Application Insights.

1. Open the Azure Portal and navigate to the Application Insights resource created during deployment (named `<project-name>-appinsights`).
2. In Application Insights, go to "Transaction Search" to view traces from the MCP server
3. You can filter and analyze traces to monitor performance and diagnose issues.

### Viewing traces in Logfire

You can also view OpenTelemetry traces in [Logfire](https://logfire.io/) by configuring the MCP server to send traces there.

1. Create a Logfire account and get your write token from the Logfire dashboard.

2. Set the azd environment variables to enable Logfire:

   ```bash
   azd env set OPENTELEMETRY_PLATFORM logfire
   azd env set LOGFIRE_TOKEN <your-logfire-write-token>
   ```

3. Provision and deploy:

   ```bash
   azd up
   ```

4. Open the Logfire dashboard to view traces from the MCP server.

---

## Deploy to Azure with private networking

To demonstrate enhanced security for production deployments, this project supports deploying with a virtual network (VNet) configuration that restricts public access to Azure resources.

1. Set these azd environment variables to set up a virtual network and private endpoints for the Container App, Cosmos DB, and OpenAI resources:

   ```bash
   azd env set USE_VNET true
   azd env set USE_PRIVATE_INGRESS true
   ```

   The Log Analytics and ACR resources will still have public access enabled, so that you can deploy and monitor the app without needing a VPN. In production, you would typically restrict these as well.

2. Provision and deploy:

   ```bash
   azd up
   ```

### Additional costs for private networking

When using VNet configuration, additional Azure resources are provisioned:

- **Virtual Network**: Pay-as-you-go tier. Costs based on data processed. [Pricing](https://azure.microsoft.com/pricing/details/virtual-network/)
- **Azure Private DNS Resolver**: Pricing per month, endpoints, and zones. [Pricing](https://azure.microsoft.com/pricing/details/dns/)
- **Azure Private Endpoints**: Pricing per hour per endpoint. [Pricing](https://azure.microsoft.com/pricing/details/private-link/)

---

## Deploy to Azure with Keycloak authentication

This project supports deploying with OAuth 2.0 authentication using Keycloak as the identity provider, implementing the [MCP OAuth specification](https://modelcontextprotocol.io/specification/2025-03-26/basic/authorization) with Dynamic Client Registration (DCR).

### What gets deployed

| Component | Description |
|-----------|-------------|
| **Keycloak Container App** | Keycloak 26.0 with pre-configured realm |
| **HTTP Route Configuration** | Rule-based routing: `/auth/*` → Keycloak, `/*` → MCP Server |
| **OAuth-protected MCP Server** | FastMCP with JWT validation against Keycloak's JWKS endpoint |

### Deployment steps

1. Enable Keycloak authentication:

   ```bash
   azd env set MCP_AUTH_PROVIDER keycloak
   ```

2. Set the Keycloak admin password (required):

   ```bash
   azd env set KEYCLOAK_ADMIN_PASSWORD "YourSecurePassword123!"
   ```

3. Optionally customize the realm name (default: `mcp`):

   ```bash
   azd env set KEYCLOAK_REALM_NAME "mcp"
   ```

4. Deploy to Azure:

   ```bash
   azd up
   ```

   This will create the Azure Container Apps environment, deploy Keycloak with the pre-configured realm, deploy the MCP server with OAuth validation, and configure HTTP route-based routing.

5. Verify deployment by checking the outputs:

   ```bash
   azd env get-value MCP_SERVER_URL
   azd env get-value KEYCLOAK_DIRECT_URL
   azd env get-value KEYCLOAK_ADMIN_CONSOLE
   ```

6. Visit the Keycloak admin console to verify the realm is configured:

   ```text
   https://<your-mcproutes-url>/auth/admin
   ```

   Login with `admin` and your configured password.

### Testing with the agent

1. Generate the local environment file (automatically created after `azd up`):

   ```bash
   ./infra/write_env.sh
   ```

   This creates `.env` with `KEYCLOAK_REALM_URL`, `MCP_SERVER_URL`, and Azure OpenAI settings.

2. Run the agent:

   ```bash
   uv run agents/agentframework_http.py
   ```

   The agent automatically detects `KEYCLOAK_REALM_URL` in the environment and authenticates via DCR + client credentials. On success, it will add an expense and print the result.

### Known limitations (demo trade-offs)

| Item | Current | Production Recommendation | Why |
|------|---------|---------------------------|-----|
| Keycloak mode | `start-dev` | `start` with proper config | Dev mode has relaxed security defaults |
| Database | H2 in-memory | PostgreSQL | H2 doesn't persist data across restarts |
| Replicas | 1 (due to H2) | Multiple with shared DB | H2 is in-memory, can't share state |
| Keycloak access | Public (direct URL) | Internal only via routes | Route URL isn't known until after deployment |
| DCR | Open (anonymous) | Require initial access token | Any client can register without auth |

> **Note:** Keycloak must be publicly accessible because its URL is dynamically generated by Azure. Token issuer validation requires a known URL, but the mcproutes URL isn't available until after deployment. Using a custom domain would fix this.

---

## Deploy to Azure with Entra OAuth Proxy

This project supports deploying with Microsoft Entra ID (Azure AD) authentication using FastMCP's built-in Azure OAuth proxy. This is an alternative to Keycloak that uses Microsoft Entra with your Azure tenant for identity management.

### What gets deployed with Entra OAuth

| Component | Description |
|-----------|-------------|
| **Microsoft Entra App Registration** | Created automatically during provisioning with redirect URIs for local development, VS Code, and production |
| **OAuth-protected MCP Server** | FastMCP with AzureProvider for OAuth authentication |
| **CosmosDB OAuth Client Storage** | Persists OAuth client registrations across server restarts |

### Deployment steps for Entra OAuth

1. Enable Entra OAuth proxy:

   ```bash
   azd env set MCP_AUTH_PROVIDER entra_proxy
   ```

2. Set your tenant ID so that the App Registration is created in the correct tenant:

   ```bash
   azd env set AZURE_TENANT_ID "<your-tenant-id>"
   ```

3. Deploy to Azure:

   ```bash
   azd up
   ```

   During deployment:
   - **Preprovision hook**: Creates a Microsoft Entra App Registration with a client secret, and stores the credentials in azd environment variables
   - **Postprovision hook**: Updates the App Registration with the deployed server URL as an additional redirect URI

4. Verify deployment by checking the outputs:

   ```bash
   azd env get-value MCP_SERVER_URL
   azd env get-value ENTRA_PROXY_AZURE_CLIENT_ID
   ```

### Environment variables

The following environment variables are automatically set by the deployment hooks:

| Variable | Description |
|----------|-------------|
| `ENTRA_PROXY_AZURE_CLIENT_ID` | The App Registration's client ID |
| `ENTRA_PROXY_AZURE_CLIENT_SECRET` | The App Registration's client secret |

These are then written to `.env` by the postprovision hook for local development.

### Testing the Entra OAuth server locally

After deployment, you can test locally with OAuth enabled:

```bash
# Run the MCP server
cd servers && uvicorn auth_mcp:app --host 0.0.0.0 --port 8000
```

The server will use the Entra App Registration for OAuth and CosmosDB for client storage.

### Use Entra OAuth MCP server with GitHub Copilot

The Entra App Registration includes these redirect URIs for VS Code:

- `https://vscode.dev/redirect` (VS Code web)
- `http://127.0.0.1:{33418-33427}` (VS Code desktop local auth helper, 10 ports)

To use the deployed MCP server with GitHub Copilot Chat:

1. To avoid conflicts, stop the MCP servers from `mcp.json` and disable the expense MCP servers in GitHub Copilot Chat tools.
2. Select "MCP: Add Server" from the VS Code Command Palette
3. Select "HTTP" as the server type
4. Enter the URL of the MCP server, either from `MCP_SERVER_URL` environment variable or `http://localhost:8000/mcp` if running locally.
5. If you get an error about "Client ID not found", open the Command Palette, run **"Authentication: Remove Dynamic Authentication Providers"**, and select the MCP server URL. This clears any cached OAuth tokens and forces a fresh authentication flow. Then restart the server to prompt the OAuth flow again.
6. You should see a FastMCP authentication screen open in your browser. Select "Allow access":

   ![FastMCP authentication screen](readme_appaccess.png)

7. After granting access, the browser will redirect to a VS Code "Sign-in successful!" page and then bring focus back to VS Code.

   ![VS Code sign-in successful page](readme_signedin.png)

8. Enable the MCP server in GitHub Copilot Chat tools and test it with an expense tracking query:

   ```text
   Log expense for 75 dollars of office supplies on my visa last Friday
   ```

   ![Example GitHub Copilot Chat Input](readme_authquery.png)

9. Verify the expense was added by checking the Cosmos DB `user-expenses` container in the Azure Portal.

   ![Cosmos DB user-expenses container](readme_userexpenses.png)
