@description('Name of the Container Apps environment')
param containerAppsEnvironmentName string

@description('Name of the MCP server container app')
param mcpServerAppName string

@description('Name of the Keycloak container app')
param keycloakAppName string

@description('Name for the HTTP route configuration')
param routeConfigName string = 'mcproutes'

resource containerEnv 'Microsoft.App/managedEnvironments@2024-10-02-preview' existing = {
  name: containerAppsEnvironmentName
}

resource mcpServerApp 'Microsoft.App/containerApps@2024-10-02-preview' existing = {
  name: mcpServerAppName
}

resource keycloakApp 'Microsoft.App/containerApps@2024-10-02-preview' existing = {
  name: keycloakAppName
}

// HTTP Route Configuration for rule-based routing
// Routes /auth/* to Keycloak and /* to MCP server
resource httpRouteConfig 'Microsoft.App/managedEnvironments/httpRouteConfigs@2024-10-02-preview' = {
  name: routeConfigName
  parent: containerEnv
  properties: {
    rules: [
      {
        description: 'Keycloak Authentication Server'
        routes: [
          {
            match: {
              pathSeparatedPrefix: '/auth'
            }
            action: {}
          }
        ]
        targets: [
          {
            containerApp: keycloakApp.name
          }
        ]
      }
      {
        description: 'MCP Expenses Server'
        routes: [
          {
            match: {
              prefix: '/'
            }
            action: {}
          }
        ]
        targets: [
          {
            containerApp: mcpServerApp.name
          }
        ]
      }
    ]
  }
}

output fqdn string = httpRouteConfig.properties.fqdn
output routeConfigUrl string = 'https://${httpRouteConfig.properties.fqdn}'
