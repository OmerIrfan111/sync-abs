// ABS Sync — Azure Container Apps deployment.
// Mirrors docker-compose.yml's 7 services, with two real infra decisions:
//  - Postgres and Redis become managed Azure services (no self-hosted DB/cache to operate).
//  - RabbitMQ is dropped entirely: Celery's broker points at the same managed Redis
//    instance instead (celery_app.py already reads RABBITMQ_URL as an override — this
//    needs zero application code changes, just the connection string shape changing
//    from amqp:// to redis://).
targetScope = 'resourceGroup'

@description('Short, unique-enough name used as a prefix for every resource (e.g. "abssync").')
param namePrefix string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Real backend secrets/env vars (everything currently in backend/.env) as one object: { KEY: "value" }. Pass via --parameters backendEnvSecrets=@secrets.json — never commit that file.')
@secure()
param backendEnvSecrets object

@description('Postgres admin password.')
@secure()
param postgresAdminPassword string

@description('Container image tags to deploy — set by the CI/CD workflow on each push, defaults to "latest" for the first manual deploy.')
param backendImageTag string = 'latest'
param frontendImageTag string = 'latest'

var postgresAdminUser = 'syncadmin'
var postgresDbName = 'sync_db'

// ---- Container Registry ----
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: '${namePrefix}acr'
  location: location
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: true }
}

// ---- Log Analytics (required by Container Apps Environment) ----
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ---- Managed Postgres (Flexible Server) ----
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-06-01-preview' = {
  name: '${namePrefix}-pg'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }
}

resource postgresDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-06-01-preview' = {
  parent: postgres
  name: postgresDbName
}

// Allow Azure services (Container Apps) to reach Postgres.
resource postgresFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-06-01-preview' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ---- Managed Redis (cache + Celery broker + Celery result backend) ----
resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: '${namePrefix}-redis'
  location: location
  properties: {
    sku: { name: 'Basic', family: 'C', capacity: 0 }
    enableNonSslPort: false
  }
}

// ---- Container Apps Environment ----
resource containerAppEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-env'
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

// Secrets common to every backend-image container (backend API, celery worker, celery beat).
var redisConnString = '${redis.properties.hostName}:${redis.properties.sslPort}'
var redisPassword = redis.listKeys().primaryKey
var databaseUrl = 'postgresql://${postgresAdminUser}:${postgresAdminPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${postgresDbName}'

var builtInSecrets = [
  { name: 'database-url', value: databaseUrl }
  { name: 'redis-url', value: 'rediss://:${redisPassword}@${redisConnString}/0' }
  // Celery broker on the same Redis instance, DB index 1 so it never collides
  // with the result-backend's DB index 0 above — this is the one piece that
  // replaces RabbitMQ; celery_app.py already reads RABBITMQ_URL as a direct
  // override (see backend/app/core/config.py get_rabbitmq_url), so pointing
  // it at a redis:// URL here needs no application code change.
  { name: 'rabbitmq-url', value: 'rediss://:${redisPassword}@${redisConnString}/1' }
  { name: 'acr-password', value: acr.listCredentials().passwords[0].value }
]

var userSecrets = [for item in items(backendEnvSecrets): {
  name: toLower(replace(item.key, '_', '-'))
  value: item.value
}]

var allSecrets = concat(builtInSecrets, userSecrets)

var userEnvFromSecrets = [for item in items(backendEnvSecrets): {
  name: item.key
  secretRef: toLower(replace(item.key, '_', '-'))
}]

var commonBackendEnv = concat(userEnvFromSecrets, [
  { name: 'DATABASE_URL', secretRef: 'database-url' }
  { name: 'REDIS_URL', secretRef: 'redis-url' }
  { name: 'RABBITMQ_URL', secretRef: 'rabbitmq-url' }
  { name: 'PYTHONPATH', value: '/app' }
])

var registryLoginServer = acr.properties.loginServer

// ---- Backend (FastAPI, external ingress) ----
resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-backend'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
      }
      registries: [
        { server: registryLoginServer, username: acr.name, passwordSecretRef: 'acr-password' }
      ]
      secrets: allSecrets
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: '${registryLoginServer}/syncabs-backend:${backendImageTag}'
          command: ['uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000']
          resources: { cpu: json('1.0'), memory: '2Gi' }
          env: commonBackendEnv
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

// ---- Celery worker (internal only, can scale out) ----
resource celeryWorkerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-celery-worker'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: null
      registries: [
        { server: registryLoginServer, username: acr.name, passwordSecretRef: 'acr-password' }
      ]
      secrets: allSecrets
    }
    template: {
      containers: [
        {
          name: 'celery-worker'
          image: '${registryLoginServer}/syncabs-backend:${backendImageTag}'
          command: ['celery', '-A', 'app.tasks.celery_app', 'worker', '--loglevel=info']
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: commonBackendEnv
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 2 }
    }
  }
}

// ---- Celery beat (internal only — MUST stay single-replica, or every
// scheduled task fires once per replica, e.g. double order ingestion). ----
resource celeryBeatApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-celery-beat'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: null
      registries: [
        { server: registryLoginServer, username: acr.name, passwordSecretRef: 'acr-password' }
      ]
      secrets: allSecrets
    }
    template: {
      containers: [
        {
          name: 'celery-beat'
          image: '${registryLoginServer}/syncabs-backend:${backendImageTag}'
          command: ['celery', '-A', 'app.tasks.celery_app', 'beat', '--loglevel=info']
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          env: commonBackendEnv
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

// ---- Frontend (Next.js, external ingress) ----
resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-frontend'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 3000
        transport: 'http'
      }
      registries: [
        { server: registryLoginServer, username: acr.name, passwordSecretRef: 'acr-password' }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${registryLoginServer}/syncabs-frontend:${frontendImageTag}'
          resources: { cpu: json('0.5'), memory: '1Gi' }
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

output backendUrl string = 'https://${backendApp.properties.configuration.ingress.fqdn}'
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output acrLoginServer string = registryLoginServer
output postgresHost string = postgres.properties.fullyQualifiedDomainName
