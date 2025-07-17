# WaddleBot Deployment Guide

## Overview

This guide covers the complete deployment of WaddleBot's multi-platform chat bot system using Docker, Kubernetes, and CI/CD pipelines. WaddleBot follows a microservices architecture with separate containers for core services, collectors, and interaction modules.

## Prerequisites

### System Requirements

- **Docker**: Version 20.04 or higher
- **Kubernetes**: Version 1.24 or higher (for K8s deployment)
- **PostgreSQL**: Version 13 or higher
- **Redis**: Version 6 or higher
- **Minimum Resources**: 4 CPU cores, 8GB RAM, 50GB storage

### Required Services

1. **Database Services**
   - PostgreSQL primary database
   - PostgreSQL read replica (optional, recommended for production)
   - Redis for session management and caching

2. **External Services**
   - Kong API Gateway
   - Container registry (Docker Hub, GHCR, etc.)
   - Monitoring stack (Prometheus, Grafana)

## Deployment Methods

### 1. Docker Compose (Development/Testing)

#### Environment Configuration

Create a `.env` file with all required environment variables:

```bash
# Database Configuration
POSTGRES_USER=waddlebot
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=waddlebot
DATABASE_URL=postgresql://waddlebot:secure_password_here@db:5432/waddlebot

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=redis_password_here

# Module Versions
MODULE_VERSION=1.0.0

# Core Modules
MODULE_NAME_ROUTER=router
MODULE_NAME_MARKETPLACE=marketplace
MODULE_NAME_PORTAL=portal

# Collector Modules
MODULE_NAME_TWITCH=twitch
MODULE_NAME_DISCORD=discord
MODULE_NAME_SLACK=slack

# Interaction Modules
MODULE_NAME_AI=ai_interaction
MODULE_NAME_INVENTORY=inventory_interaction_module
MODULE_NAME_LABELS=labels_core
MODULE_NAME_ALIAS=alias_interaction
MODULE_NAME_SHOUTOUT=shoutout_interaction

# Kong Admin Broker
MODULE_NAME_KONG_BROKER=kong_admin_broker

# API URLs
CORE_API_URL=http://router:8000
ROUTER_API_URL=http://router:8000/router
CONTEXT_API_URL=http://router:8000/api/context
REPUTATION_API_URL=http://router:8000/api/reputation

# Performance Settings
ROUTER_MAX_WORKERS=20
ROUTER_MAX_CONCURRENT=100
MAX_WORKERS=20
CACHE_TTL=300
REQUEST_TIMEOUT=30
MAX_LABELS_PER_ITEM=5

# Platform API Keys (Set your actual values)
TWITCH_APP_ID=your_twitch_app_id
TWITCH_APP_SECRET=your_twitch_app_secret
TWITCH_WEBHOOK_SECRET=your_webhook_secret

DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_APPLICATION_ID=your_discord_app_id
DISCORD_PUBLIC_KEY=your_discord_public_key

SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_APP_TOKEN=xapp-your-slack-app-token
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
SLACK_SIGNING_SECRET=your_slack_signing_secret

# AI Configuration
AI_PROVIDER=ollama
AI_HOST=http://ollama:11434
AI_MODEL=llama3.2
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=500

# Logging Configuration
LOG_LEVEL=INFO
LOG_DIR=/var/log/waddlebotlog
ENABLE_SYSLOG=false
SYSLOG_HOST=localhost
SYSLOG_PORT=514
SYSLOG_FACILITY=LOCAL0

# Kong Configuration
KONG_ADMIN_URL=http://kong:8001
KONG_ADMIN_USERNAME=admin
KONG_ADMIN_PASSWORD=admin_password

# Broker Configuration
BROKER_SECRET_KEY=waddlebot_broker_secret_key_change_me_in_production
BROKER_API_KEY=wbot_broker_master_key_placeholder
```

#### Deploy with Docker Compose

```bash
# Clone the repository
git clone https://github.com/your-org/WaddleBot.git
cd WaddleBot

# Create and configure environment file
cp .env.example .env
# Edit .env with your configuration

# Create log directory
sudo mkdir -p /var/log/waddlebotlog
sudo chown $USER:$USER /var/log/waddlebotlog

# Build and start services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f router
```

### 2. Kubernetes Deployment (Production)

#### Namespace Setup

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: waddlebot
  labels:
    name: waddlebot
```

#### Secret Management

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: waddlebot-secrets
  namespace: waddlebot
type: Opaque
stringData:
  database-url: "postgresql://user:password@postgres:5432/waddlebot"
  redis-password: "redis_password_here"
  twitch-app-secret: "your_twitch_app_secret"
  discord-bot-token: "your_discord_bot_token"
  slack-client-secret: "your_slack_client_secret"
  broker-secret-key: "waddlebot_broker_secret_key"
```

#### ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: waddlebot-config
  namespace: waddlebot
data:
  LOG_LEVEL: "INFO"
  MAX_WORKERS: "20"
  CACHE_TTL: "300"
  MODULE_VERSION: "1.0.0"
  AI_PROVIDER: "ollama"
  AI_MODEL: "llama3.2"
```

#### Core Services Deployment

```yaml
# router-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: router
  namespace: waddlebot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: router
  template:
    metadata:
      labels:
        app: router
    spec:
      containers:
      - name: router
        image: ghcr.io/your-org/waddlebot/router:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: waddlebot-secrets
              key: database-url
        - name: REDIS_HOST
          value: "redis"
        - name: MODULE_NAME
          value: "router"
        envFrom:
        - configMapRef:
            name: waddlebot-config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /router/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /router/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: log-volume
          mountPath: /var/log/waddlebotlog
      volumes:
      - name: log-volume
        persistentVolumeClaim:
          claimName: waddlebot-logs-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: router
  namespace: waddlebot
spec:
  selector:
    app: router
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

#### Horizontal Pod Autoscaler

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: router-hpa
  namespace: waddlebot
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: router
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

#### Persistent Storage

```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: waddlebot-logs-pvc
  namespace: waddlebot
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
  storageClassName: fast-ssd
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-data-pvc
  namespace: waddlebot
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 100Gi
  storageClassName: fast-ssd
```

#### Deploy to Kubernetes

```bash
# Apply namespace and basic resources
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/pvc.yaml

# Deploy core services
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/router-deployment.yaml
kubectl apply -f k8s/marketplace-deployment.yaml

# Deploy collectors
kubectl apply -f k8s/twitch-deployment.yaml
kubectl apply -f k8s/discord-deployment.yaml
kubectl apply -f k8s/slack-deployment.yaml

# Deploy interaction modules
kubectl apply -f k8s/ai-interaction-deployment.yaml
kubectl apply -f k8s/inventory-interaction-deployment.yaml
kubectl apply -f k8s/labels-core-deployment.yaml

# Deploy autoscaling
kubectl apply -f k8s/hpa.yaml

# Check deployment status
kubectl get pods -n waddlebot
kubectl get services -n waddlebot
```

## CI/CD Pipeline Setup

### GitHub Actions Configuration

The repository includes comprehensive GitHub Actions workflows:

1. **containers.yml**: Builds and tests all container modules
2. **ci-cd.yml**: Main CI/CD pipeline with security scanning
3. **android.yml**: Android app building and testing
4. **desktop-bridge.yml**: Golang desktop bridge compilation

#### Secrets Configuration

Configure these secrets in your GitHub repository:

```bash
# Container Registry
REGISTRY_USERNAME=your_registry_username
REGISTRY_PASSWORD=your_registry_password

# Kubernetes
KUBE_CONFIG=base64_encoded_kubeconfig

# Monitoring
GRAFANA_API_KEY=your_grafana_api_key
PROMETHEUS_URL=your_prometheus_url

# Security Scanning
SNYK_TOKEN=your_snyk_token
CODECOV_TOKEN=your_codecov_token
```

### Automated Deployment

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]
    tags: [ 'v*' ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'v1.24.0'
      
      - name: Configure kubectl
        run: |
          echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
          export KUBECONFIG=kubeconfig
      
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/router router=ghcr.io/${{ github.repository }}/router:${{ github.sha }} -n waddlebot
          kubectl set image deployment/marketplace marketplace=ghcr.io/${{ github.repository }}/marketplace:${{ github.sha }} -n waddlebot
          kubectl rollout status deployment/router -n waddlebot
          kubectl rollout status deployment/marketplace -n waddlebot
```

## Monitoring and Observability

### Prometheus Configuration

```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    
    scrape_configs:
    - job_name: 'waddlebot-router'
      static_configs:
      - targets: ['router.waddlebot:8000']
      metrics_path: '/router/metrics'
    
    - job_name: 'waddlebot-inventory'
      static_configs:
      - targets: ['inventory-interaction.waddlebot:8024']
      metrics_path: '/metrics'
    
    rule_files:
    - "/etc/prometheus/rules/*.yml"
    
    alerting:
      alertmanagers:
      - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboards

```json
{
  "dashboard": {
    "title": "WaddleBot Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(waddlebot_requests_total[5m])",
            "legendFormat": "{{module}} - {{method}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(waddlebot_errors_total[5m]) / rate(waddlebot_requests_total[5m]) * 100",
            "legendFormat": "Error Rate %"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(waddlebot_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### Log Aggregation with ELK Stack

```yaml
# elasticsearch-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: elasticsearch
  namespace: logging
spec:
  replicas: 3
  selector:
    matchLabels:
      app: elasticsearch
  template:
    metadata:
      labels:
        app: elasticsearch
    spec:
      containers:
      - name: elasticsearch
        image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
        env:
        - name: discovery.type
          value: single-node
        - name: ES_JAVA_OPTS
          value: "-Xms2g -Xmx2g"
        ports:
        - containerPort: 9200
        volumeMounts:
        - name: elasticsearch-data
          mountPath: /usr/share/elasticsearch/data
      volumes:
      - name: elasticsearch-data
        persistentVolumeClaim:
          claimName: elasticsearch-pvc
```

## Security Configuration

### Network Policies

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: waddlebot-network-policy
  namespace: waddlebot
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: waddlebot
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: waddlebot
  - to: []
    ports:
    - protocol: TCP
      port: 5432  # PostgreSQL
    - protocol: TCP
      port: 6379  # Redis
    - protocol: TCP
      port: 443   # HTTPS
    - protocol: TCP
      port: 53    # DNS
    - protocol: UDP
      port: 53    # DNS
```

### Pod Security Standards

```yaml
# pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: waddlebot-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## Backup and Recovery

### Database Backup

```bash
#!/bin/bash
# backup-database.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/backups/waddlebot_backup_${DATE}.sql"

# Create backup
kubectl exec -n waddlebot postgres-primary-0 -- pg_dump -U waddlebot waddlebot > "${BACKUP_FILE}"

# Compress backup
gzip "${BACKUP_FILE}"

# Upload to S3 (optional)
aws s3 cp "${BACKUP_FILE}.gz" s3://waddlebot-backups/

# Cleanup old backups (keep last 30 days)
find /backups -name "waddlebot_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
```

### Configuration Backup

```bash
#!/bin/bash
# backup-config.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/config_${DATE}"

mkdir -p "${BACKUP_DIR}"

# Backup Kubernetes resources
kubectl get secrets -n waddlebot -o yaml > "${BACKUP_DIR}/secrets.yaml"
kubectl get configmaps -n waddlebot -o yaml > "${BACKUP_DIR}/configmaps.yaml"
kubectl get deployments -n waddlebot -o yaml > "${BACKUP_DIR}/deployments.yaml"
kubectl get services -n waddlebot -o yaml > "${BACKUP_DIR}/services.yaml"

# Create archive
tar -czf "${BACKUP_DIR}.tar.gz" "${BACKUP_DIR}"
rm -rf "${BACKUP_DIR}"

echo "Configuration backup completed: ${BACKUP_DIR}.tar.gz"
```

## Scaling Guidelines

### Horizontal Scaling

1. **Router Module**
   - Scale based on CPU usage (target: 70%)
   - Min replicas: 3, Max replicas: 10
   - Consider database connection limits

2. **Collector Modules**
   - Scale based on platform activity
   - Use coordination system for load distribution
   - Monitor claim utilization

3. **Interaction Modules**
   - Scale based on request volume
   - Consider AI provider rate limits
   - Monitor response times

### Vertical Scaling

1. **Resource Limits**
   - Start with modest limits and increase based on monitoring
   - Monitor memory usage patterns
   - Consider JVM/Python GC tuning

2. **Storage Scaling**
   - Monitor log volume growth
   - Implement log retention policies
   - Consider archival strategies

## Troubleshooting

### Common Issues

1. **Service Discovery Problems**
   ```bash
   # Check DNS resolution
   kubectl exec -n waddlebot router-xxx -- nslookup postgres
   
   # Check service endpoints
   kubectl get endpoints -n waddlebot
   ```

2. **Database Connection Issues**
   ```bash
   # Check database connectivity
   kubectl exec -n waddlebot router-xxx -- nc -zv postgres 5432
   
   # Review connection pool settings
   kubectl logs -n waddlebot router-xxx | grep "connection"
   ```

3. **Log Volume Issues**
   ```bash
   # Check log disk usage
   kubectl exec -n waddlebot router-xxx -- df -h /var/log/waddlebotlog
   
   # Cleanup old logs
   kubectl exec -n waddlebot router-xxx -- find /var/log/waddlebotlog -name "*.log.*" -mtime +7 -delete
   ```

### Health Check Endpoints

```bash
# Check all service health
for service in router marketplace inventory-interaction; do
  echo "Checking $service..."
  kubectl exec -n waddlebot deploy/$service -- curl -f http://localhost:8000/health
done
```

## Maintenance

### Update Procedures

1. **Rolling Updates**
   ```bash
   # Update router with zero downtime
   kubectl set image deployment/router router=ghcr.io/org/waddlebot/router:v1.1.0 -n waddlebot
   kubectl rollout status deployment/router -n waddlebot
   ```

2. **Database Migrations**
   ```bash
   # Run database migrations
   kubectl create job migrate-$(date +%s) --from=cronjob/database-migrate -n waddlebot
   kubectl wait --for=condition=complete job/migrate-$(date +%s) -n waddlebot
   ```

3. **Configuration Updates**
   ```bash
   # Update configuration
   kubectl apply -f k8s/configmap.yaml
   kubectl rollout restart deployment/router -n waddlebot
   ```

### Monitoring Checklist

- [ ] All pods running and healthy
- [ ] Database connections stable
- [ ] Log aggregation working
- [ ] Metrics collection active
- [ ] Alerts configured and firing correctly
- [ ] Backup procedures tested
- [ ] Security scans passing
- [ ] Performance within acceptable ranges

This deployment guide provides a comprehensive foundation for running WaddleBot in production environments with proper monitoring, security, and scalability considerations.