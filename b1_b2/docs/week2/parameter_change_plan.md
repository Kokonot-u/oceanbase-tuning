# 参数变更计划

当前连接的是同事共享的 `test` 租户。本次默认安全模式：只执行参数查询、建库、建表、插入数据和 workload，不执行 ALTER SYSTEM/ALTER TENANT/SET GLOBAL。

如需执行下面计划，必须先由老师/同事确认权限、影响范围和恢复命令。

| 参数 | 原值 | 候选值 | 风险 | 状态 | 恢复 SQL |
| -- | -- | -- | -- | -- | -- |
| cpu_quota_concurrency | 4 | 4 | LOW | planned_not_executed_due_to_shared_tenant_or_permission | `-- planned rollback: ALTER SYSTEM SET cpu_quota_concurrency = '4';` |
| cpu_quota_concurrency | 4 | 8 | LOW | planned_not_executed_due_to_shared_tenant_or_permission | `-- planned rollback: ALTER SYSTEM SET cpu_quota_concurrency = '4';` |
| memstore_limit_percentage | 0 | 20 | MEDIUM | planned_not_executed_due_to_shared_tenant_or_permission | `-- planned rollback: ALTER SYSTEM SET memstore_limit_percentage = '0';` |
| memstore_limit_percentage | 0 | 40 | MEDIUM | planned_not_executed_due_to_shared_tenant_or_permission | `-- planned rollback: ALTER SYSTEM SET memstore_limit_percentage = '0';` |
| clog_io_isolation_mode | 1 | 1 | MEDIUM | planned_not_executed_due_to_shared_tenant_or_permission | `-- planned rollback: ALTER SYSTEM SET clog_io_isolation_mode = '1';` |
| clog_io_isolation_mode | 1 | 2 | MEDIUM | planned_not_executed_due_to_shared_tenant_or_permission | `-- planned rollback: ALTER SYSTEM SET clog_io_isolation_mode = '1';` |
| enable_sql_audit | True | True | MEDIUM | planned_not_executed_due_to_shared_tenant_or_permission | `-- planned rollback: ALTER SYSTEM SET enable_sql_audit = 'True';` |
| enable_sql_audit | True | False | MEDIUM | planned_not_executed_due_to_shared_tenant_or_permission | `-- planned rollback: ALTER SYSTEM SET enable_sql_audit = 'True';` |
| large_query_worker_percentage | 30 | 20 | MEDIUM | planned_not_executed_due_to_shared_tenant_or_permission | `-- planned rollback: ALTER SYSTEM SET large_query_worker_percentage = '30';` |
| large_query_worker_percentage | 30 | 40 | MEDIUM | planned_not_executed_due_to_shared_tenant_or_permission | `-- planned rollback: ALTER SYSTEM SET large_query_worker_percentage = '30';` |
