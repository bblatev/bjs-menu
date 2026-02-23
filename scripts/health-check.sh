#!/bin/bash
set -euo pipefail

ENVIRONMENT=${1:-staging}
MAX_RETRIES=30
RETRY_INTERVAL=10
HEALTH_URL="http://localhost:8000/health/ready"

echo "Running health checks for $ENVIRONMENT..."

for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        echo "Health check passed (attempt $i/$MAX_RETRIES)"
        exit 0
    fi
    echo "Health check attempt $i/$MAX_RETRIES failed, retrying in ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

echo "Health check failed after $MAX_RETRIES attempts"
exit 1
