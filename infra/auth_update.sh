#!/bin/bash
# Post-provision hook to update Azure app registration redirect URIs with deployed server URL

# Check if USE_FASTMCP_AUTH is enabled
USE_FASTMCP_AUTH=$(azd env get-value USE_FASTMCP_AUTH 2>/dev/null || echo "false")
if [ "$USE_FASTMCP_AUTH" != "true" ]; then
    echo "Skipping auth update (USE_FASTMCP_AUTH is not enabled)"
    exit 0
fi

echo "Updating FastMCP auth redirect URIs with deployed server URL..."
python ./infra/fastmcp_auth_update.py
