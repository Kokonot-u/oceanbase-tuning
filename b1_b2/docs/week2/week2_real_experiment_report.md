# 第二周真实实验报告

## 1. 实验环境

- Tailscale IP: `100.83.22.21`
- OceanBase: `5.7.25-OceanBase_CE-v4.4.2.1`
- cluster_name: `obstandalone`
- tenant_name: `test`
- username: `root@test`
- database: `week2_bench_wang`
- Docker 容器名: `ob-node`
- 连接方式: 本机执行 `docker exec ob-node bash -lc 'obclient ...'`，由容器内 obclient 连接远端 OceanBase。

## 2. 连接验证结果

连接验证已成功，日志见 `logs/real_week2/00_connection_check.log`。验证内容包括：

- `docker ps` 显示 `ob-node` 容器运行中。
- `which obclient` 返回 `/usr/bin/obclient`。
- `SELECT VERSION()` 返回 `5.7.25-OceanBase_CE-v4.4.2.1`。
- `SHOW DATABASES` 返回 `information_schema`、`mysql`、`oceanbase`、`test`。

## 3. 真实实验库与表

已创建允许范围内的数据库 `week2_bench_wang`，并创建/写入连接测试表：

- `week2_bench_wang.test_conn`
- `week2_bench_wang.workload_kv`

SQL 与输出日志见：

- `logs/real_week2/01_create_real_lab.sql`
- `logs/real_week2/01_create_real_lab.log`
- `logs/real_week2/workload_run.log`

## 4. 参数导出方法

真实参数导出通过 `scripts/real_week2/export_real_parameters.sh` 执行，优先使用 `SHOW PARAMETERS`。本次结果：

- `SHOW PARAMETERS`: 成功，生成 `b1_b2/results/week2/ob_parameters_real.tsv`
- `SHOW PARAMETERS LIKE '%cpu%'`: 成功
- `SHOW PARAMETERS LIKE '%memory%'`: 成功
- `SHOW PARAMETERS LIKE '%mem%'`: 成功
- `SHOW PARAMETERS LIKE '%io%'`: 成功
- `SHOW PARAMETERS LIKE '%sql%'`: 成功
- `SELECT * FROM oceanbase.GV$OB_PARAMETERS LIMIT 10`: 成功
- `SELECT * FROM oceanbase.DBA_OB_PARAMETERS LIMIT 10`: 失败，原因是 `oceanbase.dba_ob_parameters` 不存在

失败原因已保存到 `logs/real_week2/dba_ob_parameters_sample.log`。

## 5. 100 个关键性能参数分类结果

基于真实 `SHOW PARAMETERS` 导出，共筛选出 347 个性能相关候选参数，并生成 Top100：

- `b1_b2/results/week2/param_candidates_real.csv`
- `b1_b2/results/week2/top100_performance_params_real.csv`

分类包括 CPU 调度、内存管理、磁盘 IO、SQL 执行。字段包含当前值、默认值、范围、性能相关依据、风险、可修改性和证据来源。

## 6. Top5 参数选择理由

Top5 输出见：

- `b1_b2/results/week2/top5_params_real.csv`
- `b1_b2/docs/week2/top5_params_explanation.md`

本次选择：

| 参数 | 类别 | 当前值 | 执行状态 |
| -- | -- | -- | -- |
| cpu_quota_concurrency | CPU 调度 | 4 | 仅计划，未修改 |
| memstore_limit_percentage | 内存管理 | 0 | 仅计划，未修改 |
| clog_io_isolation_mode | 磁盘 IO | 1 | 仅计划，未修改 |
| enable_sql_audit | SQL 执行 | True | 仅计划，未修改 |
| large_query_worker_percentage | CPU 调度 | 30 | 仅计划，未修改 |

由于当前连接的是同事共享 test 租户，本次不直接执行 `ALTER SYSTEM` / `ALTER TENANT` / `SET GLOBAL`。参数变更计划和 rollback SQL 已生成：

- `b1_b2/docs/week2/parameter_change_plan.md`
- `logs/real_week2/rollback.sql`

## 7. Workload 设计

本次已经补充三类真实 workload：

1. 轻量真实 SQL workload：用于快速验证连接、建表、插入、点查、范围查询、聚合、更新和混合读写。
2. BenchmarkSQL / TPC-C：下载 BenchmarkSQL 5.0，加入 OceanBase MySQL 模式兼容配置和 MySQL JDBC driver，执行 1 warehouse、1 terminal、20 transaction 的短测试。
3. TPC-H 22 查询：创建 TPC-H 八张表，生成小规模确定性数据集，执行 22 条 TPC-H 风格查询。该部分是真实 SQL 执行，但不是官方 dbgen scale factor 数据集。

轻量真实 SQL workload 包含：

1. 建表 `workload_kv`
2. 批量插入 1000 行
3. 点查 SELECT
4. 范围查询 SELECT
5. GROUP BY 聚合查询
6. UPDATE
7. 混合读写循环

轻量 SQL 和 TPC-H 每条 SQL 均通过 Docker 容器内 `obclient` 真实连接远端 OceanBase 执行。BenchmarkSQL 通过本机 Java/JDBC 连接远端 OceanBase。

## 8. 真实实验结果

真实轻量 SQL baseline 结果：

| 指标 | 值 |
| -- | -- |
| run_id | real_week2_20260702_153400 |
| elapsed_ms | 30820.778 |
| qps_or_tps | 7.17 |
| avg_latency_ms | 139.228 |
| p50_latency_ms | 128.58 |
| p95_latency_ms | 178.12 |
| p99_latency_ms | 239.711 |
| error_count | 0 |
| rows_inserted | 1000 |
| rows_read | 21606 |
| rows_updated | 54 |

真实 BenchmarkSQL / TPC-C 结果：

| 指标 | 值 |
| -- | -- |
| run_id | benchmarksql_tpcc_20260702_171628 |
| warehouses | 1 |
| terminals | 1 |
| transaction_count | 20 |
| measured_tpmC | 46.95 |
| measured_tpmTOTAL | 109.56 |
| qps_or_tps | 1.826 |
| avg_latency_ms | 312.3 |
| p95_latency_ms | 716.0 |
| p99_latency_ms | 726.0 |
| error_count | 0 |

真实 TPC-H 22 查询结果：

| 指标 | 值 |
| -- | -- |
| run_id | tpch_22_real_20260702_172556 |
| query_count | 22 |
| total_elapsed_ms | 3370.68 |
| avg_elapsed_ms | 153.213 |
| qps_or_tps | 6.5269 |
| p95_latency_ms | 192.592 |
| p99_latency_ms | 285.852 |
| failed_queries | 0 |

结果文件：

- `b1_b2/results/week2/workload_baseline_real.csv`
- `b1_b2/results/week2/workload_summary_real.csv`
- `b1_b2/results/week2/tpcc_benchmarksql_real.csv`
- `b1_b2/results/week2/tpch_22_real.csv`
- `b1_b2/results/week2/tpch_22_summary_real.csv`
- `b1_b2/results/week2/param_perf_dataset_real.csv`
- `b1_b2/results/week2/param_perf_summary_real.csv`

说明：轻量 SQL 和 TPC-H 延迟包含 `docker exec + obclient` 调用开销；BenchmarkSQL 使用 Java/JDBC 长连接，更接近 TPC-C benchmark 测试方式。

## 9. 与旧 dry-run 文件的区别

旧文件位于 `outputs/tpcc_result_1.csv`、`outputs/tpch_result_2.csv` 等，属于 dry-run / 流程模板结果。它们没有真实执行 BenchmarkSQL/TPC-H，不作为本次真实性能结果。

本次真实文件统一放在：

- `b1_b2/results/week2/`
- `logs/real_week2/`
- `scripts/real_week2/`
- `b1_b2/docs/week2/`

## 10. 未完成项和原因

- BenchmarkSQL/TPC-C 已执行小规模真实测试。后续可扩大 warehouses、terminals、runMins。
- TPC-H 已执行 22 条真实 SQL 查询。当前数据集为脚本生成的小规模确定性数据，不是官方 dbgen 10GB 标准数据。
- 参数修改实验未执行：当前为同事共享 test 租户，安全要求是不直接改参数；已生成变更计划和 rollback SQL。
- DBA_OB_PARAMETERS 查询失败：该视图/表在当前环境不存在。

## 11. 下一步需要老师/同事确认

1. 是否允许在 test 租户执行可恢复动态参数变更。
2. 允许修改的具体参数、范围和时间窗口。
3. 是否允许扩大 BenchmarkSQL 参数，例如 warehouses=5/10、runMins=5/10。
4. 是否提供官方 tpch-obs/dbgen 工具目录，用于替换当前小规模确定性 TPC-H 数据集。
5. 是否需要单独创建压力测试租户，避免影响同事共享环境。

## 12. 截图占位符

- 【截图1：tailscale ping 成功】
- 【截图2：obclient 连接成功】
- 【截图3：SHOW DATABASES】
- 【截图4：workload 运行日志】
- 【截图5：真实结果 CSV】
