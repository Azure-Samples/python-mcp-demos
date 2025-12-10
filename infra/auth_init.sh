#!/bin/bash
# Pre-provision hook to set up Azure/Entra ID app registration for FastMCP Entra OAuth Proxy

MCP_AUTH_PROVIDER=$(azd env get-value MCP_AUTH_PROVIDER 2>/dev/null || echo "none")
if [ "$MCP_AUTH_PROVIDER" != "entra_proxy" ]; then
    echo "Skipping auth init (MCP_AUTH_PROVIDER is not entra_proxy)"
    exit 0
fi

echo "Setting up Entra ID app registration for FastMCP Entra OAuth Proxy..."
python ./infra/auth_init.py
