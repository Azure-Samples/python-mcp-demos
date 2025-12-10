#!/bin/bash
# Post-provision hook to update Azure app registration redirect URIs with deployed server URL

# Check if USE_ENTRA_PROXY is enabled
USE_ENTRA_PROXY=$(azd env get-value USE_ENTRA_PROXY 2>/dev/null || echo "false")
if [ "$USE_ENTRA_PROXY" != "true" ]; then
    echo "Skipping auth update (USE_ENTRA_PROXY is not enabled)"
    exit 0
fi

echo "Updating FastMCP auth redirect URIs with deployed server URL..."
python ./infra/ENTRA_PROXY_update.py
