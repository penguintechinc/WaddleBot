#!/bin/bash
# Waddles Alpha Smoke Test
# Tests that all docker-compose services are healthy before deployment
#
# IMPORTANT: This test MUST pass before pushing to beta cluster.
# All services must be healthy - no restarting or unhealthy containers allowed.
#
# Usage: ./tests/alpha-smoke-test.sh
# Exit codes:
#   0 - All services healthy (PASS)
#   1 - One or more services unhealthy/failed (FAIL)
#   2 - Services still starting (WARN - wait and retry)

echo "========================================"
echo "Waddles Alpha Smoke Test"
echo "========================================"
echo ""
echo "Checking container health status..."
echo ""

# Get counts
HEALTHY=$(docker compose ps 2>/dev/null | grep "(healthy)" | wc -l)
STARTING=$(docker compose ps 2>/dev/null | grep "(health: starting)" | wc -l)
UNHEALTHY=$(docker compose ps 2>/dev/null | grep -E "(unhealthy|Restarting)" | wc -l)

# List healthy services
echo "Healthy services ($HEALTHY):"
docker compose ps 2>/dev/null | grep "(healthy)" | awk '{print "  ✓ " $1}'
echo ""

# List starting services
if [ "$STARTING" -gt 0 ]; then
    echo "Starting services ($STARTING):"
    docker compose ps 2>/dev/null | grep "(health: starting)" | awk '{print "  ○ " $1}'
    echo ""
fi

# List failed services
if [ "$UNHEALTHY" -gt 0 ]; then
    echo "Failed services ($UNHEALTHY):"
    docker compose ps 2>/dev/null | grep -E "(unhealthy|Restarting)" | awk '{print "  ✗ " $1}'
    echo ""
fi

echo "========================================"
echo "Summary"
echo "========================================"
echo "Healthy:  $HEALTHY"
echo "Starting: $STARTING"
echo "Failed:   $UNHEALTHY"
echo ""

# Check for failures
if [ "$UNHEALTHY" -gt 0 ]; then
    echo "ALPHA TEST FAILED"
    echo "Fix unhealthy services before pushing to beta."
    exit 1
fi

# Check if any services still starting
if [ "$STARTING" -gt 0 ]; then
    echo "WARNING: Some services still starting"
    echo "Wait and re-run test, or check if they become healthy."
    exit 2
fi

# All healthy
echo "ALPHA TEST PASSED"
echo "All $HEALTHY services are healthy!"
exit 0
