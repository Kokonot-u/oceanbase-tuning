#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
OUT_DIR="$ROOT/results/week2"
LOG_DIR="$ROOT/logs/week2"
mkdir -p "$OUT_DIR" "$LOG_DIR"
HOST="${OB_HOST:-100.83.22.21}"
PORT="${OB_PORT:-2881}"
USER="${OB_USER:-root@test}"
PASSWORD="${OB_PASSWORD:?Set OB_PASSWORD before running this script}"
OBCLIENT="obclient -h${HOST} -P${PORT} -u${USER} -p${PASSWORD} -A -B"
run_query() {
  local name="$1"
  local sql="$2"
  local out="$OUT_DIR/${name}.tsv"
  local log="$LOG_DIR/${name}.log"
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] SQL: $sql" > "$log"
  if docker exec ob-node bash -lc "$OBCLIENT -e \"$sql\"" > "$out" 2>> "$log"; then
    echo "SUCCESS $name" >> "$log"
    return 0
  else
    echo "FAILED $name" >> "$log"
    return 1
  fi
}
: > "$LOG_DIR/02_parameter_export_summary.log"
queries=(
  "show_parameters|SHOW PARAMETERS"
  "show_parameters_cpu|SHOW PARAMETERS LIKE '%cpu%'"
  "show_parameters_memory|SHOW PARAMETERS LIKE '%memory%'"
  "show_parameters_mem|SHOW PARAMETERS LIKE '%mem%'"
  "show_parameters_io|SHOW PARAMETERS LIKE '%io%'"
  "show_parameters_sql|SHOW PARAMETERS LIKE '%sql%'"
  "gv_ob_parameters_sample|SELECT * FROM oceanbase.GV\\\$OB_PARAMETERS LIMIT 10"
  "dba_ob_parameters_sample|SELECT * FROM oceanbase.DBA_OB_PARAMETERS LIMIT 10"
)
for item in "${queries[@]}"; do
  name="${item%%|*}"
  sql="${item#*|}"
  if run_query "$name" "$sql"; then
    echo "$name SUCCESS" | tee -a "$LOG_DIR/02_parameter_export_summary.log"
  else
    echo "$name FAILED" | tee -a "$LOG_DIR/02_parameter_export_summary.log"
  fi
done
if [ -s "$OUT_DIR/show_parameters.tsv" ]; then
  cp "$OUT_DIR/show_parameters.tsv" "$OUT_DIR/ob_parameters_real.tsv"
else
  first="$(find "$OUT_DIR" -name 'show_parameters_*.tsv' -size +0 | head -1)"
  if [ -n "$first" ]; then
    cp "$first" "$OUT_DIR/ob_parameters_real.tsv"
  else
    : > "$OUT_DIR/ob_parameters_real.tsv"
  fi
fi
wc -l "$OUT_DIR"/*.tsv >> "$LOG_DIR/02_parameter_export_summary.log" 2>&1
