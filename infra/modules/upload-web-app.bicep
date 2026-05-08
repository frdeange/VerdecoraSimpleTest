targetScope = 'resourceGroup'

@description('Deployment environment name (dev/test/prod).')
param environment string

@description('Azure region for Container Apps resources.')
param location string

@description('Name of the Log Analytics workspace used by the upload-web Container Apps environment.')
param logAnalyticsWorkspaceName string = 'log-albaranes-${environment}'

@description('Azure Container Registry login server used for the upload-web image.')
param acrLoginServer string

@description('Storage account blob endpoint exposed to upload-web.')
param storageAccountUrl string

@description('Cosmos DB endpoint exposed to upload-web.')
param cosmosEndpoint string

@description('Application Insights connection string injected into upload-web.')
param applicationInsightsConnectionString string

@description('Document Intelligence endpoint exposed to upload-web.')
param docIntellEndpoint string

@description('Key Vault endpoint exposed to upload-web.')
param keyVaultUrl string

@description('Service Bus namespace name used by upload-web.')
param serviceBusNamespaceName string

@description('Optional override for the upload-web image.')
param uploadWebImage string = ''

@description('Enable Easy Auth deployment for upload-web.')
param enableAuth bool = false

@description('Microsoft Entra tenant id used by upload-web Easy Auth.')
param entraTenantId string = subscription().tenantId

@description('Microsoft Entra application client id used by upload-web Easy Auth.')
param entraClientId string = ''

@description('Microsoft Entra application client secret used by upload-web Easy Auth.')
@secure()
param entraClientSecret string = ''

@description('Optional audiences accepted by upload-web Easy Auth. Defaults to api://{entraClientId}.')
param allowedAudiences array = []

@description('Optional Microsoft Entra group object ids allowed to access upload-web.')
param allowedGroupObjectIds array = []

var tags = {
  project: 'verdecora-albaranes'
  env: environment
  service: 'upload-web'
  'managed-by': 'bicep'
}
var managedEnvironmentName = 'acae-upload-web-${environment}'
var resolvedUploadWebImage = empty(uploadWebImage) ? 'mcr.microsoft.com/k8se/quickstart:latest' : uploadWebImage
var useAcrRegistry = !empty(uploadWebImage)
var rawBlobContainerName = 'albaranes-raw'
var serviceBusFullyQualifiedNamespace = '${serviceBusNamespaceName}.servicebus.windows.net'
var serviceBusTopicName = 'albaran-events'
var uploadSessionsContainerName = 'upload-sessions'
var authSecretName = 'microsoft-provider-authentication-secret'
var authEnabled = enableAuth && !empty(entraClientId) && !empty(entraClientSecret)
var resolvedAllowedAudiences = empty(allowedAudiences) ? [
  'api://${entraClientId}'
] : allowedAudiences
var aadValidation = empty(allowedGroupObjectIds)
  ? {
      allowedAudiences: resolvedAllowedAudiences
    }
  : {
      allowedAudiences: resolvedAllowedAudiences
      defaultAuthorizationPolicy: {
        allowedPrincipals: {
          groups: allowedGroupObjectIds
        }
      }
      jwtClaimChecks: {
        allowedGroups: allowedGroupObjectIds
      }
    }

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' existing = {
  name: logAnalyticsWorkspaceName
}

resource managedEnvironment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: managedEnvironmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource uploadWebApp 'Microsoft.App/containerApps@2025-01-01' = {
  name: 'verdecora-upload-web-${environment}'
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: managedEnvironment.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: authEnabled ? [
        {
          name: authSecretName
          value: entraClientSecret
        }
      ] : []
      registries: useAcrRegistry ? [
        {
          server: acrLoginServer
          identity: 'system'
        }
      ] : []
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8000
        transport: 'Auto'
      }
    }
    template: {
      containers: [
        {
          name: 'upload-web'
          image: resolvedUploadWebImage
          env: [
            {
              name: 'STORAGE_ACCOUNT_URL'
              value: storageAccountUrl
            }
            {
              name: 'RAW_BLOB_CONTAINER'
              value: rawBlobContainerName
            }
            {
              name: 'UPLOAD_SESSIONS_CONTAINER'
              value: uploadSessionsContainerName
            }
            {
              name: 'COSMOS_ENDPOINT'
              value: cosmosEndpoint
            }
            {
              name: 'DATABASE_NAME'
              value: 'albaranes-db'
            }
            {
              name: 'COSMOS_DATABASE'
              value: 'albaranes-db'
            }
            {
              name: 'DOCINTELL_ENDPOINT'
              value: docIntellEndpoint
            }
            {
              name: 'SERVICEBUS_FQ_NAMESPACE'
              value: serviceBusFullyQualifiedNamespace
            }
            {
              name: 'SERVICEBUS_TOPIC'
              value: serviceBusTopicName
            }
            {
              name: 'KEY_VAULT_URL'
              value: keyVaultUrl
            }
            {
              name: 'AZURE_TENANT_ID'
              value: subscription().tenantId
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: applicationInsightsConnectionString
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/healthz'
                port: 8000
              }
              initialDelaySeconds: 5
              periodSeconds: 30
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
}

resource uploadWebAuth 'Microsoft.App/containerApps/authConfigs@2025-01-01' = if (authEnabled) {
  parent: uploadWebApp
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      redirectToProvider: 'azureActiveDirectory'
      unauthenticatedClientAction: 'RedirectToLoginPage'
    }
    httpSettings: {
      requireHttps: true
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        login: {
          loginParameters: [
            'scope=openid profile email'
          ]
        }
        registration: {
          clientId: entraClientId
          clientSecretSettingName: authSecretName
          openIdIssuer: '${az.environment().authentication.loginEndpoint}${entraTenantId}/v2.0'
        }
        validation: aadValidation
      }
    }
    login: {
      tokenStore: {
        enabled: true
      }
    }
  }
}

@description('Upload-web container app id.')
output uploadWebAppId string = uploadWebApp.id

@description('Upload-web managed environment id.')
output managedEnvironmentId string = managedEnvironment.id

@description('Upload-web managed environment default domain.')
output managedEnvironmentDefaultDomain string = managedEnvironment.properties.defaultDomain

@description('Upload-web container app name.')
output uploadWebAppName string = uploadWebApp.name

@description('Upload-web public FQDN.')
output uploadWebFqdn string = uploadWebApp.properties.configuration.ingress.fqdn

@description('Upload-web managed identity principal id.')
output uploadWebPrincipalId string = uploadWebApp.identity.principalId
