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
param applicationInsightsConnectionString string = ''
param keycloakRealmUrl string
param mcpServerBaseUrl string
param mcpServerAudience string = 'mcp-server'


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
    env: [
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
      // We typically store sensitive values in secrets, but App Insights connection strings are not considered highly sensitive
      {
        name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
        value: applicationInsightsConnectionString
      }
      // Keycloak authentication environment variables
      {
        name: 'KEYCLOAK_REALM_URL'
        value: keycloakRealmUrl
      }
      {
        name: 'MCP_SERVER_BASE_URL'
        value: mcpServerBaseUrl
      }
      {
        name: 'MCP_SERVER_AUDIENCE'
        value: mcpServerAudience
      }
    ]
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
