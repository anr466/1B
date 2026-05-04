#!/bin/bash
# ============================================
# Trading AI Bot - Setup Script
# ============================================
# هذا السكربت يهيئ البيئة الافتراضية ويثبت جميع المتطلبات
# يعمل على Linux/macOS
# ============================================

set -e  # Exit on any error

echo "🚀 Trading AI Bot - Setup Script"
echo "================================"

# 1. Check Python version
echo ""
echo "📋 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1 || echo "unknown")
echo "   Python: $PYTHON_VERSION"

if [[ "$PYTHON_VERSION" != "3.13" ]]; then
    echo "⚠️  Warning: This project was tested with Python 3.13.x"
    echo "   Current version: $PYTHON_VERSION"
    echo "   It may still work, but not guaranteed."
fi

# 2. Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "   ✅ Virtual environment already exists"
else
    python3 -m venv .venv
    echo "   ✅ Virtual environment created"
fi

# 3. Activate and upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
source .venv/bin/activate
pip install --upgrade pip --quiet

# 4. Install requirements
echo ""
echo "📥 Installing requirements..."
if [ -f "requirements-frozen.txt" ]; then
    echo "   Using frozen requirements (exact versions)..."
    pip install -r requirements-frozen.txt --quiet
elif [ -f "requirements.txt" ]; then
    echo "   Using requirements.txt..."
    pip install -r requirements.txt --quiet
else
    echo "   ❌ No requirements file found!"
    exit 1
fi

echo "   ✅ All packages installed"

# 5. Verify installation
echo ""
echo "🔍 Verifying installation..."
source .venv/bin/activate
python3 -c "
import pandas, numpy, pandas_ta, sklearn, xgboost
import fastapi, uvicorn, flask, psycopg2
import jwt, bcrypt, requests, binance.client
import firebase_admin, pytest, psutil, pydantic
print('   ✅ All core packages verified')
" || {
    echo "   ❌ Verification failed!"
    exit 1
}

# 6. Verify project modules
echo ""
echo "🔍 Verifying project modules..."
python3 -c "
import sys
sys.path.insert(0, '.')
modules = [
    'backend.utils.indicator_calculator',
    'backend.core.exit_manager',
    'backend.core.state_manager',
    'backend.core.trading_orchestrator',
    'backend.core.coin_state_analyzer',
    'backend.core.entry_executor',
    'backend.core.mtf_confirmation',
    'backend.core.group_b_system',
    'database.database_manager',
    'backend.core.exit_engine',
    'backend.core.monitoring_engine',
    'backend.core.portfolio_risk_manager',
    'backend.core.cognitive_decision_matrix',
    'backend.core.strategy_router',
    'backend.core.dynamic_coin_selector',
    'backend.core.dual_mode_router',
    'backend.ml.trading_brain',
    'backend.ml.hybrid_learning_system',
    'backend.cognitive.cognitive_orchestrator',
    'backend.cognitive.multi_exit_engine',
    'backend.core.binance_connector',
    'backend.analysis.market_regime_detector',
    'backend.selection',
    'backend.strategies',
]
for mod in modules:
    __import__(mod)
print(f'   ✅ All {len(modules)} project modules verified')
" || {
    echo "   ❌ Project module verification failed!"
    exit 1
}

# 7. Create .env if not exists
echo ""
echo "📝 Checking .env file..."
if [ ! -f ".env" ]; then
    echo "   ⚠️  .env file not found - creating template..."
    cat > .env << 'EOF'
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_ai_bot
DB_USER=postgres
DB_PASSWORD=your_password_here

# Binance API (optional - for real trading)
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_TESTNET=true

# Server
HOST=0.0.0.0
PORT=5000
DEBUG=false

# JWT
JWT_SECRET=your-secret-key-here
JWT_EXPIRATION_HOURS=24

# Firebase (optional - for push notifications)
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
EOF
    echo "   ✅ .env template created - please edit with your values"
else
    echo "   ✅ .env file exists"
fi

# 8. Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p logs logs/audit tmp
echo "   ✅ Directories created"

# 9. Summary
echo ""
echo "================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your database credentials"
echo "  2. Start PostgreSQL: docker-compose up -d postgres"
echo "  3. Run migrations: python3 database/migrations/*.sql"
echo "  4. Start the server: python3 start_server.py"
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo "================================"
