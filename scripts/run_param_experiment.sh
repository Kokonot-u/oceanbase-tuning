#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MATRIX="${ROOT}/outputs/param_test_matrix.csv"
EXPERIMENT_ID="${1:-}"

if [ -z "${EXPERIMENT_ID}" ]; then
  echo "Usage: bash scripts/run_param_experiment.sh experiment_id" >&2
  exit 2
fi
if [ ! -f "${MATRIX}" ]; then
  echo "Missing ${MATRIX}. Run python3 scripts/generate_test_matrix.py first." >&2
  exit 1
fi

row="$(awk -F',' -v id="${EXPERIMENT_ID}" 'NR > 1 && $1 == id {print; exit}' "${MATRIX}")"
if [ -z "${row}" ]; then
  echo "experiment_id ${EXPERIMENT_ID} not found in ${MATRIX}" >&2
  exit 1
fi

IFS=',' read -r experiment_id param_name category original_value test_value workload_type test_round expected_impact risk_level need_restart status note <<< "${row}"
echo "Experiment ${experiment_id}: ${param_name}=${test_value}, workload=${workload_type}, risk=${risk_level}, need_restart=${need_restart}"
echo "Safety: this script does not run ALTER SYSTEM SET. Confirm and apply manually with scripts/set_param_template.sh if needed."

bash "${ROOT}/scripts/collect_metrics.sh" || true
if [ "${workload_type}" = "tpcc" ]; then
  bash "${ROOT}/scripts/run_tpcc_test.sh" "${experiment_id}" "${param_name}" "${test_value}" 5
elif [ "${workload_type}" = "tpch" ]; then
  bash "${ROOT}/scripts/run_tpch_test.sh" "${experiment_id}" "${param_name}" "${test_value}" 1
else
  echo "Unsupported workload_type: ${workload_type}" >&2
  exit 1
fi
bash "${ROOT}/scripts/collect_metrics.sh" || true
python3 "${ROOT}/scripts/summarize_results.py"
