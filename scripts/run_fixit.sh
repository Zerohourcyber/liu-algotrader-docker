#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
docker-compose build fix-it-bot
docker-compose run --rm fix-it-bot \
  --symbols AAPL,MSFT,GOOG \
  --start-date 2025-06-19 \
  --end-date   2025-06-19
