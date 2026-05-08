targetScope = 'subscription'

@description('Deployment environment name.')
param environment string = 'dev'

@description('Azure region for bootstrap resources.')
param location string = 'swedencentral'

@description('Target resource group for the simplified platform bootstrap.')
param resourceGroupName string = 'rg-verdecora-simple-dev'

module resourceGroupModule '../modules/resource-group.bicep' = {
  name: 'bootstrap-resource-group'
  params: {
    environment: environment
    location: location
    resourceGroupName: resourceGroupName
  }
}

@description('Bootstrap resource group name.')
output resourceGroupName string = resourceGroupName

@description('Reminder for post-bootstrap operations.')
output nextStep string = 'Bootstrap complete. Deploy infra/modules/main.bicep directly by using GitHub-hosted runners with Azure OIDC against the rg-verdecora-simple resource group.'
