#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/outputs/metrics_log.csv"
CONTAINER="${OB_CONTAINER:-obstandalone}"

mkdir -p "${ROOT}/outputs"
if [ ! -f "${OUT}" ]; then
  echo "timestamp,container_name,cpu_percent,memory_usage,memory_limit,memory_percent,net_io,block_io,pids" > "${OUT}"
fi
if ! command -v docker >/dev/null; then
  echo "docker command not found" >&2
  exit 1
fi
if ! docker ps --format '{{.Names}}' | grep -qx "${CONTAINER}"; then
  echo "container ${CONTAINER} does not exist or is not running" >&2
  exit 1
fi
line="$(docker stats "${CONTAINER}" --no-stream --format '{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}')"
IFS=',' read -r name cpu mem_usage mem_pct net_io block_io pids <<< "${line}"
memory_usage="${mem_usage%% / *}"
memory_limit="${mem_usage##* / }"
printf '%s,%s,%s,%s,%s,%s,%s,%s,%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "${name}" "${cpu%\%}" "${memory_usage}" "${memory_limit}" "${mem_pct%\%}" "\"${net_io}\"" "\"${block_io}\"" "${pids}" >> "${OUT}"
echo "Appended metrics to ${OUT}"
