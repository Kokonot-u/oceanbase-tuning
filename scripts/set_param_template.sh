#!/usr/bin/env bash
set -euo pipefail
PARAM_NAME="${1:-param_name}"
VALUE="${2:-value}"
cat <<SQL
-- Template only. Review original value before any change:
SHOW PARAMETERS LIKE '${PARAM_NAME}';

-- Confirm official range, risk level, and whether restart is required.
-- Execute manually only after approval:
ALTER SYSTEM SET ${PARAM_NAME} = '${VALUE}';

-- Record before_value/after_value/workload_type in ob_param_lab.experiment_log.
SQL
