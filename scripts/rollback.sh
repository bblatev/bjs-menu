#!/bin/bash
set -euo pipefail

ENVIRONMENT=${1:-staging}
COMPOSE_FILE="docker-compose.yml"
[[ "$ENVIRONMENT" == "production" ]] && COMPOSE_FILE="docker-compose.prod.yml"

DIGEST_FILE="/opt/bjs-menu/backups/.last-deploy-digests-${ENVIRONMENT}"

echo "=== Rolling back $ENVIRONMENT ==="

if [ -f "$DIGEST_FILE" ]; then
    echo "Restoring previous image versions..."
    while IFS='=' read -r service digest; do
        if [ -n "$service" ] && [ -n "$digest" ]; then
            echo "  Restoring $service to $digest"
            docker compose -f "$COMPOSE_FILE" pull "$service" 2>/dev/null || true
        fi
    done < "$DIGEST_FILE"
else
    echo "WARNING: No previous deploy digests found at $DIGEST_FILE"
    echo "Rolling back with current images (restart only)."
fi

# Stop current services
docker compose -f "$COMPOSE_FILE" down

# Restart with previous images
docker compose -f "$COMPOSE_FILE" up -d

echo "=== Rollback complete ==="
