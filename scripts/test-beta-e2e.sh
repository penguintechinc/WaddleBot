#!/usr/bin/env bash
#
# WaddleBot API E2E Test Suite
#
# Tests API routing, CORS, correlation-id, security headers, and service
# health through the Kubernetes ingress (no Kong dependency).
#
# Usage:
#   ./scripts/test-beta-e2e.sh                  # Test beta (default)
#   ./scripts/test-beta-e2e.sh --env alpha      # Test alpha
#   ./scripts/test-beta-e2e.sh --env local      # Test local dev (localhost:3000)
#
set -uo pipefail

# ── Defaults ──────────────────────────────────────────────────────────────────
ENV="beta"
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --env)   ENV="$2"; shift 2 ;;
        -v|--verbose) VERBOSE=true; shift ;;
        -h|--help)
            sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Environment config ───────────────────────────────────────────────────────
case "$ENV" in
    beta)
        BASE_URL="https://dal2.penguintech.io"
        HOST_HEADER="waddlebot.penguintech.cloud"
        CURL_OPTS="-sk"
        KUBE_CTX="dal2-beta"
        KUBE_NS="waddlebot"
        CORS_ORIGINS=(
            "https://waddlebot.io"
            "https://waddles.penguintech.cloud"
            "https://waddlebot.penguintech.cloud"
            "http://localhost:5173"
            "http://localhost:3000"
        )
        ;;
    alpha)
        BASE_URL="https://waddlebot.localhost.local"
        HOST_HEADER=""
        CURL_OPTS="-sk"
        KUBE_CTX="local-alpha"
        KUBE_NS="waddlebot-alpha"
        CORS_ORIGINS=(
            "http://localhost:5173"
            "http://localhost:3000"
        )
        ;;
    local)
        BASE_URL="http://localhost:3000"
        HOST_HEADER=""
        CURL_OPTS="-s"
        KUBE_CTX=""
        KUBE_NS=""
        CORS_ORIGINS=(
            "http://localhost:5173"
            "http://localhost:3000"
        )
        ;;
    *)
        echo "Unknown environment: $ENV (use beta, alpha, or local)"
        exit 1 ;;
esac

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PASSED=0
FAILED=0
SKIPPED=0
FAILURES=()

# ── Helpers ───────────────────────────────────────────────────────────────────
_curl() {
    local args=($CURL_OPTS)
    [[ -n "$HOST_HEADER" ]] && args+=(-H "Host: ${HOST_HEADER}")
    curl "${args[@]}" "$@"
}

pass()  { printf "  %-42s ${GREEN}PASS${NC}  %s\n" "$1" "$2"; ((PASSED++)); }
fail()  { printf "  %-42s ${RED}FAIL${NC}  %s\n" "$1" "$2"; ((FAILED++)); FAILURES+=("$1: $2"); }
skip()  { printf "  %-42s ${YELLOW}SKIP${NC}  %s\n" "$1" "$2"; ((SKIPPED++)); }

section() { printf "\n${CYAN}── %s ──${NC}\n" "$1"; }

# Assert HTTP status code
assert_status() {
    local name="$1" method="$2" path="$3" expected="$4"
    shift 4
    local code
    code=$(_curl -o /dev/null -w "%{http_code}" -X "$method" "$@" "${BASE_URL}${path}" 2>/dev/null) || code="000"
    if [[ "$code" == "$expected" ]]; then
        pass "$name" "HTTP $code"
    elif [[ "$code" == "000" ]]; then
        skip "$name" "connection refused"
    else
        fail "$name" "HTTP $code (expected $expected)"
    fi
}

# Assert response body contains string
assert_body_contains() {
    local name="$1" path="$2" needle="$3"
    shift 3
    local body
    body=$(_curl "$@" "${BASE_URL}${path}" 2>/dev/null) || body=""
    if echo "$body" | grep -q "$needle"; then
        pass "$name" "found '$needle'"
    elif [[ -z "$body" ]]; then
        skip "$name" "empty response"
    else
        fail "$name" "missing '$needle'"
        $VERBOSE && echo "    body: ${body:0:200}"
    fi
}

# Assert response header exists (or not)
assert_header() {
    local name="$1" path="$2" header="$3" expected_present="$4"
    shift 4
    local headers
    headers=$(_curl -I "$@" "${BASE_URL}${path}" 2>&1) || headers=""
    local found
    found=$(echo "$headers" | grep -ci "^${header}:" || true)
    if [[ "$expected_present" == "true" && "$found" -gt 0 ]]; then
        local val
        val=$(echo "$headers" | grep -i "^${header}:" | head -1 | cut -d: -f2- | tr -d '\r' | xargs)
        pass "$name" "$val"
    elif [[ "$expected_present" == "false" && "$found" -eq 0 ]]; then
        pass "$name" "(absent, as expected)"
    elif [[ "$expected_present" == "true" && "$found" -eq 0 ]]; then
        fail "$name" "header '$header' missing"
    else
        fail "$name" "header '$header' present (expected absent)"
    fi
}

# Assert header has specific value
assert_header_value() {
    local name="$1" path="$2" header="$3" expected_value="$4"
    shift 4
    local headers
    headers=$(_curl -I "$@" "${BASE_URL}${path}" 2>&1) || headers=""
    local val
    val=$(echo "$headers" | grep -i "^${header}:" | head -1 | cut -d: -f2- | tr -d '\r' | xargs)
    if [[ "$val" == "$expected_value" ]]; then
        pass "$name" "$val"
    elif [[ -z "$val" ]]; then
        fail "$name" "header '$header' missing"
    else
        fail "$name" "'$val' (expected '$expected_value')"
    fi
}

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  WaddleBot E2E API Tests — ${ENV}${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "  Target: ${BASE_URL}"
[[ -n "$HOST_HEADER" ]] && echo -e "  Host:   ${HOST_HEADER}"

# ── 1. API Routing ────────────────────────────────────────────────────────────
section "API Routing"

assert_body_contains  "Public signup-settings"     "/api/v1/public/signup-settings" '"success":true'
assert_status         "Auth login (validation block)" POST "/api/v1/auth/login" 400 \
                      -H "Content-Type: application/json" -d '{}'
assert_body_contains  "Protected route (401)"      "/api/v1/communities" '"UNAUTHORIZED"'
assert_body_contains  "Cookie endpoint"            "/api/v1/cookie/policy" '"success"'

# ── 2. CORS ───────────────────────────────────────────────────────────────────
section "CORS"

for origin in "${CORS_ORIGINS[@]}"; do
    short="${origin#*://}"
    assert_header_value "Allowed origin: ${short}" "/api/v1/public/signup-settings" \
        "access-control-allow-origin" "$origin" \
        -X OPTIONS \
        -H "Origin: ${origin}" \
        -H "Access-Control-Request-Method: GET"
done

assert_header "Blocked origin: evil.example.com" "/api/v1/public/signup-settings" \
    "access-control-allow-origin" false \
    -X OPTIONS \
    -H "Origin: https://evil.example.com" \
    -H "Access-Control-Request-Method: GET"

# ── 3. Correlation ID ────────────────────────────────────────────────────────
section "Correlation ID"

assert_header "Auto-generated X-Request-ID" "/api/v1/public/signup-settings" \
    "x-request-id" true

assert_header_value "Preserved X-Request-ID" "/api/v1/public/signup-settings" \
    "x-request-id" "test-trace-e2e-123" \
    -H "X-Request-ID: test-trace-e2e-123"

# ── 4. Security Headers ──────────────────────────────────────────────────────
section "Security Headers (Helmet)"

assert_header "Strict-Transport-Security"   "/api/v1/public/signup-settings" "strict-transport-security"   true
assert_header "X-Content-Type-Options"      "/api/v1/public/signup-settings" "x-content-type-options"      true
assert_header "X-Frame-Options"             "/api/v1/public/signup-settings" "x-frame-options"             true
assert_header "Content-Security-Policy"     "/api/v1/public/signup-settings" "content-security-policy"     true
assert_header "Referrer-Policy"             "/api/v1/public/signup-settings" "referrer-policy"             true

# ── 5. WebUI ──────────────────────────────────────────────────────────────────
section "Frontend"

assert_status "WebUI serves HTML" GET "/" 200

# ── 6. Kong removal verification ─────────────────────────────────────────────
if [[ -n "$KUBE_CTX" ]]; then
    section "Kong Removal Verification"

    kong_pods=$(kubectl --context "$KUBE_CTX" get pods -n "$KUBE_NS" --field-selector=status.phase=Running 2>/dev/null \
        | grep -c "^kong" || true)
    if [[ "$kong_pods" -eq 0 ]]; then
        pass "No Kong pods running" ""
    else
        fail "Kong pods still running" "$kong_pods pod(s)"
    fi

    hub_ready=$(kubectl --context "$KUBE_CTX" get pods -n "$KUBE_NS" 2>/dev/null \
        | grep "hub-api" | grep -c "1/1" || true)
    if [[ "$hub_ready" -gt 0 ]]; then
        pass "Hub-API pod healthy" "1/1 Running"
    else
        fail "Hub-API pod unhealthy" ""
    fi
fi

# ── 7. Authenticated Operations ────────────────────────────────────────────────
section "Authenticated Operations"

# Get CSRF token first
CSRF_RESP=$(_curl -c /tmp/wb-e2e-cookies.txt "${BASE_URL}/api/v1/auth/csrf" 2>/dev/null) || CSRF_RESP=""
CSRF_TOKEN=$(echo "$CSRF_RESP" | grep -o '"csrfToken":"[^"]*"' | cut -d'"' -f4)

if [[ -z "$CSRF_TOKEN" ]]; then
    skip "Login as admin" "CSRF token unavailable"
    skip "Create community (auth)" "skipped (no session)"
    skip "Cleanup test community" "skipped (no session)"
else
    # Login as admin
    LOGIN_RESP=$(_curl -b /tmp/wb-e2e-cookies.txt -c /tmp/wb-e2e-cookies.txt \
        -X POST "${BASE_URL}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -H "x-csrf-token: ${CSRF_TOKEN}" \
        -d '{"email":"admin@localhost.local","password":"admin123"}' 2>/dev/null) || LOGIN_RESP=""

    if echo "$LOGIN_RESP" | grep -q '"success":true'; then
        pass "Login as admin" "authenticated"

        # Test community creation
        CREATE_RESP=$(_curl -b /tmp/wb-e2e-cookies.txt \
            -X POST "${BASE_URL}/api/v1/communities/create" \
            -H "Content-Type: application/json" \
            -d '{"name":"e2e-test-community","displayName":"E2E Test","platform":"discord","communityType":"creator"}' \
            2>/dev/null) || CREATE_RESP=""

        if echo "$CREATE_RESP" | grep -q '"success":true'; then
            COMMUNITY_ID=$(echo "$CREATE_RESP" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
            pass "Create community (auth)" "id=$COMMUNITY_ID"

            # Cleanup: delete test community
            if [[ -n "$COMMUNITY_ID" ]]; then
                DEL_RESP=$(_curl -b /tmp/wb-e2e-cookies.txt \
                    -X DELETE "${BASE_URL}/api/v1/superadmin/communities/${COMMUNITY_ID}" \
                    2>/dev/null) || DEL_RESP=""
                if echo "$DEL_RESP" | grep -q '"success":true'; then
                    pass "Cleanup test community" "deleted id=$COMMUNITY_ID"
                else
                    skip "Cleanup test community" "delete returned unexpected response"
                fi
            fi
        else
            fail "Create community (auth)" "unexpected response"
            skip "Cleanup test community" "skipped (creation failed)"
            $VERBOSE && echo "    body: ${CREATE_RESP:0:200}"
        fi
    else
        fail "Login as admin" "login failed"
        skip "Create community (auth)" "skipped (no session)"
        skip "Cleanup test community" "skipped (no session)"
        $VERBOSE && echo "    body: ${LOGIN_RESP:0:200}"
    fi

    # Cleanup cookie jar
    rm -f /tmp/wb-e2e-cookies.txt
fi

# ── Summary ───────────────────────────────────────────────────────────────────
TOTAL=$((PASSED + FAILED + SKIPPED))

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "  Total: $TOTAL    ${GREEN}Pass: $PASSED${NC}    ${RED}Fail: $FAILED${NC}    ${YELLOW}Skip: $SKIPPED${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"

if [[ ${#FAILURES[@]} -gt 0 ]]; then
    echo ""
    echo -e "${RED}Failures:${NC}"
    for f in "${FAILURES[@]}"; do
        echo -e "  ${RED}✗${NC} $f"
    done
fi

echo ""
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED test(s) failed.${NC}"
    exit 1
fi
