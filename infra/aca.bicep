param name string
param location string = resourceGroup().location
param tags object = {}

param identityName string
param containerAppsEnvironmentName string
param containerRegistryName string
param serviceName string = 'aca'
param exists bool
param openAiDeploymentName string
param openAiEndpoint string
param cosmosDbAccount string
param cosmosDbDatabase string
param cosmosDbContainer string

resource acaIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: identityName
  location: location
}


module app 'core/host/container-app-upsert.bicep' = {
  name: '${serviceName}-container-app-module'
  params: {
    name: name
    location: location
    tags: union(tags, { 'azd-service-name': serviceName })
    identityName: acaIdentity.name
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
        value: acaIdentity.properties.clientId
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
    ]
    targetPort: 8000
  }
}

output identityPrincipalId string = acaIdentity.properties.principalId
output name string = app.outputs.name
output hostName string = app.outputs.hostName
output uri string = app.outputs.uri
output imageName string = app.outputs.imageName
