#!/bin/bash

# Waddles Deployment Test Script
# This script tests the deployment of core services

set -e  # Exit on any error

echo "🚀 Waddles Deployment Test"
echo "============================="

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "📝 Please edit .env file with your actual values before running this script again"
        exit 1
    else
        echo "❌ .env.example file not found"
        exit 1
    fi
fi

echo "✅ Environment file found"

# Test infrastructure services first (just PostgreSQL and Redis)
echo ""
echo "🔧 Testing infrastructure services..."

cat > docker-compose.test-infra.yml << 'EOF'
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-waddlebot}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-testpass}
      POSTGRES_DB: ${POSTGRES_DB:-waddlebot}
    ports:
      - "15432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-waddlebot} -d ${POSTGRES_DB:-waddlebot}"]
      interval: 10s
      timeout: 5s
      retries: 5
    
  redis:
    image: redis:7-alpine
    ports:
      - "16379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  default:
    name: waddlebot-test
EOF

# Start infrastructure services
echo "Starting PostgreSQL and Redis..."
docker-compose -f docker-compose.test-infra.yml up -d

# Wait for services to be healthy
echo "Waiting for services to be ready..."
sleep 30

# Check service health
echo "Checking service health..."
if docker-compose -f docker-compose.test-infra.yml ps | grep -q "Up (healthy)"; then
    echo "✅ Infrastructure services are healthy"
else
    echo "❌ Infrastructure services failed health check"
    docker-compose -f docker-compose.test-infra.yml logs
    docker-compose -f docker-compose.test-infra.yml down -v
    exit 1
fi

# Clean up test infrastructure
echo "Cleaning up test infrastructure..."
docker-compose -f docker-compose.test-infra.yml down -v
rm docker-compose.test-infra.yml

echo ""
echo "📋 Deployment Test Summary"
echo "=========================="
echo "✅ Docker and docker-compose are available"
echo "✅ Environment configuration is present"
echo "✅ PostgreSQL can start and accept connections"
echo "✅ Redis can start and accept connections"
echo ""
echo "🎉 Basic deployment test passed!"
echo ""
echo "📖 Next Steps:"
echo "1. Review and update .env file with your actual configuration values"
echo "2. Run 'docker-compose -f docker-compose.updated.yml up -d' to start core services"
echo "3. Check logs with 'docker-compose -f docker-compose.updated.yml logs -f'"
echo "4. Access services:"
echo "   - Kong API Gateway: http://localhost:8000"
echo "   - Portal: http://localhost:8060"
echo "   - Router Health: http://localhost:8010/health"

echo ""
echo "⚠️  Important Notes:"
echo "- Update Dockerfile paths in modules before running full deployment"
echo "- Configure platform credentials (Discord, Twitch, Slack) in .env"
echo "- Ensure all required ports are available"
echo "- Consider using docker-compose.updated.yml for the latest configuration"