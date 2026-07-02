#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "${ROOT}/docker/docker-compose.yml" ]; then
  docker compose -f "${ROOT}/docker/docker-compose.yml" up -d
else
  docker compose up -d
fi
