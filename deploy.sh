#!/usr/bin/env bash
set -eu

# Куда деплоим (можно переопределить через env)
APP_DIR="${APP_DIR:-/opt/vispr}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

cd "$APP_DIR"

echo "==> Pull latest images"
docker compose -f "$COMPOSE_FILE" pull app

echo "==> Recreate containers"
docker compose -f "$COMPOSE_FILE" up -d

echo "==> Wait for health"
for i in {1..20}; do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    echo "==> Healthy"
    break
  fi
  echo "  waiting... ($i)"
  sleep 2
done

echo "==> Cleanup old images"
docker image prune -f >/dev/null

echo "==> Done. TAG=$TAG"