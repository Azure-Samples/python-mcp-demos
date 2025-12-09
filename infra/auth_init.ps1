# Pre-provision hook to set up Azure/Entra ID app registration for FastMCP OAuth Proxy

# Check if USE_FASTMCP_AUTH is enabled
$USE_FASTMCP_AUTH = azd env get-value USE_FASTMCP_AUTH 2>$null
if ($USE_FASTMCP_AUTH -ne "true") {
    Write-Host "Skipping auth init (USE_FASTMCP_AUTH is not enabled)"
    exit 0
}

Write-Host "Setting up Azure/Entra ID app registration for FastMCP OAuth Proxy..."
python ./infra/fastmcp_auth_init.py
