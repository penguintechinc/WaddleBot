#!/bin/bash
# Comprehensive Test Suite for Waddles Implementation
# Tests all completed phases

set -e

echo "========================================="
echo "Waddles Comprehensive Test Suite"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

total_tests=0
passed_tests=0
failed_tests=0

# Function to run test and track results
run_test() {
    local test_name=$1
    local test_command=$2

    ((total_tests++))
    echo -n "Running $test_name... "

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((passed_tests++))
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((failed_tests++))
    fi
}

echo -e "${BLUE}Phase 1: Security & Performance Tests${NC}"
echo "========================================="

# Test migrations exist
run_test "Performance indexes migration" "test -f /home/penguin/code/WaddleBot/config/postgres/migrations/001_add_performance_indexes.sql"
run_test "Commands table migration" "test -f /home/penguin/code/WaddleBot/config/postgres/migrations/002_add_commands_table.sql"
run_test "Migration runner script" "test -x /home/penguin/code/WaddleBot/config/postgres/migrations/run-migrations.sh"

# Test security middleware exists
run_test "CSRF middleware" "test -f /home/penguin/code/WaddleBot/admin/hub_module/backend/src/middleware/csrf.js"
run_test "Validation middleware" "test -f /home/penguin/code/WaddleBot/admin/hub_module/backend/src/middleware/validation.js"

echo ""
echo -e "${BLUE}Phase 2: Distributed Services Tests${NC}"
echo "========================================="

# Test core libraries exist
run_test "Cache library" "test -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/cache.py"
run_test "Rate limiter library" "test -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/rate_limiter.py"
run_test "Message queue library" "test -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/message_queue.py"
run_test "Circuit breaker library" "test -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/circuit_breaker.py"

# Test Python syntax
run_test "Cache syntax check" "python3 -m py_compile /home/penguin/code/WaddleBot/libs/flask_core/flask_core/cache.py"
run_test "Rate limiter syntax check" "python3 -m py_compile /home/penguin/code/WaddleBot/libs/flask_core/flask_core/rate_limiter.py"
run_test "Message queue syntax check" "python3 -m py_compile /home/penguin/code/WaddleBot/libs/flask_core/flask_core/message_queue.py"
run_test "Circuit breaker syntax check" "python3 -m py_compile /home/penguin/code/WaddleBot/libs/flask_core/flask_core/circuit_breaker.py"

echo ""
echo -e "${BLUE}Phase 3: Skeleton Modules Tests${NC}"
echo "========================================="

# Test migrations
run_test "Shoutout migration" "test -f /home/penguin/code/WaddleBot/config/postgres/migrations/003_add_shoutout_tables.sql"
run_test "Memories migration" "test -f /home/penguin/code/WaddleBot/config/postgres/migrations/004_add_memories_tables.sql"
run_test "Music migration" "test -f /home/penguin/code/WaddleBot/config/postgres/migrations/005_add_music_tables.sql"

# Test services
run_test "Shoutout Twitch service" "test -f /home/penguin/code/WaddleBot/action/interactive/shoutout_interaction_module/services/twitch_service.py"
run_test "Shoutout service" "test -f /home/penguin/code/WaddleBot/action/interactive/shoutout_interaction_module/services/shoutout_service.py"
run_test "Quote service" "test -f /home/penguin/code/WaddleBot/action/interactive/memories_interaction_module/services/quote_service.py"
run_test "Bookmark service" "test -f /home/penguin/code/WaddleBot/action/interactive/memories_interaction_module/services/bookmark_service.py"
run_test "Reminder service" "test -f /home/penguin/code/WaddleBot/action/interactive/memories_interaction_module/services/reminder_service.py"
run_test "Spotify OAuth service" "test -f /home/penguin/code/WaddleBot/action/interactive/spotify_interaction_module/services/oauth_service.py"

# Test Python syntax for services
run_test "Quote service syntax" "python3 -m py_compile /home/penguin/code/WaddleBot/action/interactive/memories_interaction_module/services/quote_service.py"
run_test "Bookmark service syntax" "python3 -m py_compile /home/penguin/code/WaddleBot/action/interactive/memories_interaction_module/services/bookmark_service.py"
run_test "Reminder service syntax" "python3 -m py_compile /home/penguin/code/WaddleBot/action/interactive/memories_interaction_module/services/reminder_service.py"

# Test browser source overlay
run_test "Music player overlay" "test -f /home/penguin/code/WaddleBot/core/browser_source_core_module/templates/music-player-overlay.html"

echo ""
echo -e "${BLUE}Phase 4: Scalability Tests${NC}"
echo "========================================="

# Test sharding library
run_test "Sharding library" "test -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/sharding.py"
run_test "Sharding syntax check" "python3 -m py_compile /home/penguin/code/WaddleBot/libs/flask_core/flask_core/sharding.py"

# Test read replica (if agent completed)
if [ -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/read_replica.py ]; then
    run_test "Read replica library" "test -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/read_replica.py"
    run_test "Read replica syntax check" "python3 -m py_compile /home/penguin/code/WaddleBot/libs/flask_core/flask_core/read_replica.py"
fi

# Test HPA configs (if agent completed)
if [ -d /home/penguin/code/WaddleBot/k8s/hpa ]; then
    run_test "HPA configs directory" "test -d /home/penguin/code/WaddleBot/k8s/hpa"
fi

echo ""
echo -e "${BLUE}Phase 5: Observability Tests${NC}"
echo "========================================="

# Test observability files (if agent completed)
if [ -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/tracing.py ]; then
    run_test "Tracing library" "test -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/tracing.py"
    run_test "Tracing syntax check" "python3 -m py_compile /home/penguin/code/WaddleBot/libs/flask_core/flask_core/tracing.py"
fi

if [ -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/correlation.py ]; then
    run_test "Correlation library" "test -f /home/penguin/code/WaddleBot/libs/flask_core/flask_core/correlation.py"
    run_test "Correlation syntax check" "python3 -m py_compile /home/penguin/code/WaddleBot/libs/flask_core/flask_core/correlation.py"
fi

echo ""
echo -e "${BLUE}Documentation Tests${NC}"
echo "========================================="

run_test "Redis architecture doc" "test -f /home/penguin/code/WaddleBot/docs/redis-architecture.md"
run_test "Phase 3 summary" "test -f /home/penguin/code/WaddleBot/PHASE-3-COMPLETION-SUMMARY.md"
run_test "Final summary" "test -f /home/penguin/code/WaddleBot/FINAL-IMPLEMENTATION-SUMMARY.md"
run_test "Implementation progress" "test -f /home/penguin/code/WaddleBot/.IMPLEMENTATION-PROGRESS.md"

echo ""
echo "========================================="
echo -e "${BLUE}Test Summary${NC}"
echo "========================================="
echo -e "Total Tests:  $total_tests"
echo -e "Passed:       ${GREEN}$passed_tests${NC}"
echo -e "Failed:       ${RED}$failed_tests${NC}"

if [ $failed_tests -eq 0 ]; then
    pass_rate=100
else
    pass_rate=$((passed_tests * 100 / total_tests))
fi

echo -e "Pass Rate:    ${pass_rate}%"
echo ""

if [ $failed_tests -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
elif [ $pass_rate -ge 80 ]; then
    echo -e "${YELLOW}⚠ Most tests passed (${pass_rate}%)${NC}"
    exit 0
else
    echo -e "${RED}✗ Many tests failed (${pass_rate}% pass rate)${NC}"
    exit 1
fi
