# B1 参数影响因子分析报告 - real_week4

负责人：Wang

## 数据来源

- 参数候选：`b1_b2/results/week2/param_candidates_real.csv`，共 347 个性能相关候选参数。
- 基线性能：`b1_b2/results/week2/param_perf_dataset_real.csv`，包含轻量 SQL、BenchmarkSQL TPC-C、TPC-H 22 查询。
- 当前限制：共享 `test` 租户尚未开放参数修改窗口，因此本报告使用离线启发式特征工程，不声称已经完成真实改参因果验证。

## Top30 参数影响力

| rank | parameter_name | category | importance_score | max_workload_score | safety_score | risk_level | can_modify | action_type | min_value | max_value | step | enum_values | selection_reason | interpretation |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| 1 | log_disk_utilization_limit_threshold | 磁盘IO | 0.9007999999999999 | 0.932 | 1.0 | LOW | YES | numeric | 80.0 | 100.0 | 5.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 2 | log_disk_utilization_threshold | 磁盘IO | 0.9007999999999999 | 0.932 | 1.0 | LOW | YES | numeric | 10.0 | 100.0 | 22.5 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 3 | log_disk_throttling_maximum_duration | 磁盘IO | 0.8808000000000001 | 0.912 | 1.0 | LOW | YES | numeric | 1.0 | 3.0 | 1.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 4 | enable_clog_encryption | 磁盘IO | 0.805467 | 0.836667 | 1.0 | LOW | YES | bool | 0.0 | 1.0 | 1.0 | True\|False | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 5 | log_disk_throttling_percentage | 磁盘IO | 0.790133 | 0.821333 | 1.0 | LOW | YES | numeric | 30.0 | 90.0 | 15.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 6 | standby_db_preferred_upstream_log_region | 磁盘IO | 0.790133 | 0.821333 | 1.0 | LOW | YES | numeric | 0.0 | 100.0 | 25.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 7 | clog_io_isolation_mode | 磁盘IO | 0.789035 | 0.820235 | 0.4464 | MEDIUM | UNKNOWN | enum | 1.0 | 2.0 | 1.0 | 1\|2 | week2_top5_core_prior | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 8 | vector_index_memory_saving_mode | 内存管理 | 0.781733 | 0.805733 | 1.0 | LOW | YES | bool | 0.0 | 1.0 | 1.0 | True\|False | offline_importance_rank | 内存水位、缓存和冻结行为会影响写入路径与大查询中间结果。 |
| 9 | memory_chunk_cache_size | 内存管理 | 0.7806350000000001 | 0.804635 | 0.4464 | MEDIUM | UNKNOWN | numeric | 0.0 | 1.0 | 1.0 |  | offline_importance_rank | 内存水位、缓存和冻结行为会影响写入路径与大查询中间结果。 |
| 10 | syslog_io_bandwidth_limit | 磁盘IO | 0.769035 | 0.800235 | 0.4464 | MEDIUM | UNKNOWN | numeric | 15.0 | 45.0 | 7.5 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 11 | cpu_quota_concurrency | CPU调度 | 0.7656000000000001 | 0.7776 | 1.0 | LOW | YES | numeric | 1.0 | 20.0 | 4.75 |  | week2_top5_core_prior | 并发调度和后台线程会影响事务排队与大查询执行资源。 |
| 12 | px_workers_per_cpu_quota | CPU调度 | 0.7656000000000001 | 0.7776 | 1.0 | LOW | YES | numeric | 0.0 | 20.0 | 5.0 |  | offline_importance_rank | 并发调度和后台线程会影响事务排队与大查询执行资源。 |
| 13 | compaction_dag_cnt_limit | 磁盘IO | 0.7648 | 0.796 | 1.0 | LOW | YES | numeric | 10000.0 | 500000.0 | 122500.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 14 | compaction_high_thread_score | 磁盘IO | 0.7648 | 0.796 | 1.0 | LOW | YES | numeric | 0.0 | 100.0 | 25.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 15 | compaction_low_thread_score | 磁盘IO | 0.7648 | 0.796 | 1.0 | LOW | YES | numeric | 0.0 | 100.0 | 25.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 16 | compaction_mid_thread_score | 磁盘IO | 0.7648 | 0.796 | 1.0 | LOW | YES | numeric | 0.0 | 100.0 | 25.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 17 | compaction_schedule_tablet_batch_cnt | 磁盘IO | 0.7648 | 0.796 | 1.0 | LOW | YES | numeric | 10000.0 | 500000.0 | 122500.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 18 | dump_data_dictionary_to_log_interval | 磁盘IO | 0.7648 | 0.796 | 1.0 | LOW | YES | numeric | 0.0 | 1.0 | 1.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 19 | mds_compaction_high_thread_score | 磁盘IO | 0.7648 | 0.796 | 1.0 | LOW | YES | numeric | 0.0 | 100.0 | 25.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 20 | mds_compaction_mid_thread_score | 磁盘IO | 0.7648 | 0.796 | 1.0 | LOW | YES | numeric | 0.0 | 100.0 | 25.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 21 | ob_compaction_schedule_interval | 磁盘IO | 0.7648 | 0.796 | 1.0 | LOW | YES | numeric | 3.0 | 5.0 | 1.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 22 | __min_full_resource_pool_memory | 内存管理 | 0.7606350000000001 | 0.784635 | 0.4464 | MEDIUM | UNKNOWN | numeric | 1073741824.0 | 3221225472.0 | 536870912.0 |  | offline_importance_rank | 内存水位、缓存和冻结行为会影响写入路径与大查询中间结果。 |
| 23 | audit_log_compression | 磁盘IO | 0.7448 | 0.776 | 1.0 | LOW | YES | numeric | 0.0 | 100.0 | 25.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 24 | load_data_diagnosis_log_compression | 磁盘IO | 0.7448 | 0.776 | 1.0 | LOW | YES | numeric | 0.0 | 100.0 | 25.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 25 | shared_log_retention | 磁盘IO | 0.7448 | 0.776 | 1.0 | LOW | YES | numeric | 0.5 | 2.0 | 1.0 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 26 | log_disk_percentage | 磁盘IO | 0.7437010000000001 | 0.774901 | 0.4464 | MEDIUM | UNKNOWN | numeric | 0.0 | 99.0 | 24.75 |  | offline_importance_rank | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| 27 | log_archive_concurrency | CPU调度 | 0.742933 | 0.754933 | 1.0 | LOW | YES | numeric | 0.0 | 100.0 | 25.0 |  | offline_importance_rank | 并发调度和后台线程会影响事务排队与大查询执行资源。 |
| 28 | memstore_limit_percentage | 内存管理 | 0.689968 | 0.713968 | 0.4464 | MEDIUM | UNKNOWN | numeric | 0.0 | 100.0 | 25.0 |  | week2_top5_core_prior | 内存水位、缓存和冻结行为会影响写入路径与大查询中间结果。 |
| 29 | large_query_worker_percentage | CPU调度 | 0.608501 | 0.620501 | 0.4464 | MEDIUM | UNKNOWN | numeric | 0.0 | 100.0 | 25.0 |  | week2_top5_core_prior | 并发调度和后台线程会影响事务排队与大查询执行资源。 |
| 30 | enable_sql_audit | SQL执行 | 0.581301 | 0.607701 | 0.4464 | MEDIUM | UNKNOWN | bool | 0.0 | 1.0 | 1.0 | True\|False | week2_top5_core_prior | SQL 审计、计划和长查询调度对复杂查询更敏感。 |

## 方法说明

影响力得分由关键词/参数元信息、参数类别先验、workload 相关性、安全可执行性、动态生效、范围可解析性、文档证据共同加权得到。该方法用于在样本不足阶段为 B2 缩小动作空间，后续真实参数实验产出后应替换或叠加 Lasso、RandomForest、XGBoost、SHAP 等数据驱动重要性。
