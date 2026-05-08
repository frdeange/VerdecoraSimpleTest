targetScope = 'resourceGroup'

@description('Deployment environment name (dev/test/prod).')
param environment string

@description('Azure region for Service Bus resources.')
param location string

var tags = {
  project: 'verdecora-albaranes'
  env: environment
  'managed-by': 'bicep'
}

var uniqueSuffix = substring(uniqueString(subscription().subscriptionId, 'verdecora-simple', environment), 0, 6)
var namespaceName = 'sb-vds-${environment}-${uniqueSuffix}'

resource serviceBusNamespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: namespaceName
  location: location
  tags: tags
  sku: {
    name: 'Premium'
    tier: 'Premium'
    capacity: 1
  }
  properties: {
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource ingestionQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'extraccion-queue'
  properties: {}
}

resource extraccionQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'extraccion-in'
  properties: {}
}

resource hitlReviewQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'hitl-review'
  properties: {
    maxDeliveryCount: 10
    deadLetteringOnMessageExpiration: true
    lockDuration: 'PT1M'
    defaultMessageTimeToLive: 'P14D'
  }
}

resource albaranEventsTopic 'Microsoft.ServiceBus/namespaces/topics@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'albaran-events'
  properties: {}
}

resource albaranRecibidoSubscription 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = {
  parent: albaranEventsTopic
  name: 'albaran-recibido'
  properties: {
    maxDeliveryCount: 10
  }
}

resource albaranValidadoSubscription 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = {
  parent: albaranEventsTopic
  name: 'albaran-validado'
  properties: {
    maxDeliveryCount: 10
  }
}

resource hitlDecisionsTopic 'Microsoft.ServiceBus/namespaces/topics@2022-10-01-preview' = {
  parent: serviceBusNamespace
  name: 'hitl-decisions'
  properties: {}
}

resource hitlDecisionsSubscription 'Microsoft.ServiceBus/namespaces/topics/subscriptions@2022-10-01-preview' = {
  parent: hitlDecisionsTopic
  name: 'orchestrator-sub'
  properties: {
    maxDeliveryCount: 10
  }
}

@description('Service Bus namespace id.')
output serviceBusNamespaceId string = serviceBusNamespace.id

@description('Service Bus namespace name.')
output serviceBusNamespaceName string = serviceBusNamespace.name

@description('Service Bus fully qualified namespace.')
output serviceBusFullyQualifiedNamespace string = '${serviceBusNamespace.name}.servicebus.windows.net'

@description('Flow 0 ingestion queue id.')
output ingestionQueueId string = ingestionQueue.id

@description('Flow 0 ingestion queue name.')
output ingestionQueueName string = last(split(ingestionQueue.name, '/'))

@description('Extraction queue id.')
output extraccionQueueId string = extraccionQueue.id

@description('Extraction queue name.')
output extraccionQueueName string = last(split(extraccionQueue.name, '/'))

@description('HITL review queue id.')
output hitlReviewQueueId string = hitlReviewQueue.id

@description('HITL review queue name.')
output hitlReviewQueueName string = last(split(hitlReviewQueue.name, '/'))

@description('Topic id.')
output albaranEventsTopicId string = albaranEventsTopic.id

@description('Subscription (recibido) id.')
output albaranRecibidoSubscriptionId string = albaranRecibidoSubscription.id

@description('Subscription (validado) id.')
output albaranValidadoSubscriptionId string = albaranValidadoSubscription.id

@description('HITL decisions topic name.')
output hitlDecisionsTopicName string = last(split(hitlDecisionsTopic.name, '/'))
