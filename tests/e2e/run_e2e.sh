#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# E2E Test Runner — Trading AI Bot
# ─────────────────────────────────────────────────────────────────────────────
# الاستخدام:
#   ./tests/e2e/run_e2e.sh              # Backend API tests فقط
#   ./tests/e2e/run_e2e.sh --flutter    # + Flutter integration tests
#   ./tests/e2e/run_e2e.sh --all        # كل الاختبارات

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FLUTTER_DIR="$PROJECT_ROOT/flutter_trading_app"
BACKEND_URL="http://localhost:3002/health"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
PYTHON="${VENV_PYTHON:-python3}"

# ─── Colors ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }

# ─── Flags ───────────────────────────────────────────────────────────────────
RUN_FLUTTER=false
for arg in "$@"; do
  case "$arg" in
    --flutter|--all) RUN_FLUTTER=true ;;
  esac
done

echo ""
echo "═══════════════════════════════════════════════"
echo "   Trading AI Bot — E2E Test Suite"
echo "═══════════════════════════════════════════════"
echo ""

# ─── 1. Check server is running ──────────────────────────────────────────────
info "Checking server at $BACKEND_URL ..."
if ! curl -sf "$BACKEND_URL" > /dev/null 2>&1; then
  error "Backend server is NOT running on port 3002"
  error "Start it with: python start_server.py"
  exit 1
fi
info "✅ Server is running"

# ─── 2. Backend API E2E Tests ────────────────────────────────────────────────
echo ""
info "Running Backend API E2E Tests..."
echo "───────────────────────────────────────────────"

if [ -f "$VENV_PYTHON" ]; then
  PYTHON="$VENV_PYTHON"
fi

# Install pytest + requests if needed
$PYTHON -m pip install pytest requests --quiet 2>/dev/null || true

cd "$PROJECT_ROOT"
$PYTHON -m pytest tests/e2e/test_api_e2e.py \
  -v \
  --tb=short \
  --no-header \
  -p no:warnings \
  2>&1

BACKEND_EXIT=$?

echo "───────────────────────────────────────────────"
if [ $BACKEND_EXIT -eq 0 ]; then
  info "✅ Backend API tests PASSED"
else
  error "❌ Backend API tests FAILED (exit: $BACKEND_EXIT)"
fi

# ─── 3. Flutter Integration Tests ────────────────────────────────────────────
FLUTTER_EXIT=0
if [ "$RUN_FLUTTER" = true ]; then
  echo ""
  info "Running Flutter Integration Tests..."
  echo "───────────────────────────────────────────────"

  if ! command -v flutter &>/dev/null; then
    warn "flutter not found in PATH — skipping Flutter tests"
  else
    # Get connected devices
    DEVICE=$(flutter devices --machine 2>/dev/null | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d[0]['id'] if d else '')" 2>/dev/null || echo "")

    if [ -z "$DEVICE" ]; then
      warn "No Flutter device found — skipping integration tests"
      warn "Start an emulator with: flutter emulators --launch <emulator_id>"
    else
      info "Using device: $DEVICE"
      cd "$FLUTTER_DIR"
      flutter pub get --quiet 2>/dev/null || true
      flutter test \
        integration_test/app_e2e_test.dart \
        -d "$DEVICE" \
        --reporter compact \
        2>&1
      FLUTTER_EXIT=$?
    fi
  fi

  echo "───────────────────────────────────────────────"
  if [ $FLUTTER_EXIT -eq 0 ]; then
    info "✅ Flutter integration tests PASSED"
  else
    error "❌ Flutter integration tests FAILED (exit: $FLUTTER_EXIT)"
  fi
fi

# ─── 4. Summary ──────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════"
echo "   E2E Results Summary"
echo "═══════════════════════════════════════════════"

TOTAL_FAIL=0
[ $BACKEND_EXIT  -ne 0 ] && { error "❌ Backend API:         FAILED"; TOTAL_FAIL=$((TOTAL_FAIL+1)); } \
                          || info  "✅ Backend API:         PASSED"

if [ "$RUN_FLUTTER" = true ]; then
  [ $FLUTTER_EXIT -ne 0 ] && { error "❌ Flutter Integration: FAILED"; TOTAL_FAIL=$((TOTAL_FAIL+1)); } \
                           || info  "✅ Flutter Integration: PASSED"
fi

echo ""
if [ $TOTAL_FAIL -eq 0 ]; then
  info "🎉 All E2E tests passed!"
  exit 0
else
  error "💥 $TOTAL_FAIL test suite(s) failed"
  exit 1
fi
