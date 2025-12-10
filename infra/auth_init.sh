#!/bin/bash
# Pre-provision hook to set up Azure/Entra ID app registration for FastMCP Entra OAuth Proxy

USE_ENTRA_PROXY=$(azd env get-value USE_ENTRA_PROXY 2>/dev/null || echo "false")
if [ "$USE_ENTRA_PROXY" != "true" ]; then
    echo "Skipping auth init (USE_ENTRA_PROXY is not enabled)"
    exit 0
fi

echo "Setting up Entra ID app registration for FastMCP Entra OAuth Proxy..."
python ./infra/auth_init.py
