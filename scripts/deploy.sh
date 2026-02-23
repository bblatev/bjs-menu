#!/bin/bash
set -euo pipefail

ENVIRONMENT=${1:-staging}
COMPOSE_FILE="docker-compose.yml"
[[ "$ENVIRONMENT" == "production" ]] && COMPOSE_FILE="docker-compose.prod.yml"

echo "=== Deploying to $ENVIRONMENT ==="
echo "Using compose file: $COMPOSE_FILE"

# Pull latest images
echo "Pulling latest images..."
docker compose -f "$COMPOSE_FILE" pull

# Deploy with rolling update
echo "Starting services..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# Wait for health checks
echo "Waiting for services to be healthy..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/health-check.sh" "$ENVIRONMENT"

if [ $? -ne 0 ]; then
    echo "Health check failed! Rolling back..."
    bash "$SCRIPT_DIR/rollback.sh" "$ENVIRONMENT"
    exit 1
fi

echo "=== Deployment to $ENVIRONMENT successful ==="
