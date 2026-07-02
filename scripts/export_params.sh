#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${OB_HOST:-127.0.0.1}"
PORT="${OB_PORT:-2881}"
USER="${OB_USER:-root@sys}"
PASSWORD="${OB_PASSWORD:-}"
mkdir -p "${ROOT}/outputs"
CLIENT="mysql"
command -v obclient >/dev/null && CLIENT="obclient"
"${CLIENT}" -h"${HOST}" -P"${PORT}" -u"${USER}" -p"${PASSWORD}" -N -B < "${ROOT}/sql/02_export_parameters.sql" > "${ROOT}/outputs/ob_parameters.tsv"
echo "Exported ${ROOT}/outputs/ob_parameters.tsv"
