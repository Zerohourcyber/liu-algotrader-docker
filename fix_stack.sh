#!/usr/bin/env bash
set -euo pipefail

echo "🔧 1) Patching Dockerfile.streamlit…"
cat > Dockerfile.streamlit << 'EOF'
# Dockerfile.streamlit
FROM python:3.10-slim

# Install system deps (for psycopg2, etc.)
RUN apt-get update && apt-get install -y build-essential

# Install Python packages
RUN pip install --no-cache-dir streamlit pandas liualgotrader psycopg2-binary streamlit-autorefresh

WORKDIR /app

# Copy only the two Streamlit apps
COPY streamlit/app/dashboard_diagnostics.py /app/dashboard_diagnostics.py
COPY streamlit/app/live_trades.py        /app/live_trades.py

ENTRYPOINT ["streamlit"]
EOF

echo "✅ Dockerfile.streamlit patched."

echo "🔧 2) Initializing paper portfolio (25k)…"
docker compose run --rm live-trader liu create portfolio 25000
echo "✅ Portfolio created."

echo "🔧 3) Rebuilding images (streamlit-ui, live-trader, fix-it-bot)…"
docker compose build streamlit-ui live-trader fix-it-bot

echo "🔧 4) Restarting services…"
docker compose up -d streamlit-ui live-trader fix-it-bot

echo "🎉 Done! Services are up:"
docker compose ps streamlit-ui live-trader fix-it-bot

echo ""
echo "▶ Tail the logs with:"
echo "    docker compose logs -f streamlit-ui"
echo "    docker compose logs -f live-trader"
echo "    docker compose logs -f fix-it-bot"
