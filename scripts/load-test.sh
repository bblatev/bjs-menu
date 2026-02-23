#!/bin/bash
set -euo pipefail

TARGET=${1:-http://localhost:8000}
USERS=${2:-50}
SPAWN_RATE=${3:-5}
DURATION=${4:-300}

echo "=== Load Testing $TARGET with $USERS users ==="
echo "Spawn rate: $SPAWN_RATE/s, Duration: ${DURATION}s"

locust -f backend/tests/performance/locustfile.py \
    --host="$TARGET" \
    --users="$USERS" \
    --spawn-rate="$SPAWN_RATE" \
    --run-time="${DURATION}s" \
    --headless \
    --csv=load_test_results \
    --html=load_test_report.html

echo "=== Load test complete. Report: load_test_report.html ==="
