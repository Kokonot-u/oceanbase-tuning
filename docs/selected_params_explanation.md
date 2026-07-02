# 5 个核心参数选择说明

本轮从第一周导出的 OceanBase 参数表中，按 CPU 调度、内存管理、磁盘 IO、SQL 执行四类筛选候选参数。选择时优先覆盖多类性能机制，避开明显高风险或可能导致 observer 无法启动的参数。所有梯度均为保守占位，真实执行前必须核对官方文档范围和当前租户资源。

| param_name | category | original_value | test_value_1 | test_value_2 | test_value_3 | test_value_4 | workload_tpcc | workload_tpch | expected_impact | risk_level | need_restart | note |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| cpu_quota_concurrency | CPU调度 | 10 | 4 | 8 | 10 | 16 | yes | yes | 影响并发执行、后台任务调度和高负载下排队时间 | medium | no | 需要人工确认官方文档默认值和范围；脚本不会自动执行 ALTER SYSTEM SET |
| memstore_limit_percentage | 内存管理 | 0 | 0 | 20 | 40 | 60 | yes | yes | 影响缓存命中、冻结频率和内存压力 | medium | no | 需要人工确认官方文档默认值和范围；脚本不会自动执行 ALTER SYSTEM SET |
| clog_io_isolation_mode | 磁盘IO | 1 | 1 | 2 | 1 | 1 | yes | yes | 影响日志写入、刷盘、压缩和磁盘吞吐 | medium | no | 需要人工确认官方文档默认值和范围；脚本不会自动执行 ALTER SYSTEM SET |
| enable_sql_audit | SQL执行 | True | conservative | True | aggressive | manual_confirm | yes | yes | 影响 SQL 执行路径、审计开销和长查询调度 | medium | no | 需要人工确认官方文档默认值和范围；脚本不会自动执行 ALTER SYSTEM SET |
| large_query_worker_percentage | CPU调度 | 30 | 10 | 20 | 30 | 40 | yes | yes | 影响并发执行、后台任务调度和高负载下排队时间 | medium | no | 需要人工确认官方文档默认值和范围；脚本不会自动执行 ALTER SYSTEM SET |

注意：本脚本只生成建议，不执行参数修改。
