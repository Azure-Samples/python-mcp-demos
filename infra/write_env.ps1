# Define the .env file path
$ENV_FILE_PATH = ".env"

# Clear the contents of the .env file
Set-Content -Path $ENV_FILE_PATH -Value $null

Add-Content -Path $ENV_FILE_PATH -Value "AZURE_OPENAI_CHAT_DEPLOYMENT=$(azd env get-value AZURE_OPENAI_CHAT_DEPLOYMENT)"
Add-Content -Path $ENV_FILE_PATH -Value "AZURE_OPENAI_CHAT_MODEL=$(azd env get-value AZURE_OPENAI_CHAT_MODEL)"
Add-Content -Path $ENV_FILE_PATH -Value "AZURE_OPENAI_ENDPOINT=$(azd env get-value AZURE_OPENAI_ENDPOINT)"
Add-Content -Path $ENV_FILE_PATH -Value "AZURE_TENANT_ID=$(azd env get-value AZURE_TENANT_ID)"
Add-Content -Path $ENV_FILE_PATH -Value "AZURE_COSMOSDB_ACCOUNT=$(azd env get-value AZURE_COSMOSDB_ACCOUNT)"
Add-Content -Path $ENV_FILE_PATH -Value "AZURE_COSMOSDB_DATABASE=$(azd env get-value AZURE_COSMOSDB_DATABASE)"
Add-Content -Path $ENV_FILE_PATH -Value "AZURE_COSMOSDB_CONTAINER=$(azd env get-value AZURE_COSMOSDB_CONTAINER)"
Add-Content -Path $ENV_FILE_PATH -Value "AZURE_COSMOSDB_USER_CONTAINER=$(azd env get-value AZURE_COSMOSDB_USER_CONTAINER)"
Add-Content -Path $ENV_FILE_PATH -Value "AZURE_COSMOSDB_OAUTH_CONTAINER=$(azd env get-value AZURE_COSMOSDB_OAUTH_CONTAINER)"
Add-Content -Path $ENV_FILE_PATH -Value "APPLICATIONINSIGHTS_CONNECTION_STRING=$(azd env get-value APPLICATIONINSIGHTS_CONNECTION_STRING)"
# Auth feature flags
Add-Content -Path $ENV_FILE_PATH -Value "USE_FASTMCP_AUTH=$(azd env get-value USE_FASTMCP_AUTH)"
Add-Content -Path $ENV_FILE_PATH -Value "USE_KEYCLOAK=$(azd env get-value USE_KEYCLOAK)"
$KEYCLOAK_REALM_URL = azd env get-value KEYCLOAK_REALM_URL 2>$null
if ($KEYCLOAK_REALM_URL -and $KEYCLOAK_REALM_URL -ne "") {
    Add-Content -Path $ENV_FILE_PATH -Value "KEYCLOAK_REALM_URL=$KEYCLOAK_REALM_URL"
}
$FASTMCP_AUTH_AZURE_CLIENT_ID = azd env get-value FASTMCP_AUTH_AZURE_CLIENT_ID 2>$null
if ($FASTMCP_AUTH_AZURE_CLIENT_ID -and $FASTMCP_AUTH_AZURE_CLIENT_ID -ne "") {
    Add-Content -Path $ENV_FILE_PATH -Value "FASTMCP_AUTH_AZURE_CLIENT_ID=$FASTMCP_AUTH_AZURE_CLIENT_ID"
    Add-Content -Path $ENV_FILE_PATH -Value "FASTMCP_AUTH_AZURE_CLIENT_SECRET=$(azd env get-value FASTMCP_AUTH_AZURE_CLIENT_SECRET)"
}
Add-Content -Path $ENV_FILE_PATH -Value "MCP_ENTRY=$(azd env get-value MCP_ENTRY)"
Add-Content -Path $ENV_FILE_PATH -Value "MCP_SERVER_URL=$(azd env get-value MCP_SERVER_URL)"
Add-Content -Path $ENV_FILE_PATH -Value "API_HOST=azure"
