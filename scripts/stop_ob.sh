#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "${ROOT}/docker/docker-compose.yml" ]; then
  docker compose -f "${ROOT}/docker/docker-compose.yml" down
else
  docker compose down
fi
