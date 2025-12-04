param name string
param location string = resourceGroup().location
param tags object = {}

param identityName string
param containerAppsEnvironmentName string
param containerRegistryName string
param serviceName string = 'agent'
param exists bool
param openAiDeploymentName string
param openAiEndpoint string
param mcpServerUrl string

resource agentIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}

module app 'core/host/container-app-upsert.bicep' = {
  name: '${serviceName}-container-app-module'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    identityName: agentIdentity.name
    exists: exists
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerRegistryName: containerRegistryName
    ingressEnabled: false
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
        name: 'API_HOST'
        value: 'azure'
      }
      {
        name: 'AZURE_CLIENT_ID'
        value: agentIdentity.properties.clientId
      }
      {
        name: 'MCP_SERVER_URL'
        value: mcpServerUrl
      }
      {
        name: 'RUNNING_IN_PRODUCTION'
        value: 'true'
      }
    ]
  }
}

output identityPrincipalId string = agentIdentity.properties.principalId
output name string = app.outputs.name
output hostName string = app.outputs.hostName
output uri string = app.outputs.uri
output imageName string = app.outputs.imageName
