#!/usr/bin/env bash
set -euo pipefail
PARAM_NAME="${1:-param_name}"
ORIGINAL_VALUE="${2:-original_value}"
cat <<SQL
-- Template only. Restore the original or official default value after experiment:
SHOW PARAMETERS LIKE '${PARAM_NAME}';
ALTER SYSTEM SET ${PARAM_NAME} = '${ORIGINAL_VALUE}';
SHOW PARAMETERS LIKE '${PARAM_NAME}';

-- Update ob_param_lab.experiment_log with restored_default='yes'.
SQL
