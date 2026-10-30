#!/usr/bin/env bash
# ============================================================
#  Vault-ZeroBaran — Quick Start Script
# ============================================================
set -e

cd "$(dirname "$0")"

echo "============================================================"
echo "  Vault-ZeroBaran — Quick Start"
echo "  Self-Knowledge Brain  •  100% Free Tech Stack"
echo "============================================================"
echo

# 1) Virtualenv
if [ ! -d ".venv" ]; then
    echo ">>> Creating Python virtual environment..."
    python3 -m venv .venv
fi
source .venv/bin/activate

# 2) Deps
echo ">>> Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# 3) Env file
if [ ! -f ".env" ]; then
    echo ">>> Copying .env.example → .env"
    cp .env.example .env
    echo ">>> ⚠️  Open .env and fill in your API keys before continuing."
    echo "    • GEMINI_API_KEY      → https://aistudio.google.com/app/apikey"
    echo "    • SUPABASE_URL/KEY    → https://supabase.com"
    echo "    • SUPABASE_DB_URL     → Supabase project Settings → Database"
    echo "    • TELEGRAM_BOT_TOKEN  → @BotFather on Telegram"
    echo
    read -p "Press ENTER after editing .env... "
fi

# 4) DB schema
echo ">>> Ensuring Supabase pgvector schema..."
python scripts/ingest_folder.py --init-db || true

# 5) Launch
echo
echo ">>> Choose what to launch:"
echo "    1) Streamlit Dashboard  (port 8501)"
echo "    2) Telegram Bot"
echo "    3) Ingest ./data/uploads now"
echo "    4) Exit"
echo
read -p "Choice [1-4]: " choice

case "$choice" in
    1) streamlit run ui/streamlit_app.py --server.port=8501 --server.address=0.0.0.0 ;;
    2) python -m bot.telegram_bot ;;
    3) python scripts/ingest_folder.py ;;
    *) echo "Bye." ;;
esac
