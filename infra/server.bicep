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
param keycloakRealmUrl string = ''
param mcpServerBaseUrl string = ''
param keycloakMcpServerAudience string = 'mcp-server'
param entraProxyClientId string = ''
@secure()
param entraProxyClientSecret string = ''
param entraProxyBaseUrl string = ''
param tenantId string = ''

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
]

// Keycloak authentication environment variables (only added when configured)
var keycloakEnv = !empty(keycloakRealmUrl) ? [
  {
    name: 'KEYCLOAK_REALM_URL'
    value: keycloakRealmUrl
  }
  {
    name: 'MCP_SERVER_BASE_URL'
    value: mcpServerBaseUrl
  }
  {
    name: 'KEYCLOAK_MCP_SERVER_AUDIENCE'
    value: keycloakMcpServerAudience
  }
] : []

// Azure/Entra ID OAuth Proxy environment variables (only added when configured)
var entraProxyEnv = !empty(entraProxyClientId) ? [
  {
    name: 'FASTMCP_AUTH_AZURE_CLIENT_ID'
    value: entraProxyClientId
  }
  {
    name: 'FASTMCP_AUTH_AZURE_CLIENT_SECRET'
    secretRef: 'entra-proxy-client-secret'
  }
  {
    name: 'FASTMCP_AUTH_AZURE_BASE_URL'
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
    env: concat(baseEnv, keycloakEnv, entraProxyEnv)
    secrets: entraProxySecrets
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
