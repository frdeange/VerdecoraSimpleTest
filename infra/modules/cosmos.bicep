targetScope = 'resourceGroup'

@description('Deployment environment name (dev/test/prod).')
param environment string

@description('Azure region for Cosmos DB resources.')
param location string

var tags = {
  project: 'verdecora-albaranes'
  env: environment
  'managed-by': 'bicep'
}

var uniqueSuffix = substring(uniqueString(subscription().subscriptionId, 'verdecora-simple', environment), 0, 6)
var accountName = 'cosmos-vds-${environment}-${uniqueSuffix}'

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
  }
}

resource albaranesDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosAccount
  name: 'albaranes-db'
  properties: {
    resource: {
      id: 'albaranes-db'
    }
    options: {
      autoscaleSettings: {
        maxThroughput: 10000
      }
    }
  }
}

resource albaranesContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: albaranesDb
  name: 'albaranes'
  properties: {
    resource: {
      id: 'albaranes'
      partitionKey: {
        paths: [
          '/pk'
        ]
        kind: 'Hash'
      }
    }
    options: {}
  }
}

resource tiendasContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: albaranesDb
  name: 'tiendas'
  properties: {
    resource: {
      id: 'tiendas'
      partitionKey: {
        paths: [
          '/tienda_id'
        ]
        kind: 'Hash'
      }
    }
    options: {}
  }
}

resource dlqContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: albaranesDb
  name: 'dlq'
  properties: {
    resource: {
      id: 'dlq'
      partitionKey: {
        paths: [
          '/pk'
        ]
        kind: 'Hash'
      }
    }
    options: {}
  }
}

resource uploadSessionsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: albaranesDb
  name: 'upload-sessions'
  properties: {
    resource: {
      id: 'upload-sessions'
      partitionKey: {
        paths: [
          '/user_oid'
        ]
        kind: 'Hash'
      }
      defaultTtl: 86400
    }
    options: {
      throughput: 400
    }
  }
}

resource processingRecordsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: albaranesDb
  name: 'processing-records'
  properties: {
    resource: {
      id: 'processing-records'
      partitionKey: {
        paths: [
          '/id'
        ]
        kind: 'Hash'
      }
    }
    options: {}
  }
}

@description('Cosmos DB account id.')
output cosmosAccountId string = cosmosAccount.id

@description('Cosmos DB account name.')
output cosmosAccountName string = cosmosAccount.name

@description('Cosmos DB endpoint.')
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint

@description('Cosmos DB database id.')
output albaranesDatabaseId string = albaranesDb.id

@description('Albaranes container id.')
output albaranesContainerId string = albaranesContainer.id

@description('Tiendas container id.')
output tiendasContainerId string = tiendasContainer.id

@description('DLQ container id.')
output dlqContainerId string = dlqContainer.id

@description('Upload sessions container id.')
output uploadSessionsContainerId string = uploadSessionsContainer.id

@description('Processing records container id.')
output processingRecordsContainerId string = processingRecordsContainer.id
