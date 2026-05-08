targetScope = 'resourceGroup'

@description('Deployment environment name (dev/test/prod).')
param environment string

@description('Azure region for Storage resources.')
param location string

@description('Exact origins allowed to call Blob service CORS. Pass the direct upload-web public origin explicitly (for example https://<app-name>.<region>.azurecontainerapps.io or a custom domain).')
param blobCorsAllowedOrigins array = []

var tags = {
  project: 'verdecora-albaranes'
  env: environment
  'managed-by': 'bicep'
}

var uniqueSuffix = substring(uniqueString(subscription().subscriptionId, 'verdecora-simple', environment), 0, 6)
var storageAccountName = 'stvds${environment}${uniqueSuffix}'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_ZRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    isVersioningEnabled: true
    cors: {
      corsRules: length(blobCorsAllowedOrigins) == 0 ? [] : [
        {
          allowedOrigins: blobCorsAllowedOrigins
          allowedMethods: [
            'PUT'
            'OPTIONS'
          ]
          allowedHeaders: [
            '*'
          ]
          exposedHeaders: [
            '*'
          ]
          maxAgeInSeconds: 3600
        }
      ]
    }
  }
}

resource albaranesRawContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'albaranes-raw'
  properties: {
    publicAccess: 'None'
    immutableStorageWithVersioning: {
      enabled: false
    }
  }
}

resource albaranesProcessedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'albaranes-processed'
  properties: {
    publicAccess: 'None'
  }
}

resource dlqContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'dlq'
  properties: {
    publicAccess: 'None'
  }
}

resource lifecyclePolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'tiering'
          enabled: true
          type: 'Lifecycle'
          definition: {
            actions: {
              baseBlob: {
                tierToCool: {
                  daysAfterModificationGreaterThan: 30
                }
              }
            }
            filters: {
              blobTypes: [
                'blockBlob'
              ]
            }
          }
        }
      ]
    }
  }
}

@description('Storage account id.')
output storageAccountId string = storageAccount.id

@description('Storage account name.')
output storageAccountName string = storageAccount.name

@description('Raw container id.')
output albaranesRawContainerId string = albaranesRawContainer.id

@description('Processed container id.')
output albaranesProcessedContainerId string = albaranesProcessedContainer.id

@description('DLQ container id.')
output dlqContainerId string = dlqContainer.id
