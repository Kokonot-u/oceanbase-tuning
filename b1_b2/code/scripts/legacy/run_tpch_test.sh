#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPERIMENT_ID="${1:-}"
PARAM_NAME="${2:-}"
TEST_VALUE="${3:-}"
SCALE_FACTOR="${4:-1}"
OUT="${ROOT}/outputs/tpch_result_${EXPERIMENT_ID:-unknown}.csv"
TPCH_HOME="${TPCH_HOME:-${ROOT}/tools/tpch-obs}"

if [ -z "${EXPERIMENT_ID}" ] || [ -z "${PARAM_NAME}" ] || [ -z "${TEST_VALUE}" ]; then
  echo "Usage: bash scripts/run_tpch_test.sh experiment_id param_name test_value [scale_factor]" >&2
  exit 2
fi
mkdir -p "${ROOT}/outputs"
echo "experiment_id,workload_type,param_name,test_value,query_id,elapsed_ms,status,note" > "${OUT}"
if [ -d "${TPCH_HOME}" ]; then
  for q in $(seq 1 22); do
    printf '%s,tpch,%s,%s,Q%s,,manual_ready,"tpch tool found; wire query execution before production run"\n' "${EXPERIMENT_ID}" "${PARAM_NAME}" "${TEST_VALUE}" "${q}" >> "${OUT}"
  done
else
  for q in $(seq 1 22); do
    printf '%s,tpch,%s,%s,Q%s,,dry_run,"tpch-obs 未安装，scale_factor=%s，已生成 dry-run 结果"\n' "${EXPERIMENT_ID}" "${PARAM_NAME}" "${TEST_VALUE}" "${q}" "${SCALE_FACTOR}" >> "${OUT}"
  done
  printf '\n- tpch-obs 未安装，实验 %s 已生成 dry-run 结果：outputs/tpch_result_%s.csv\n' "${EXPERIMENT_ID}" "${EXPERIMENT_ID}" >> "${ROOT}/docs/troubleshooting.md"
fi
echo "Wrote ${OUT}"
