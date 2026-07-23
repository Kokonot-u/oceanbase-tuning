#!/usr/bin/env bash
set -euo pipefail
HOST="${OB_HOST:-127.0.0.1}"
PORT="${OB_PORT:-2881}"
USER="${OB_USER:-root@sys}"
PASSWORD="${OB_PASSWORD:-}"
if command -v obclient >/dev/null; then
  obclient -h"${HOST}" -P"${PORT}" -u"${USER}" -p"${PASSWORD}"
else
  mysql -h"${HOST}" -P"${PORT}" -u"${USER}" -p"${PASSWORD}"
fi
