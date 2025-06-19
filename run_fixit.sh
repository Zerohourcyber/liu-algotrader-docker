#!/usr/bin/env bash
# run_fixit.sh — build & run the fix-it-bot with your CLI args
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 --symbols AAPL,MSFT,GOOG --start-date YYYY-MM-DD --end-date YYYY-MM-DD
EOF
  exit 1
}

# parse flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --symbols)    SYMBOLS="$2";    shift 2;;
    --start-date) START="$2";      shift 2;;
    --end-date)   END="$2";        shift 2;;
    *) echo "Unknown flag: $1"; usage;;
  esac
done

# require all three
: "${SYMBOLS:?--symbols is required}"
: "${START:?--start-date is required}"
: "${END:?--end-date is required}"

echo "🛠 Building fix-it-bot image…"
docker-compose build fix-it-bot

echo "🚀 Launching backtest with symbols=${SYMBOLS}, dates=${START}→${END}"
docker-compose run --rm fix-it-bot \
  --symbols    "${SYMBOLS}" \
  --start-date "${START}" \
  --end-date   "${END}"
