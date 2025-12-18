param name string
param location string = resourceGroup().location
param tags object = {}

param identityName string
param containerAppsEnvironmentName string
param containerRegistryName string
param serviceName string = 'server'
param exists bool
param openAiDeploymentName string
param openAiEndpoint string
param cosmosDbAccount string
param cosmosDbDatabase string
param cosmosDbContainer string
param cosmosDbUserContainer string
param cosmosDbOAuthContainer string
param applicationInsightsConnectionString string = ''
@allowed([
  'appinsights'
  'logfire'
  'none'
])
param openTelemetryPlatform string = 'appinsights'
param keycloakRealmUrl string = ''
param keycloakMcpServerAudience string = 'mcp-server'
param keycloakMcpServerBaseUrl string = ''
param entraProxyClientId string = ''
@secure()
param entraProxyClientSecret string = ''
param entraProxyBaseUrl string = ''
param tenantId string = ''
@secure()
param logfireToken string = ''
@allowed([
  'none'
  'keycloak'
  'entra_proxy'
])
param mcpAuthProvider string = 'none'

// Base environment variables
// Select MCP entrypoint based on configured auth (Keycloak or FastMCP Azure auth)
var mcpEntry = (!empty(keycloakRealmUrl) || !empty(entraProxyClientId)) ? 'auth' : 'deployed'
var baseEnv = [
  {
    name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
    value: openAiDeploymentName
  }
  {
    name: 'AZURE_OPENAI_ENDPOINT'
    value: openAiEndpoint
  }
  {
    name: 'RUNNING_IN_PRODUCTION'
    value: 'true'
  }
  {
    name: 'MCP_AUTH_PROVIDER'
    value: mcpAuthProvider
  }
  {
    name: 'AZURE_CLIENT_ID'
    value: serverIdentity.properties.clientId
  }
  {
    name: 'AZURE_COSMOSDB_ACCOUNT'
    value: cosmosDbAccount
  }
  {
    name: 'AZURE_COSMOSDB_DATABASE'
    value: cosmosDbDatabase
  }
  {
    name: 'AZURE_COSMOSDB_CONTAINER'
    value: cosmosDbContainer
  }
  {
    name: 'AZURE_COSMOSDB_USER_CONTAINER'
    value: cosmosDbUserContainer
  }
  {
    name: 'AZURE_COSMOSDB_OAUTH_CONTAINER'
    value: cosmosDbOAuthContainer
  }
  // We typically store sensitive values in secrets, but App Insights connection strings are not considered highly sensitive
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: applicationInsightsConnectionString
  }
  {
    name: 'MCP_ENTRY'
    value: mcpEntry
  }
  {
    name: 'OPENTELEMETRY_PLATFORM'
    value: openTelemetryPlatform
  }
]

// Logfire environment variables (only added when configured)
var logfireEnv = !empty(logfireToken) ? [
  {
    name: 'LOGFIRE_TOKEN'
    secretRef: 'logfire-token'
  }
] : []

// Keycloak authentication environment variables (only added when configured)
var keycloakEnv = !empty(keycloakRealmUrl) ? [
  {
    name: 'KEYCLOAK_REALM_URL'
    value: keycloakRealmUrl
  }
  {
    name: 'KEYCLOAK_MCP_SERVER_AUDIENCE'
    value: keycloakMcpServerAudience
  }
  {
    name: 'KEYCLOAK_MCP_SERVER_BASE_URL'
    value: keycloakMcpServerBaseUrl
  }
] : []

// Azure/Entra ID OAuth Proxy environment variables (only added when configured)
var entraProxyEnv = !empty(entraProxyClientId) ? [
  {
    name: 'ENTRA_PROXY_AZURE_CLIENT_ID'
    value: entraProxyClientId
  }
  {
    name: 'ENTRA_PROXY_AZURE_CLIENT_SECRET'
    secretRef: 'entra-proxy-client-secret'
  }
  {
    name: 'ENTRA_PROXY_MCP_SERVER_BASE_URL'
    value: entraProxyBaseUrl
  }
  {
    name: 'AZURE_TENANT_ID'
    value: tenantId
  }
] : []

// Secrets for sensitive values
var entraProxySecrets = !empty(entraProxyClientSecret) ? [
  {
    name: 'entra-proxy-client-secret'
    value: entraProxyClientSecret
  }
] : []

// Secret for Logfire token
var logfireSecrets = !empty(logfireToken) ? [
  {
    name: 'logfire-token'
    value: logfireToken
  }
] : []


resource serverIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

module app 'core/host/container-app-upsert.bicep' = {
  name: '${serviceName}-container-app-module'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    identityName: serverIdentity.name
    exists: exists
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerRegistryName: containerRegistryName
    ingressEnabled: true
    env: concat(baseEnv, keycloakEnv, entraProxyEnv, logfireEnv)
    secrets: concat(entraProxySecrets, logfireSecrets)
    targetPort: 8000
    probes: [
      {
        type: 'Startup'
        httpGet: {
          path: '/health'
          port: 8000
        }
        initialDelaySeconds: 10
        periodSeconds: 3
        failureThreshold: 60
      }
      {
        type: 'Readiness'
        httpGet: {
          path: '/health'
          port: 8000
        }
        initialDelaySeconds: 5
        periodSeconds: 5
        failureThreshold: 3
      }
      {
        type: 'Liveness'
        httpGet: {
          path: '/health'
          port: 8000
        }
        periodSeconds: 10
        failureThreshold: 3
      }
    ]
  }
}

output identityPrincipalId string = serverIdentity.properties.principalId
output name string = app.outputs.name
output hostName string = app.outputs.hostName
output uri string = app.outputs.uri
output imageName string = app.outputs.imageName
output mcpEntry string = mcpEntry
