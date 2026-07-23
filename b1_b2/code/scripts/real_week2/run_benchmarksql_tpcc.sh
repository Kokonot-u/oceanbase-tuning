#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT}/.." && pwd)"
OUT_DIR="${ROOT}/results/week2"
LOG_DIR="${ROOT}/logs/week2"
BMSQL_DIR="${BENCHMARKSQL_HOME:-${PROJECT_ROOT}/tools/benchmarksql}"
RUN_DIR="${BMSQL_DIR}/run"
mkdir -p "${OUT_DIR}" "${LOG_DIR}"

export PATH="/opt/homebrew/opt/openjdk/bin:${PATH}"
HOST="${OB_HOST:-100.83.22.21}"
PORT="${OB_PORT:-2881}"
USER="${OB_USER:-root@test}"
PASSWORD="${OB_PASSWORD:?Set OB_PASSWORD before running BenchmarkSQL}"
DATABASE="${OB_DATABASE:-week2_bench_wang}"
RUN_ID="benchmarksql_tpcc_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_DIR}/${RUN_ID}.log"
PROPS_FILE="${RUN_DIR}/props.ob.runtime"

cat > "${PROPS_FILE}" <<EOF_PROPS
db=oceanbase
driver=com.mysql.cj.jdbc.Driver
conn=jdbc:mysql://${HOST}:${PORT}/${DATABASE}?useSSL=false&allowPublicKeyRetrieval=true&rewriteBatchedStatements=true&serverTimezone=UTC&sessionVariables=ob_query_timeout=60000000
user=${USER}
password=${PASSWORD}

warehouses=${TPCC_WAREHOUSES:-1}
loadWorkers=${TPCC_LOAD_WORKERS:-2}
terminals=${TPCC_TERMINALS:-1}
runTxnsPerTerminal=${TPCC_TXNS_PER_TERMINAL:-20}
runMins=0
limitTxnsPerMin=${TPCC_LIMIT_TXNS_PER_MIN:-120}
terminalWarehouseFixed=true
newOrderWeight=45
paymentWeight=43
orderStatusWeight=4
deliveryWeight=4
stockLevelWeight=4
resultDirectory=${RUN_ID}
EOF_PROPS

{
  echo "run_id=${RUN_ID}"
  echo "start_time=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "host=${HOST} port=${PORT} user=${USER} database=${DATABASE}"
  echo "java=$(java -version 2>&1 | head -1)"
  echo "benchmarksql_dir=${BMSQL_DIR}"
  echo "dropping only project-owned bmsql_* tables in ${DATABASE}"
} > "${LOG_FILE}"

docker exec -i ob-node bash -lc "obclient -h${HOST} -P${PORT} -u${USER} -p${PASSWORD} -A -D${DATABASE}" >> "${LOG_FILE}" 2>&1 <<'SQL'
DROP TABLE IF EXISTS bmsql_config;
DROP TABLE IF EXISTS bmsql_new_order;
DROP TABLE IF EXISTS bmsql_order_line;
DROP TABLE IF EXISTS bmsql_oorder;
DROP TABLE IF EXISTS bmsql_history;
DROP TABLE IF EXISTS bmsql_customer;
DROP TABLE IF EXISTS bmsql_stock;
DROP TABLE IF EXISTS bmsql_item;
DROP TABLE IF EXISTS bmsql_district;
DROP TABLE IF EXISTS bmsql_warehouse;
SQL

pushd "${RUN_DIR}" >/dev/null
echo "## runDatabaseBuild" >> "${LOG_FILE}"
./runDatabaseBuild.sh "${PROPS_FILE}" >> "${LOG_FILE}" 2>&1
echo "## runBenchmark" >> "${LOG_FILE}"
./runBenchmark.sh "${PROPS_FILE}" >> "${LOG_FILE}" 2>&1
popd >/dev/null

RESULT_DIR="$(find "${RUN_DIR}" -maxdepth 1 -type d -name "${RUN_ID}" | head -1)"
if [ -n "${RESULT_DIR}" ]; then
  cp -R "${RESULT_DIR}" "${OUT_DIR}/${RUN_ID}"
  if [ -f "${OUT_DIR}/${RUN_ID}/run.properties" ]; then
    sed -i.bak 's/^password=.*/password=***REDACTED***/' "${OUT_DIR}/${RUN_ID}/run.properties"
    rm -f "${OUT_DIR}/${RUN_ID}/run.properties.bak"
  fi
fi

python3 "${ROOT}/code/scripts/real_week2/summarize_benchmarksql_tpcc.py" "${LOG_FILE}" "${OUT_DIR}/tpcc_benchmarksql_real.csv" "${RUN_ID}" "${HOST}" "${USER}" "${DATABASE}"
echo "end_time=$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> "${LOG_FILE}"
echo "BenchmarkSQL TPC-C finished: ${OUT_DIR}/tpcc_benchmarksql_real.csv"
