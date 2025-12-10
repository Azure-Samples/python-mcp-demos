#!/bin/bash
# Post-provision hook to update Azure app registration redirect URIs with deployed server URL

# Check if MCP_AUTH_PROVIDER is entra_proxy
MCP_AUTH_PROVIDER=$(azd env get-value MCP_AUTH_PROVIDER 2>/dev/null || echo "none")
if [ "$MCP_AUTH_PROVIDER" != "entra_proxy" ]; then
    echo "Skipping auth update (MCP_AUTH_PROVIDER is not entra_proxy)"
    exit 0
fi

echo "Updating FastMCP auth redirect URIs with deployed server URL..."
python ./infra/auth_update.py
