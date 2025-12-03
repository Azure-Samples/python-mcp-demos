targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name which is used to generate a short unique hash for each resource')
param name string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Id of the user or app to assign application roles')
param principalId string = ''

param acaExists bool = false

@description('Location for the OpenAI resource group')
@allowed([
  'canadaeast'
  'eastus'
  'eastus2'
  'francecentral'
  'switzerlandnorth'
  'uksouth'
  'japaneast'
  'northcentralus'
  'australiaeast'
  'swedencentral'
])
@metadata({
  azd: {
    type: 'location'
  }
})
param openAiResourceLocation string

@description('Flag to enable or disable monitoring resources')
param useMonitoring bool = true

@description('Flag to enable or disable the virtual network feature')
param useVnet bool = false

@description('Flag to enable or disable public ingress')
param usePrivateIngress bool = false

var resourceToken = toLower(uniqueString(subscription().id, name, location))
var tags = { 'azd-env-name': name }

resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: '${name}-rg'
  location: location
  tags: tags
}

var prefix = '${name}-${resourceToken}'

var openAiDeploymentName = 'gpt-4o-mini'
var openAiModelName = 'gpt-4o-mini'

// Cosmos DB configuration
var cosmosDbDatabaseName = 'expenses-database'
var cosmosDbContainerName = 'expenses'

module openAi 'br/public:avm/res/cognitive-services/account:0.7.2' = {
  name: 'openai'
  scope: resourceGroup
  params: {
    name: '${resourceToken}-cog'
    location: openAiResourceLocation
    tags: tags
    kind: 'OpenAI'
    customSubDomainName: '${resourceToken}-cog'
    publicNetworkAccess: useVnet ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: useVnet ? 'Deny' : 'Allow'
      bypass: 'AzureServices'
    }
    sku: 'S0'
    diagnosticSettings: useMonitoring
      ? [
          {
            name: 'customSetting'
            workspaceResourceId: logAnalyticsWorkspace.?outputs.resourceId
          }
        ]
      : []
    deployments: [
      {
        name: openAiDeploymentName
        model: {
          format: 'OpenAI'
          name: openAiModelName
          version: '2024-07-18'
        }
        sku: {
          name: 'GlobalStandard'
          capacity: 30
        }
      }
    ]
    disableLocalAuth: true
  }
}

// Cosmos DB for storing expenses
module cosmosDb 'br/public:avm/res/document-db/database-account:0.6.1' = {
  name: 'cosmosdb'
  scope: resourceGroup
  params: {
    name: '${resourceToken}-cosmos'
    location: location
    tags: tags
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    networkRestrictions: {
      ipRules: []
      publicNetworkAccess: useVnet ? 'Disabled' : 'Enabled'
      virtualNetworkRules: []
    }
    sqlDatabases: [
      {
        name: cosmosDbDatabaseName
        containers: [
          {
            name: cosmosDbContainerName
            kind: 'Hash'
            paths: [
              '/category'
            ]
          }
        ]
      }
    ]
  }
}

module logAnalyticsWorkspace 'br/public:avm/res/operational-insights/workspace:0.7.0' = if (useMonitoring) {
  name: 'loganalytics'
  scope: resourceGroup
  params: {
    name: '${prefix}-loganalytics'
    location: location
    tags: tags
    skuName: 'PerGB2018'
    dataRetention: 30
    publicNetworkAccessForIngestion: useVnet ? 'Disabled' : 'Enabled'
    publicNetworkAccessForQuery: useVnet ? 'Disabled' : 'Enabled'
    useResourcePermissions: true
  }
}

// https://learn.microsoft.com/en-us/azure/container-apps/firewall-integration?tabs=consumption-only
module containerAppsNSG 'br/public:avm/res/network/network-security-group:0.5.1' = if (useVnet) {
  name: 'containerAppsNSG'
  scope: resourceGroup
  params: {
    name: '${prefix}-container-apps-nsg'
    location: location
    tags: tags
    securityRules: !usePrivateIngress
      ? [
          {
            name: 'AllowHttpsInbound'
            properties: {
              protocol: 'Tcp'
              sourcePortRange: '*'
              sourceAddressPrefix: 'Internet'
              destinationPortRange: '443'
              destinationAddressPrefix: '*'
              access: 'Allow'
              priority: 100
              direction: 'Inbound'
            }
          }
        ]
      : []
  }
}

module privateEndpointsNSG 'br/public:avm/res/network/network-security-group:0.5.1' = if (useVnet) {
  name: 'privateEndpointsNSG'
  scope: resourceGroup
  params: {
    name: '${prefix}-private-endpoints-nsg'
    location: location
    tags: tags
    securityRules: [
      {
        name: 'AllowVnetInBound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationPortRange: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowAzureLoadBalancerInbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: 'AzureLoadBalancer'
          destinationPortRange: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 110
          direction: 'Inbound'
        }
      }
      {
        name: 'DenyInternetInbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: 'Internet'
          destinationPortRange: '*'
          destinationAddressPrefix: '*'
          access: 'Deny'
          priority: 4096
          direction: 'Inbound'
        }
      }
      {
        name: 'AllowVnetOutbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '*'
          destinationAddressPrefix: 'VirtualNetwork'
          access: 'Allow'
          priority: 100
          direction: 'Outbound'
        }
      }
      {
        name: 'AllowAzureCloudOutbound'
        properties: {
          protocol: 'Tcp'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '443'
          destinationAddressPrefix: 'AzureCloud'
          access: 'Allow'
          priority: 110
          direction: 'Outbound'
        }
      }
      {
        name: 'AllowDnsOutbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '53'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 120
          direction: 'Outbound'
        }
      }
      {
        name: 'DenyInternetOutbound'
        properties: {
          protocol: '*'
          sourcePortRange: '*'
          sourceAddressPrefix: '*'
          destinationPortRange: '*'
          destinationAddressPrefix: 'Internet'
          access: 'Deny'
          priority: 4096
          direction: 'Outbound'
        }
      }
    ]
  }
}

// Virtual network for all resources
module virtualNetwork 'br/public:avm/res/network/virtual-network:0.6.1' = if (useVnet) {
  name: 'vnet'
  scope: resourceGroup
  params: {
    name: '${prefix}-vnet'
    location: location
    tags: tags
    addressPrefixes: [
      '10.0.0.0/16'
    ]
    subnets: [
      {
        name: 'container-apps-subnet'
        addressPrefix: '10.0.0.0/21'
        networkSecurityGroupResourceId: containerAppsNSG!.outputs.resourceId
        delegation: 'Microsoft.App/environments'
      }
      {
        name: 'private-endpoints-subnet'
        addressPrefix: '10.0.8.0/24'
        privateEndpointNetworkPolicies: 'Enabled'
        privateLinkServiceNetworkPolicies: 'Enabled'
        networkSecurityGroupResourceId: privateEndpointsNSG!.outputs.resourceId
      }
      {
        name: 'GatewaySubnet' // Required name for Gateway subnet
        addressPrefix: '10.0.255.0/27' // Using a /27 subnet size which is minimal required size for gateway subnet
      }
      {
        name: 'dns-resolver-subnet' // Dedicated subnet for Azure Private DNS Resolver
        addressPrefix: '10.0.11.0/28' // Original value kept as requested
        delegation: 'Microsoft.Network/dnsResolvers'
      }
    ]
  }
}

// Azure OpenAI Private DNS Zone
module openAiPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (useVnet) {
  name: 'openai-dns-zone'
  scope: resourceGroup
  params: {
    name: 'privatelink.openai.azure.com'
    tags: tags
    virtualNetworkLinks: [
      {
        registrationEnabled: false
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
  }
}

// Log Analytics Private DNS Zone
module logAnalyticsPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (useVnet && useMonitoring) {
  name: 'log-analytics-dns-zone'
  scope: resourceGroup
  params: {
    name: 'privatelink.oms.opinsights.azure.com'
    tags: tags
    virtualNetworkLinks: [
      {
        registrationEnabled: false
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
  }
}

// Additional Log Analytics Private DNS Zone for query endpoint
module logAnalyticsQueryPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (useVnet && useMonitoring) {
  name: 'log-analytics-query-dns-zone'
  scope: resourceGroup
  params: {
    name: 'privatelink.ods.opinsights.azure.com'
    tags: tags
    virtualNetworkLinks: [
      {
        registrationEnabled: false
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
  }
}

// Additional Log Analytics Private DNS Zone for agent service
module logAnalyticsAgentPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (useVnet && useMonitoring) {
  name: 'log-analytics-agent-dns-zone'
  scope: resourceGroup
  params: {
    name: 'privatelink.agentsvc.azure-automation.net'
    tags: tags
    virtualNetworkLinks: [
      {
        registrationEnabled: false
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
  }
}

// Azure Monitor Private DNS Zone
module monitorPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (useVnet && useMonitoring) {
  name: 'monitor-dns-zone'
  scope: resourceGroup
  params: {
    name: 'privatelink.monitor.azure.com'
    tags: tags
    virtualNetworkLinks: [
      {
        registrationEnabled: false
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
  }
}

// Storage Blob Private DNS Zone for Log Analytics solution packs
module blobPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (useVnet && useMonitoring) {
  name: 'blob-dns-zone'
  scope: resourceGroup
  params: {
    name: 'privatelink.blob.${environment().suffixes.storage}'
    tags: tags
    virtualNetworkLinks: [
      {
        registrationEnabled: false
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
  }
}

// Azure Container Registry Private DNS Zone
module acrPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (useVnet) {
  name: 'acr-dns-zone'
  scope: resourceGroup
  params: {
    name: 'privatelink.azurecr.io'
    tags: tags
    virtualNetworkLinks: [
      {
        registrationEnabled: false
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
  }
}

// Container Apps Private DNS Zone
module containerAppsPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (useVnet) {
  name: 'container-apps-dns-zone'
  scope: resourceGroup
  params: {
    name: 'privatelink.${location}.azurecontainerapps.io'
    tags: tags
    virtualNetworkLinks: [
      {
        registrationEnabled: false
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
  }
}

// CosmosDB Private DNS Zone
module cosmosDbPrivateDnsZone 'br/public:avm/res/network/private-dns-zone:0.7.1' = if (useVnet) {
  name: 'cosmosdb-dns-zone'
  scope: resourceGroup
  params: {
    name: 'privatelink.documents.azure.com'
    tags: tags
    virtualNetworkLinks: [
      {
        registrationEnabled: false
        virtualNetworkResourceId: virtualNetwork!.outputs.resourceId
      }
    ]
  }
}

// Container Apps Environment Private Endpoint
// https://learn.microsoft.com/azure/container-apps/how-to-use-private-endpoint
module containerAppsEnvironmentPrivateEndpoint 'br/public:avm/res/network/private-endpoint:0.11.0' = if (useVnet) {
  name: 'containerAppsEnvironmentPrivateEndpointDeployment'
  scope: resourceGroup
  params: {
    name: '${prefix}-containerappsenv-pe'
    location: location
    tags: tags
    subnetResourceId: virtualNetwork!.outputs.subnetResourceIds[1]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          privateDnsZoneResourceId: containerAppsPrivateDnsZone!.outputs.resourceId
        }
      ]
    }
    privateLinkServiceConnections: [
      {
        name: '${prefix}-container-apps-env-pe'
        properties: {
          groupIds: [
            'managedEnvironments'
          ]
          privateLinkServiceId: containerApps.outputs.environmentId
        }
      }
    ]
  }
}

module privateEndpoint 'br/public:avm/res/network/private-endpoint:0.11.0' = if (useVnet) {
  name: 'privateEndpointDeployment'
  scope: resourceGroup
  params: {
    name: '${prefix}-openai-pe'
    location: location
    tags: tags
    subnetResourceId: virtualNetwork!.outputs.subnetResourceIds[1]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          privateDnsZoneResourceId: openAiPrivateDnsZone!.outputs.resourceId
        }
      ]
    }
    privateLinkServiceConnections: [
      {
        name: '${prefix}-openai-pe'
        properties: {
          groupIds: [
            'account'
          ]
          privateLinkServiceId: openAi.outputs.resourceId
        }
      }
    ]
  }
}

// Azure Monitor Private Link Scope
module monitorPrivateLinkScope 'br/public:avm/res/insights/private-link-scope:0.7.1' = if (useVnet && useMonitoring) {
  name: 'monitor-private-link-scope'
  scope: resourceGroup
  params: {
    name: '${prefix}-ampls'
    location: 'global'
    tags: tags
    accessModeSettings: {
      ingestionAccessMode: 'PrivateOnly'
      queryAccessMode: 'PrivateOnly'
    }
    scopedResources: [
      {
        name: 'loganalytics-scoped-resource'
        linkedResourceId: logAnalyticsWorkspace!.outputs.resourceId
      }
    ]
    privateEndpoints: [
      {
        name: 'loganalytics-private-endpoint'
        subnetResourceId: virtualNetwork!.outputs.subnetResourceIds[1]
        privateDnsZoneGroup: {
          privateDnsZoneGroupConfigs: [
            {
              privateDnsZoneResourceId: monitorPrivateDnsZone!.outputs.resourceId
            }
            {
              privateDnsZoneResourceId: logAnalyticsPrivateDnsZone!.outputs.resourceId
            }
            {
              privateDnsZoneResourceId: logAnalyticsQueryPrivateDnsZone!.outputs.resourceId
            }
            {
              privateDnsZoneResourceId: logAnalyticsAgentPrivateDnsZone!.outputs.resourceId
            }
            {
              privateDnsZoneResourceId: blobPrivateDnsZone!.outputs.resourceId
            }
          ]
        }
      }
    ]
  }
}

// Container apps host (including container registry)
module containerApps 'core/host/container-apps.bicep' = {
  name: 'container-apps'
  scope: resourceGroup
  params: {
    name: 'app'
    location: location
    tags: tags
    containerAppsEnvironmentName: '${prefix}-containerapps-env'
    containerRegistryName: '${take(replace(prefix, '-', ''), 42)}registry'
    logAnalyticsWorkspaceName: useMonitoring ? logAnalyticsWorkspace!.outputs.name : ''
    // Reference the virtual network only if useVnet is true
    subnetResourceId: useVnet ? virtualNetwork!.outputs.subnetResourceIds[0] : ''
    vnetName: useVnet ? virtualNetwork!.outputs.name : ''
    subnetName: useVnet ? virtualNetwork!.outputs.subnetNames[0] : ''
    usePrivateIngress: usePrivateIngress
  }
}

// Container Registry Private Endpoint
module acrPrivateEndpoint 'br/public:avm/res/network/private-endpoint:0.11.0' = if (useVnet) {
  name: 'acrPrivateEndpointDeployment'
  scope: resourceGroup
  params: {
    name: '${prefix}-acr-pe'
    location: location
    tags: tags
    subnetResourceId: virtualNetwork!.outputs.subnetResourceIds[1]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          privateDnsZoneResourceId: acrPrivateDnsZone!.outputs.resourceId
        }
      ]
    }
    privateLinkServiceConnections: [
      {
        name: '${prefix}-acr-pe'
        properties: {
          groupIds: [
            'registry'
          ]
          privateLinkServiceId: containerApps.outputs.registryId
        }
      }
    ]
  }
}

// CosmosDB Private Endpoint
module cosmosDbPrivateEndpoint 'br/public:avm/res/network/private-endpoint:0.11.0' = if (useVnet) {
  name: 'cosmosDbPrivateEndpointDeployment'
  scope: resourceGroup
  params: {
    name: '${prefix}-cosmosdb-pe'
    location: location
    tags: tags
    subnetResourceId: virtualNetwork!.outputs.subnetResourceIds[1]
    privateDnsZoneGroup: {
      privateDnsZoneGroupConfigs: [
        {
          privateDnsZoneResourceId: cosmosDbPrivateDnsZone!.outputs.resourceId
        }
      ]
    }
    privateLinkServiceConnections: [
      {
        name: '${prefix}-cosmosdb-pe'
        properties: {
          groupIds: [
            'Sql'
          ]
          privateLinkServiceId: cosmosDb.outputs.resourceId
        }
      }
    ]
  }
}

// Container app frontend
module aca 'aca.bicep' = {
  name: 'aca'
  scope: resourceGroup
  params: {
    name: replace('${take(prefix,19)}-ca', '--', '-')
    location: location
    tags: tags
    identityName: '${prefix}-id-aca'
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerRegistryName: containerApps.outputs.registryName
    openAiDeploymentName: openAiDeploymentName
    openAiEndpoint: openAi.outputs.endpoint
    cosmosDbAccount: cosmosDb.outputs.name
    cosmosDbDatabase: cosmosDbDatabaseName
    cosmosDbContainer: cosmosDbContainerName
    exists: acaExists
  }
}

module openAiRoleUser 'core/security/role.bicep' = {
  scope: resourceGroup
  name: 'openai-role-user'
  params: {
    principalId: principalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    principalType: 'User'
  }
}

module openAiRoleBackend 'core/security/role.bicep' = {
  scope: resourceGroup
  name: 'openai-role-backend'
  params: {
    principalId: aca.outputs.identityPrincipalId
    roleDefinitionId: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    principalType: 'ServicePrincipal'
  }
}

// Cosmos DB Data Contributor role for user
module cosmosDbRoleUser 'core/security/documentdb-sql-role.bicep' = {
  scope: resourceGroup
  name: 'cosmosdb-role-user'
  params: {
    databaseAccountName: cosmosDb.outputs.name
    principalId: principalId
    roleDefinitionId: '/${subscription().id}/resourceGroups/${resourceGroup.name}/providers/Microsoft.DocumentDB/databaseAccounts/${cosmosDb.outputs.name}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
  }
}

// Cosmos DB Data Contributor role for backend
module cosmosDbRoleBackend 'core/security/documentdb-sql-role.bicep' = {
  scope: resourceGroup
  name: 'cosmosdb-role-backend'
  params: {
    databaseAccountName: cosmosDb.outputs.name
    principalId: aca.outputs.identityPrincipalId
    roleDefinitionId: '/${subscription().id}/resourceGroups/${resourceGroup.name}/providers/Microsoft.DocumentDB/databaseAccounts/${cosmosDb.outputs.name}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = resourceGroup.name

output AZURE_OPENAI_CHAT_DEPLOYMENT string = openAiDeploymentName
output AZURE_OPENAI_CHAT_MODEL string = openAiModelName
output AZURE_OPENAI_ENDPOINT string = openAi.outputs.endpoint
output AZURE_OPENAI_RESOURCE string = openAi.outputs.name
output AZURE_OPENAI_RESOURCE_LOCATION string = openAi.outputs.location

output SERVICE_ACA_IDENTITY_PRINCIPAL_ID string = aca.outputs.identityPrincipalId
output SERVICE_ACA_NAME string = aca.outputs.name
output SERVICE_ACA_URI string = aca.outputs.uri
output SERVICE_ACA_IMAGE_NAME string = aca.outputs.imageName

output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerApps.outputs.registryName

output AZURE_COSMOSDB_ACCOUNT string = cosmosDb.outputs.name
output AZURE_COSMOSDB_ENDPOINT string = cosmosDb.outputs.endpoint
output AZURE_COSMOSDB_DATABASE string = cosmosDbDatabaseName
output AZURE_COSMOSDB_CONTAINER string = cosmosDbContainerName
