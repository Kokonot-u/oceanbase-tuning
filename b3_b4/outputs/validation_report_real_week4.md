# B4 参数调优效果自动化验证报告

- experiment_id: `real_week4`
- 执行人: Huang
- 执行时间: 2026-07-23 01:09:31
- 运行模式: `simulation`（simulation=基于 B2 预期收益+真实 baseline 推算；real=连独立测试租户实跑）
- 输入: B2 调优建议 `inputs/b2_tuning_recommendations_real_week4.csv`，baseline 性能 `inputs/baseline_perf/param_perf_dataset_real.csv`

## 1. baseline 基准
| workload | 吞吐指标 | baseline 吞吐 | p95(ms) | p99(ms) | avg(ms) |
| -- | -- | -- | -- | -- | -- |
| TPC-C | tps | 1.8260 | 716.0 | 726.0 | 312.3 |
| TPC-H | qps | 6.5269 | 192.6 | 285.9 | 153.2 |

## 2. 调优参数与取值（调度概况）
- 已批准并自动验证: **14** 条；requires_approval=1 转人工审核: **6** 条

## 3. baseline 与调优后关键指标对比
| workload | 参数 | 建议值 | 吞吐提升% | p95变化% | 错误 | 推广 |
| -- | -- | -- | -- | -- | -- | -- |
| TPC-C | log_disk_utilization_limit_threshold | 90 | +4.03 | -5.83 | 0 | ✅ |
| TPC-C | log_disk_utilization_threshold | 55 | +5.53 | -4.33 | 0 | ✅ |
| TPC-C | log_disk_throttling_maximum_duration | 2 | +4.12 | -5.26 | 0 | ✅ |
| TPC-C | enable_clog_encryption | True | +3.69 | -3.88 | 0 | ✅ |
| TPC-C | log_disk_throttling_percentage | 60 | +3.56 | -3.65 | 0 | ✅ |
| TPC-C | standby_db_preferred_upstream_log_region | 50 | +3.93 | -3.27 | 0 | ✅ |
| TPC-C | vector_index_memory_saving_mode | True | +3.04 | -3.96 | 0 | ✅ |
| TPC-H | log_disk_utilization_limit_threshold | 90 | +3.11 | -7.67 | 0 | ✅ |
| TPC-H | log_disk_utilization_threshold | 55 | +2.60 | -8.18 | 0 | ✅ |
| TPC-H | log_disk_throttling_maximum_duration | 2 | +2.33 | -7.93 | 0 | ✅ |
| TPC-H | enable_clog_encryption | True | +2.60 | -5.70 | 0 | ✅ |
| TPC-H | log_disk_throttling_percentage | 60 | +2.63 | -5.27 | 0 | ✅ |
| TPC-H | standby_db_preferred_upstream_log_region | 50 | +2.93 | -4.97 | 0 | ✅ |
| TPC-H | vector_index_memory_saving_mode | True | +2.47 | -5.21 | 0 | ✅ |

## 4. 待人工审核（未自动执行）
| workload | 参数 | 建议值 | 说明 |
| -- | -- | -- | -- |
| TPC-C | clog_io_isolation_mode | 2 | requires_approval=1，高风险，未自动执行，转人工审核 |
| TPC-C | memory_chunk_cache_size | 0.5 | requires_approval=1，高风险，未自动执行，转人工审核 |
| TPC-C | syslog_io_bandwidth_limit | 30 | requires_approval=1，高风险，未自动执行，转人工审核 |
| TPC-H | clog_io_isolation_mode | 2 | requires_approval=1，高风险，未自动执行，转人工审核 |
| TPC-H | memory_chunk_cache_size | 0.5 | requires_approval=1，高风险，未自动执行，转人工审核 |
| TPC-H | syslog_io_bandwidth_limit | 30 | requires_approval=1，高风险，未自动执行，转人工审核 |

## 5. 是否建议在生产环境推广的结论
建议优先在生产灰度验证以下 **14** 条通过自动化验证的参数：

> log_disk_utilization_limit_threshold(TPC-C), log_disk_utilization_threshold(TPC-C), log_disk_throttling_maximum_duration(TPC-C), enable_clog_encryption(TPC-C), log_disk_throttling_percentage(TPC-C), standby_db_preferred_upstream_log_region(TPC-C), vector_index_memory_saving_mode(TPC-C), log_disk_utilization_limit_threshold(TPC-H), log_disk_utilization_threshold(TPC-H), log_disk_throttling_maximum_duration(TPC-H), enable_clog_encryption(TPC-H), log_disk_throttling_percentage(TPC-H), standby_db_preferred_upstream_log_region(TPC-H), vector_index_memory_saving_mode(TPC-H)

> 所有变更均附带 `rollback_sql`，推广前需在独立测试租户复跑确认，并保留回滚路径。

## 6. 复现
```
python -m b4_validation.run_b4
```
