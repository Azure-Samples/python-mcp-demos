# Post-provision hook to update Azure app registration redirect URIs with deployed server URL

# Check if USE_ENTRA_PROXY is enabled
$USE_ENTRA_PROXY = azd env get-value USE_ENTRA_PROXY 2>$null
if ($USE_ENTRA_PROXY -ne "true") {
    Write-Host "Skipping auth update (USE_ENTRA_PROXY is not enabled)"
    exit 0
}

Write-Host "Updating FastMCP auth redirect URIs with deployed server URL..."
python ./infra/ENTRA_PROXY_update.py
