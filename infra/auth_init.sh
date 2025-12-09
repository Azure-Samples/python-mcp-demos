#!/bin/bash
# Pre-provision hook to set up Azure/Entra ID app registration for FastMCP OAuth Proxy

# Check if USE_FASTMCP_AUTH is enabled
USE_FASTMCP_AUTH=$(azd env get-value USE_FASTMCP_AUTH 2>/dev/null || echo "false")
if [ "$USE_FASTMCP_AUTH" != "true" ]; then
    echo "Skipping auth init (USE_FASTMCP_AUTH is not enabled)"
    exit 0
fi

echo "Setting up Azure/Entra ID app registration for FastMCP OAuth Proxy..."
python ./infra/fastmcp_auth_init.py
