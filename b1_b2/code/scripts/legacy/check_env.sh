#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTAINER="${OB_CONTAINER:-obstandalone}"

echo "Project: ${ROOT}"
command -v python3 >/dev/null && python3 --version || echo "python3 not found"
command -v docker >/dev/null && docker --version || echo "docker not found"
if command -v docker >/dev/null; then
  docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}" && echo "container ${CONTAINER}: running" || echo "container ${CONTAINER}: not running"
fi
command -v obclient >/dev/null && echo "obclient: found" || echo "obclient: not found"
test -f "${ROOT}/outputs/ob_parameters.tsv" && echo "outputs/ob_parameters.tsv: found" || echo "outputs/ob_parameters.tsv: missing"
