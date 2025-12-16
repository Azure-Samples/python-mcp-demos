#!/bin/bash

set -e

# Define the .env file path
ENV_FILE_PATH=".env"

# Returns empty string if value not found or contains ERROR
get_azd_value() {
  local key="$1"
  local value
  value=$(azd env get-value "$key" 2>/dev/null || echo "")
  if [[ "$value" == *ERROR:* ]]; then
    echo ""
  else
    echo "$value"
  fi
}

# Write a required env var (always written)
write_env() {
  local key="$1"
  echo "${key}=$(get_azd_value "$key")" >> "$ENV_FILE_PATH"
}

# Write an optional env var (only written if value is non-empty)
write_env_if_set() {
  local key="$1"
  local value
  value=$(get_azd_value "$key")
  if [ -n "$value" ]; then
    echo "${key}=${value}" >> "$ENV_FILE_PATH"
  fi
}

# Clear the contents of the .env file
> "$ENV_FILE_PATH"

echo "AZURE_OPENAI_CHAT_DEPLOYMENT=$(azd env get-value AZURE_OPENAI_CHAT_DEPLOYMENT)" >> "$ENV_FILE_PATH"
echo "AZURE_OPENAI_CHAT_MODEL=$(azd env get-value AZURE_OPENAI_CHAT_MODEL)" >> "$ENV_FILE_PATH"
echo "AZURE_OPENAI_ENDPOINT=$(azd env get-value AZURE_OPENAI_ENDPOINT)" >> "$ENV_FILE_PATH"
echo "AZURE_TENANT_ID=$(azd env get-value AZURE_TENANT_ID)" >> "$ENV_FILE_PATH"
echo "AZURE_COSMOSDB_ACCOUNT=$(azd env get-value AZURE_COSMOSDB_ACCOUNT)" >> "$ENV_FILE_PATH"
echo "AZURE_COSMOSDB_DATABASE=$(azd env get-value AZURE_COSMOSDB_DATABASE)" >> "$ENV_FILE_PATH"
echo "AZURE_COSMOSDB_CONTAINER=$(azd env get-value AZURE_COSMOSDB_CONTAINER)" >> "$ENV_FILE_PATH"
echo "AZURE_COSMOSDB_USER_CONTAINER=$(azd env get-value AZURE_COSMOSDB_USER_CONTAINER)" >> "$ENV_FILE_PATH"
echo "AZURE_COSMOSDB_OAUTH_CONTAINER=$(azd env get-value AZURE_COSMOSDB_OAUTH_CONTAINER)" >> "$ENV_FILE_PATH"
echo "APPLICATIONINSIGHTS_CONNECTION_STRING=$(azd env get-value APPLICATIONINSIGHTS_CONNECTION_STRING)" >> "$ENV_FILE_PATH"
write_env_if_set LOGFIRE_TOKEN
write_env MCP_AUTH_PROVIDER
write_env OPENTELEMETRY_PLATFORM

# Keycloak-related env vars (only if KEYCLOAK_REALM_URL is set)
KEYCLOAK_REALM_URL=$(get_azd_value KEYCLOAK_REALM_URL)
if [ -n "$KEYCLOAK_REALM_URL" ]; then
  echo "KEYCLOAK_REALM_URL=${KEYCLOAK_REALM_URL}" >> "$ENV_FILE_PATH"
  write_env_if_set KEYCLOAK_TOKEN_ISSUER
  write_env_if_set KEYCLOAK_AGENT_REALM_URL
fi

# Entra proxy env vars (only if ENTRA_PROXY_AZURE_CLIENT_ID is set)
ENTRA_PROXY_AZURE_CLIENT_ID=$(get_azd_value ENTRA_PROXY_AZURE_CLIENT_ID)
if [ -n "$ENTRA_PROXY_AZURE_CLIENT_ID" ]; then
  echo "ENTRA_PROXY_AZURE_CLIENT_ID=${ENTRA_PROXY_AZURE_CLIENT_ID}" >> "$ENV_FILE_PATH"
  write_env ENTRA_PROXY_AZURE_CLIENT_SECRET
  write_env ENTRA_PROXY_MCP_SERVER_BASE_URL
fi
echo "MCP_ENTRY=$(azd env get-value MCP_ENTRY)" >> "$ENV_FILE_PATH"
echo "MCP_SERVER_URL=$(azd env get-value MCP_SERVER_URL)" >> "$ENV_FILE_PATH"
echo "KEYCLOAK_MCP_SERVER_BASE_URL=$(azd env get-value KEYCLOAK_MCP_SERVER_BASE_URL)" >> "$ENV_FILE_PATH"
echo "API_HOST=azure" >> "$ENV_FILE_PATH"
