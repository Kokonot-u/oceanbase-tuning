#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPERIMENT_ID="${1:-}"
PARAM_NAME="${2:-}"
TEST_VALUE="${3:-}"
RUN_MINUTES="${4:-5}"
OUT="${ROOT}/outputs/tpcc_result_${EXPERIMENT_ID:-unknown}.csv"
BENCHMARKSQL_HOME="${BENCHMARKSQL_HOME:-${ROOT}/tools/benchmarksql}"

if [ -z "${EXPERIMENT_ID}" ] || [ -z "${PARAM_NAME}" ] || [ -z "${TEST_VALUE}" ]; then
  echo "Usage: bash scripts/run_tpcc_test.sh experiment_id param_name test_value [run_minutes]" >&2
  exit 2
fi
mkdir -p "${ROOT}/outputs"
echo "experiment_id,workload_type,param_name,test_value,qps,avg_latency_ms,p95_latency_ms,p99_latency_ms,error_count,start_time,end_time,status,note" > "${OUT}"
start_time="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
if [ -d "${BENCHMARKSQL_HOME}" ] && [ -x "${BENCHMARKSQL_HOME}/run/runBenchmark.sh" ]; then
  echo "BenchmarkSQL found at ${BENCHMARKSQL_HOME}; please adapt configs/tpcc_config.example.properties before long runs."
  status="manual_ready"
  note="BenchmarkSQL found; script did not parse vendor output automatically yet"
else
  status="dry_run"
  note="BenchmarkSQL 未安装，已生成 dry-run 结果"
  printf '%s,tpcc,%s,%s,,,,,0,%s,%s,%s,"%s"\n' "${EXPERIMENT_ID}" "${PARAM_NAME}" "${TEST_VALUE}" "${start_time}" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "${status}" "${note}" >> "${OUT}"
  printf '\n- BenchmarkSQL 未安装，实验 %s 已生成 dry-run 结果：outputs/tpcc_result_%s.csv\n' "${EXPERIMENT_ID}" "${EXPERIMENT_ID}" >> "${ROOT}/docs/troubleshooting.md"
  echo "Wrote dry-run result ${OUT}"
  exit 0
fi
printf '%s,tpcc,%s,%s,,,,,0,%s,%s,%s,"%s"\n' "${EXPERIMENT_ID}" "${PARAM_NAME}" "${TEST_VALUE}" "${start_time}" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "${status}" "${note}" >> "${OUT}"
