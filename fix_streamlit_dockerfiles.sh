#!/usr/bin/env bash
set -euo pipefail

# ───────────────────────────────────────────────────────────────────────────────
# 1) Patch the three Streamlit Dockerfiles (no -E, so it works with older sed)
# ───────────────────────────────────────────────────────────────────────────────
FILES=(Dockerfile.streamlit Dockerfile.live_trades Dockerfile.diagnostics)

for df in "${FILES[@]}"; do
  if [ -f "$df" ]; then
    echo "🔧 Patching $df…"
    sed -i '/^RUN pip install/ a\
    altair==4.2.2 \\ 
    vega_datasets \\ 
' "$df"
  else
    echo "⚠️  $df not found, skipping"
  fi
done

# ───────────────────────────────────────────────────────────────────────────────
# 2) Tear down & prune
# ───────────────────────────────────────────────────────────────────────────────
echo
echo "⬇️  docker compose down (remove orphans & volumes)"
docker compose down --remove-orphans --volumes

echo
echo "🧹 docker builder prune --all --force"
docker builder prune --all --force

# ───────────────────────────────────────────────────────────────────────────────
# 3) Rebuild & bring up
# ───────────────────────────────────────────────────────────────────────────────
echo
echo "🔨 docker compose build --no-cache"
docker compose build --no-cache

echo
echo "🚀 docker compose up -d"
docker compose up -d

echo
echo "✅ Done! Your UIs should now include Altair & vega_datasets."
echo "   Tail logs if you like:"
echo "     docker compose logs -f diagnostics-ui"
echo "     docker compose logs -f live-trades-ui"
