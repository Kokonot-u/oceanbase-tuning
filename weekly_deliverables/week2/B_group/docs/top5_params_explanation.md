# Top5 真实参数选择说明

Top5 基于真实 `SHOW PARAMETERS` 导出结果生成；默认只做安全模式，不直接修改共享 test 租户参数。

| 参数 | 类别 | 当前值 | 风险 | 可修改性 | 依据 |
| -- | -- | -- | -- | -- | -- |
| cpu_quota_concurrency | CPU调度 | 4 | LOW | YES | 影响并发度、后台线程调度、排队和高负载响应时间 |
| memstore_limit_percentage | 内存管理 | 0 | MEDIUM | UNKNOWN | 影响缓存、冻结、内存水位和租户资源使用 |
| clog_io_isolation_mode | 磁盘IO | 1 | MEDIUM | UNKNOWN | 影响日志写入、刷盘、压缩、磁盘带宽和 IO 隔离 |
| enable_sql_audit | SQL执行 | True | MEDIUM | UNKNOWN | 影响 SQL 计划、审计、长查询调度和执行超时 |
| large_query_worker_percentage | CPU调度 | 30 | MEDIUM | UNKNOWN | 影响并发度、后台线程调度、排队和高负载响应时间 |

所有候选值执行前需老师/同事确认，并先写入 rollback SQL。
