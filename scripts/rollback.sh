#!/bin/bash
set -euo pipefail

ENVIRONMENT=${1:-staging}
COMPOSE_FILE="docker-compose.yml"
[[ "$ENVIRONMENT" == "production" ]] && COMPOSE_FILE="docker-compose.prod.yml"

echo "=== Rolling back $ENVIRONMENT ==="

# Stop current services
docker compose -f "$COMPOSE_FILE" down

# Restart with previous images
docker compose -f "$COMPOSE_FILE" up -d

echo "=== Rollback complete ==="
