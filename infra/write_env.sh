#!/bin/bash

set -e

# Define the .env file path
ENV_FILE_PATH=".env"

# Clear the contents of the .env file
> "$ENV_FILE_PATH"

echo "AZURE_OPENAI_CHAT_DEPLOYMENT=$(azd env get-value AZURE_OPENAI_CHAT_DEPLOYMENT)" >> "$ENV_FILE_PATH"
echo "AZURE_OPENAI_CHAT_MODEL=$(azd env get-value AZURE_OPENAI_CHAT_MODEL)" >> "$ENV_FILE_PATH"
echo "AZURE_OPENAI_ENDPOINT=$(azd env get-value AZURE_OPENAI_ENDPOINT)" >> "$ENV_FILE_PATH"
echo "AZURE_TENANT_ID=$(azd env get-value AZURE_TENANT_ID)" >> "$ENV_FILE_PATH"
echo "AZURE_COSMOSDB_ACCOUNT=$(azd env get-value AZURE_COSMOSDB_ACCOUNT)" >> "$ENV_FILE_PATH"
echo "AZURE_COSMOSDB_DATABASE=$(azd env get-value AZURE_COSMOSDB_DATABASE)" >> "$ENV_FILE_PATH"
echo "AZURE_COSMOSDB_CONTAINER=$(azd env get-value AZURE_COSMOSDB_CONTAINER)" >> "$ENV_FILE_PATH"
echo "APPLICATIONINSIGHTS_CONNECTION_STRING=$(azd env get-value APPLICATIONINSIGHTS_CONNECTION_STRING)" >> "$ENV_FILE_PATH"
# Use direct Keycloak URL for token requests (issuer must match what MCP server expects)
echo "KEYCLOAK_REALM_URL=$(azd env get-value KEYCLOAK_DIRECT_URL)/realms/mcp" >> "$ENV_FILE_PATH"
echo "MCP_SERVER_URL=$(azd env get-value MCP_SERVER_URL)/mcp" >> "$ENV_FILE_PATH"
echo "API_HOST=azure" >> "$ENV_FILE_PATH"
