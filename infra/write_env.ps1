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
Add-Content -Path $ENV_FILE_PATH -Value "APPLICATIONINSIGHTS_CONNECTION_STRING=$(azd env get-value APPLICATIONINSIGHTS_CONNECTION_STRING)"
# Use direct Keycloak URL for token requests (issuer must match what MCP server expects)
Add-Content -Path $ENV_FILE_PATH -Value "KEYCLOAK_REALM_URL=$(azd env get-value KEYCLOAK_DIRECT_URL)/realms/mcp"
Add-Content -Path $ENV_FILE_PATH -Value "MCP_SERVER_URL=$(azd env get-value MCP_SERVER_URL)/mcp"
Add-Content -Path $ENV_FILE_PATH -Value "API_HOST=azure"
