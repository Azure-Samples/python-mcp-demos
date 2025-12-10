# Pre-provision hook to set up Azure/Entra ID app registration for FastMCP OAuth Proxy

# Check if USE_ENTRA_PROXY is enabled
$USE_ENTRA_PROXY = azd env get-value USE_ENTRA_PROXY 2>$null
if ($USE_ENTRA_PROXY -ne "true") {
    Write-Host "Skipping auth init (USE_ENTRA_PROXY is not enabled)"
    exit 0
}

Write-Host "Setting up Azure/Entra ID app registration for FastMCP OAuth Proxy..."
python ./infra/ENTRA_PROXY_init.py
