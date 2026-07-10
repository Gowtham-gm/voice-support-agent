// infra/main.bicep
// Deploys: Log Analytics workspace, Container Apps Environment, and the API
// as an Azure Container App pulling from Azure Container Registry.
//
// Usage:
//   az deployment group create \
//     --resource-group rg-voice-agent \
//     --template-file infra/main.bicep \
//     --parameters acrName=youracrname appName=voice-support-agent \
//                  openAiKey=$OPENAI_API_KEY jwtSecret=$JWT_SECRET

@description('Location for all resources')
param location string = resourceGroup().location

@description('Name of the container app')
param appName string = 'voice-support-agent'

@description('Existing or new Azure Container Registry name (must be globally unique)')
param acrName string

@description('Container image tag to deploy, e.g. latest or a git sha')
param imageTag string = 'latest'

@secure()
param openAiKey string

@secure()
param jwtSecret string

var acrLoginServer = '${acrName}.azurecr.io'
var imageName = '${acrLoginServer}/${appName}:${imageTag}'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: true }
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${appName}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource containerAppEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${appName}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: acrLoginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
        { name: 'openai-api-key', value: openAiKey }
        { name: 'jwt-secret', value: jwtSecret }
      ]
    }
    template: {
      containers: [
        {
          name: appName
          image: imageName
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            { name: 'OPENAI_API_KEY', secretRef: 'openai-api-key' }
            { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
            { name: 'ENV', value: 'production' }
            { name: 'DEBUG', value: 'false' }
            { name: 'DATABASE_URL', value: 'sqlite:////tmp/voice_agent.db' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/api/v1/health', port: 8000 }
              initialDelaySeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
        rules: [
          {
            name: 'http-scale'
            http: { metadata: { concurrentRequests: '20' } }
          }
        ]
      }
    }
  }
}

output appUrl string = containerApp.properties.configuration.ingress.fqdn
output acrLoginServer string = acrLoginServer
