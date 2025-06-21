#!/usr/bin/env bash
set -e

docker compose down --remove-orphans --volumes
docker builder prune --all --force
docker compose build --no-cache
docker compose up -d
