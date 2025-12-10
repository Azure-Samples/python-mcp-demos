# Post-provision hook to update Azure app registration redirect URIs with deployed server URL

# Check if MCP_AUTH_PROVIDER is entra_proxy
$MCP_AUTH_PROVIDER = azd env get-value MCP_AUTH_PROVIDER 2>$null
if ($MCP_AUTH_PROVIDER -ne "entra_proxy") {
    Write-Host "Skipping auth update (MCP_AUTH_PROVIDER is not entra_proxy)"
    exit 0
}

Write-Host "Updating FastMCP auth redirect URIs with deployed server URL..."
python ./infra/auth_update.py
