#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="./docker-compose.yml"
SERVICES=(liu-db liu-fix-it liu-live liu-streamlit liu-prometheus liu-grafana)

echo "🔍 Bringing up all services (detached)..."
docker compose -f "$COMPOSE_FILE" up -d

echo "⏳ Waiting 5s for containers to settle..."
sleep 5

# Gather unhealthy services
echo
echo "📋 Checking container statuses..."
UNHEALTHY=()
while read -r name status rest; do
    if [[ "$status" =~ ^(Restarting|Exited) ]]; then
        UNHEALTHY+=("$name")
    fi
done < <(docker compose -f "$COMPOSE_FILE" ps --format '{{.Name}} {{.State}} {{.Ports}}')

if [ ${#UNHEALTHY[@]} -eq 0 ]; then
    echo "✅ All containers are running normally."
    exit 0
fi

echo
echo "⚠️  Detected issues with the following containers:"
for c in "${UNHEALTHY[@]}"; do
    echo "   • $c"
done

echo
echo "📜 Last 20 log lines from each failing container:"
for c in "${UNHEALTHY[@]}"; do
    echo
    echo "── Logs: $c ─────────────────────────────────"
    docker compose -f "$COMPOSE_FILE" logs --tail 20 "$c"
done

echo
read -p "🔧 Rebuild & restart these services? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "❌ Aborting fix."
    exit 1
fi

echo
echo "🔨 Rebuilding & restarting..."
for c in "${UNHEALTHY[@]}"; do
    echo "⟳ $c"
    docker compose -f "$COMPOSE_FILE" build "$c"
    docker compose -f "$COMPOSE_FILE" up -d "$c"
done

echo
echo "✅ Done. New statuses:"
docker compose -f "$COMPOSE_FILE" ps

