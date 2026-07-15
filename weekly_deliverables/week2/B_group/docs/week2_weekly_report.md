# OceanBase 性能智能诊断与参数调优项目周报

## 一、本周工作概述

本周主要围绕第二周 B 组任务，将前期 dry-run / mock 结果替换为可追溯的真实 OceanBase 实验结果，并补齐 BenchmarkSQL / TPC-C、TPC-H 查询 workload、参数候选集、参数实验矩阵和结果可视化。

当前真实实验统一放在 `outputs/real_week2/`、`logs/real_week2/`、`scripts/real_week2/` 和 `docs/real_week2/` 目录下。所有数据库连接、参数导出、workload 执行和结果汇总均基于实际 OceanBase 环境完成。

## 二、实验环境与连接验证

本周使用远端 OceanBase 单节点环境进行真实实验：

- OceanBase 版本：`5.7.25-OceanBase_CE-v4.4.2.1`
- 集群：`obstandalone`
- 租户：`test`
- 数据库：`week2_bench_wang`
- 连接方式：本机通过 Docker 容器 `ob-node` 内的 `obclient` 连接远端 OceanBase

已完成连接可用性验证，验证内容包括容器运行状态、`obclient` 可用性、`SELECT VERSION()`、`SHOW DATABASES` 等。连接日志已保存到 `logs/real_week2/00_connection_check.log`。

## 三、参数采集与候选参数筛选

本周完成了基于真实 OceanBase 环境的参数导出和性能相关参数筛选。

已完成内容：

- 通过 `SHOW PARAMETERS` 导出真实参数，共生成 `outputs/real_week2/ob_parameters_real.tsv`。
- 分别导出 CPU、内存、IO、SQL 相关参数样本，便于分类分析。
- 基于真实参数构建性能参数候选集，生成 `outputs/real_week2/param_candidates_real.csv`。
- 从候选集中筛选 Top100 性能相关参数，生成 `outputs/real_week2/top100_performance_params_real.csv`。
- 进一步选出 Top5 参数并生成实验矩阵。

本周选择的 Top5 参数如下：

| 参数 | 类型 | 当前值 | 计划测试值 |
| -- | -- | -- | -- |
| `cpu_quota_concurrency` | CPU 调度 | 4 | 4 / 8 |
| `memstore_limit_percentage` | 内存管理 | 0 | 20 / 40 | 
| `clog_io_isolation_mode` | 磁盘 IO | 1 | 1 / 2 | 
| `enable_sql_audit` | SQL 执行 | True | True / False | 
| `large_query_worker_percentage` | CPU 调度 | 30 | 20 / 40 | 

由于当前使用的是共享 `test` 租户，本周未直接执行 `ALTER SYSTEM`、`ALTER TENANT` 或 `SET GLOBAL`，避免影响其他同学或已有环境。对应的参数变更计划和回滚 SQL 已生成：

- `docs/real_week2/parameter_change_plan.md`
- `logs/real_week2/rollback.sql`

## 四、真实 Workload 与基准测试结果

本周补充了三类真实 workload，用于替代旧的 dry-run 结果。

### 1. 轻量真实 SQL workload

该 workload 用于验证 OceanBase 真实读写链路，包含建表、批量插入、点查、范围查询、聚合查询、更新和混合读写。

| 指标 | 结果 |
| -- | -- |
| run_id | `real_week2_20260702_153400` |
| 总耗时 | 30820.778 ms |
| 吞吐 | 7.17 ops/s |
| 平均延迟 | 139.228 ms |
| P95 延迟 | 178.12 ms |
| P99 延迟 | 239.711 ms |
| 错误数 | 0 |

### 2. BenchmarkSQL / TPC-C

本周完成 BenchmarkSQL 工具接入，并在 OceanBase MySQL 模式下执行 TPC-C 短测试。测试配置为 1 warehouse、1 terminal、20 transactions。

| 指标 | 结果 |
| -- | -- |
| run_id | `benchmarksql_tpcc_20260702_171628` |
| warehouses | 1 |
| terminals | 1 |
| transaction_count | 20 |
| measured_tpmC | 46.95 |
| measured_tpmTOTAL | 109.56 |
| 吞吐 | 1.826 ops/s |
| 平均延迟 | 312.3 ms |
| P95 延迟 | 716.0 ms |
| P99 延迟 | 726.0 ms |
| 错误数 | 0 |

结果说明：TPC-C 是多表事务型 workload，包含读写事务、索引维护和提交开销，因此延迟明显高于轻量 SQL 与 TPC-H 查询 workload。

### 3. TPC-H 22 查询

本周实现并执行了 22 条 TPC-H 风格 SQL 查询。当前使用的是脚本生成的小规模确定性数据集，属于真实 SQL 执行结果，但不是官方 dbgen scale factor 数据。

| 指标 | 结果 |
| -- | -- |
| run_id | `tpch_22_real_20260702_172556` |
| query_count | 22 |
| 总耗时 | 3370.68 ms |
| 吞吐 | 6.5269 query/s |
| 平均延迟 | 153.213 ms |
| P95 延迟 | 192.592 ms |
| P99 延迟 | 285.852 ms |
| 失败查询数 | 0 |

结果说明：TPC-H 当前数据规模较小，因此总体延迟较低，主要作用是验证 OLAP 查询链路、SQL 兼容性和自动化结果采集流程。

## 五、结果汇总与可视化

本周将三类真实 workload 统一汇总到 `outputs/real_week2/param_perf_dataset_real.csv`，并生成基线汇总表和延迟对比图。

已生成文件：

- `outputs/real_week2/param_perf_dataset_real.csv`
- `outputs/real_week2/param_perf_summary_real.csv`
- `outputs/real_week2/figures/baseline_summary_table.md`
- `outputs/real_week2/figures/baseline_summary_table.png`
- `outputs/real_week2/figures/latency_comparison.png`

核心对比结果如下：

| workload | 吞吐 | 平均延迟 | P95 延迟 | P99 延迟 | 错误数 |
| -- | -- | -- | -- | -- | -- |
| TPC-C / BenchmarkSQL | 1.826 ops/s | 312.3 ms | 716.0 ms | 726.0 ms | 0 |
| TPC-H / 22 queries | 6.5269 query/s | 153.213 ms | 192.592 ms | 285.852 ms | 0 |

从结果看，TPC-C 的尾延迟明显高于 TPC-H，说明事务型写入和提交路径对性能更敏感。当前所有 workload 错误数均为 0，说明实验链路、连接方式和结果采集脚本已具备可复现实验基础。

## 六、本周问题与处理

本周遇到的主要问题包括：

1. `DBA_OB_PARAMETERS` 在当前 OceanBase 环境中不存在，因此改用 `SHOW PARAMETERS` 和 `GV$OB_PARAMETERS` 作为真实参数来源。
2. BenchmarkSQL 默认不直接识别 OceanBase，需要通过 MySQL 兼容方式和 JDBC driver 接入。
3. 当前连接的是共享 `test` 租户，不能直接执行参数修改实验，因此本周只生成参数实验矩阵和回滚方案，没有实际修改系统参数。
4. 当前 TPC-H 数据集为小规模脚本生成数据，不是官方 dbgen 标准数据，因此只能作为真实 SQL 链路验证和轻量 OLAP baseline，不能直接作为标准 TPC-H 跑分。

## 七、阶段性结论

本周已完成第二周 B 组任务中“真实实验替换 dry-run 结果”的主要工作。当前项目已经具备：

- 真实 OceanBase 连接验证记录；
- 真实参数导出结果；
- 性能参数候选集和 Top5 参数实验计划；
- BenchmarkSQL / TPC-C baseline；
- TPC-H 22 查询 baseline；
- 统一性能结果数据集；
- 自动化汇总表和延迟对比图；
- 参数变更计划和回滚 SQL。

当前实验结果可以作为后续参数调优的 baseline。真正的参数调优收益对比，需要在独立测试租户中执行参数修改后，再重复 TPC-C、TPC-H 和轻量 SQL workload 进行对照实验。

## 八、下周计划

下周建议重点推进以下工作：

1. 在独立租户中执行 Top5 参数的可控变更实验，并记录每组参数下的 TPC-C / TPC-H 指标。
2. 扩大 BenchmarkSQL 测试规模，例如提高 warehouses、terminals 和运行时间，使 TPC-C 结果更稳定。
3. 如条件允许，引入官方 TPC-H dbgen 数据集，替换当前小规模确定性数据。
4. 将 baseline 与参数修改后的结果做成对比表和图，形成“参数变化 -> 性能变化 -> 调优建议”的闭环。

