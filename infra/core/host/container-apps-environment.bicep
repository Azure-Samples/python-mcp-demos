param name string
param location string = resourceGroup().location
param tags object = {}

param logAnalyticsWorkspaceName string = ''

@description('Virtual network name for container apps environment.')
param vnetName string = ''
@description('Subnet name for container apps environment integration.')
param subnetName string = ''
param subnetResourceId string = ''

param usePrivateIngress bool = false

var useVnet = !empty(vnetName) && !empty(subnetName)
var useLogging = !empty(logAnalyticsWorkspaceName)

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = if (useLogging) {
  name: logAnalyticsWorkspaceName
}

module containerAppsEnvironment 'br/public:avm/res/app/managed-environment:0.11.3' = {
  name: take('${name}-aca-env', 64)
  params: {
    name: name
    location: location
    tags: tags
    zoneRedundant: false
    publicNetworkAccess: usePrivateIngress ? 'Disabled' : 'Enabled'
    workloadProfiles: usePrivateIngress
      ? [
          {
            name: 'Consumption'
            workloadProfileType: 'Consumption'
          }
          {
            name: 'Warm'
            workloadProfileType: 'D4'
            minimumCount: 1
            maximumCount: 3
          }
        ]
      : []
    appLogsConfiguration: useLogging
      ? {
          destination: 'log-analytics'
          logAnalyticsConfiguration: {
            customerId: logAnalyticsWorkspace!.properties.customerId
            sharedKey: logAnalyticsWorkspace!.listKeys().primarySharedKey
          }
        }
      : {
          destination: 'azure-monitor'
        }
    internal: useVnet ? usePrivateIngress : false
    infrastructureSubnetResourceId: useVnet ? subnetResourceId : ''
  }
}

output defaultDomain string = containerAppsEnvironment.outputs.defaultDomain
output name string = containerAppsEnvironment.outputs.name
output resourceId string = containerAppsEnvironment.outputs.resourceId
