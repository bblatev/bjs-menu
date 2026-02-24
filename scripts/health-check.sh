#!/bin/bash
set -euo pipefail

ENVIRONMENT=${1:-staging}
MAX_RETRIES=30
RETRY_INTERVAL=10
BACKEND_URL="http://localhost:8000/health/ready"
FRONTEND_URL="http://localhost:3011/"

echo "Running health checks for $ENVIRONMENT..."

# Wait for backend
echo "Checking backend..."
for i in $(seq 1 $MAX_RETRIES); do
    if curl -sf "$BACKEND_URL" > /dev/null 2>&1; then
        echo "Backend health check passed (attempt $i/$MAX_RETRIES)"
        break
    fi
    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo "ERROR: Backend health check failed after $MAX_RETRIES attempts"
        exit 1
    fi
    echo "  Backend attempt $i/$MAX_RETRIES failed, retrying in ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

# Wait for frontend
echo "Checking frontend..."
FRONTEND_RETRIES=15
for i in $(seq 1 $FRONTEND_RETRIES); do
    if curl -sf "$FRONTEND_URL" > /dev/null 2>&1; then
        echo "Frontend health check passed (attempt $i/$FRONTEND_RETRIES)"
        break
    fi
    if [ "$i" -eq "$FRONTEND_RETRIES" ]; then
        echo "ERROR: Frontend health check failed after $FRONTEND_RETRIES attempts"
        exit 1
    fi
    echo "  Frontend attempt $i/$FRONTEND_RETRIES failed, retrying in ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

# Check database connectivity (via backend readiness)
echo "Checking database connectivity..."
READY_RESPONSE=$(curl -sf "$BACKEND_URL" 2>/dev/null || echo "")
if echo "$READY_RESPONSE" | grep -qi "database.*false\|db.*unhealthy\|error"; then
    echo "WARNING: Backend reports database connectivity issues"
    echo "Response: $READY_RESPONSE"
fi

# Check Redis connectivity (via backend readiness)
if echo "$READY_RESPONSE" | grep -qi "redis.*false\|cache.*unhealthy"; then
    echo "WARNING: Backend reports Redis connectivity issues"
    echo "Response: $READY_RESPONSE"
fi

echo "All health checks passed for $ENVIRONMENT"
exit 0
