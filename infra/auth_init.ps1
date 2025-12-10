# Pre-provision hook to set up Azure/Entra ID app registration for FastMCP OAuth Proxy

# Check if MCP_AUTH_PROVIDER is entra_proxy
$MCP_AUTH_PROVIDER = azd env get-value MCP_AUTH_PROVIDER 2>$null
if ($MCP_AUTH_PROVIDER -ne "entra_proxy") {
    Write-Host "Skipping auth init (MCP_AUTH_PROVIDER is not entra_proxy)"
    exit 0
}

Write-Host "Setting up Azure/Entra ID app registration for FastMCP OAuth Proxy..."
python ./infra/auth_init.py
