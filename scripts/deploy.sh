#!/bin/bash
set -euo pipefail

ENVIRONMENT=${1:-staging}
COMPOSE_FILE="docker-compose.yml"
[[ "$ENVIRONMENT" == "production" ]] && COMPOSE_FILE="docker-compose.prod.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIGEST_FILE="/opt/bjs-menu/backups/.last-deploy-digests-${ENVIRONMENT}"

echo "=== Deploying to $ENVIRONMENT ==="
echo "Using compose file: $COMPOSE_FILE"

# Pre-deployment database backup
echo "Creating pre-deployment backup..."
if bash "$SCRIPT_DIR/backup-db.sh"; then
    echo "Pre-deployment backup successful."
else
    echo "WARNING: Pre-deployment backup failed. Continuing deployment..."
fi

# Save current image digests for rollback
echo "Saving current image digests for rollback..."
mkdir -p /opt/bjs-menu/backups
> "$DIGEST_FILE"
for service in $(docker compose -f "$COMPOSE_FILE" config --services 2>/dev/null); do
    digest=$(docker compose -f "$COMPOSE_FILE" images "$service" --format json 2>/dev/null | head -1 | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ID',''))" 2>/dev/null || echo "")
    if [ -n "$digest" ]; then
        echo "${service}=${digest}" >> "$DIGEST_FILE"
    fi
done

# Pull latest images
echo "Pulling latest images..."
docker compose -f "$COMPOSE_FILE" pull

# Deploy with rolling update
echo "Starting services..."
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans

# Wait for health checks
echo "Waiting for services to be healthy..."
if ! bash "$SCRIPT_DIR/health-check.sh" "$ENVIRONMENT"; then
    echo "Health check failed! Rolling back..."
    bash "$SCRIPT_DIR/rollback.sh" "$ENVIRONMENT"
    exit 1
fi

echo "=== Deployment to $ENVIRONMENT successful ==="
