# B1-B2 内部联调测试报告 - real_week4

## 测试目标

验证 B1 Top 参数筛选结果可以自动映射为 B2 动作空间，并生成离线调优策略。

## 测试结果

- B1 输出 Top30 参数：30 个。
- B2 动作空间参数：30 个。
- 离线策略建议：20 条。
- 自动执行允许参数：22 个；其余进入人工审核。

## 映射样例

| experiment_id | rank | parameter_name | category | action_type | current_value | min_value | max_value | step | enum_values | risk_level | can_modify | auto_execute_allowed | requires_approval | action_mask_reason |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| real_week4_offline | 1 | log_disk_utilization_limit_threshold | 磁盘IO | numeric |  | 80.0 | 100.0 | 5.0 |  | LOW | YES | 1 | 0 | allowed_offline_recommendation_only |
| real_week4_offline | 2 | log_disk_utilization_threshold | 磁盘IO | numeric |  | 10.0 | 100.0 | 22.5 |  | LOW | YES | 1 | 0 | allowed_offline_recommendation_only |
| real_week4_offline | 3 | log_disk_throttling_maximum_duration | 磁盘IO | numeric |  | 1.0 | 3.0 | 1.0 |  | LOW | YES | 1 | 0 | allowed_offline_recommendation_only |
| real_week4_offline | 4 | enable_clog_encryption | 磁盘IO | bool |  | 0.0 | 1.0 | 1.0 | True\|False | LOW | YES | 1 | 0 | allowed_offline_recommendation_only |
| real_week4_offline | 5 | log_disk_throttling_percentage | 磁盘IO | numeric |  | 30.0 | 90.0 | 15.0 |  | LOW | YES | 1 | 0 | allowed_offline_recommendation_only |
| real_week4_offline | 6 | standby_db_preferred_upstream_log_region | 磁盘IO | numeric |  | 0.0 | 100.0 | 25.0 |  | LOW | YES | 1 | 0 | allowed_offline_recommendation_only |
| real_week4_offline | 7 | clog_io_isolation_mode | 磁盘IO | enum |  | 1.0 | 2.0 | 1.0 | 1\|2 | MEDIUM | UNKNOWN | 0 | 1 | manual_approval_required_due_to_risk_or_unknown_modifiability |
| real_week4_offline | 8 | vector_index_memory_saving_mode | 内存管理 | bool |  | 0.0 | 1.0 | 1.0 | True\|False | LOW | YES | 1 | 0 | allowed_offline_recommendation_only |
| real_week4_offline | 9 | memory_chunk_cache_size | 内存管理 | numeric |  | 0.0 | 1.0 | 1.0 |  | MEDIUM | UNKNOWN | 0 | 1 | manual_approval_required_due_to_risk_or_unknown_modifiability |
| real_week4_offline | 10 | syslog_io_bandwidth_limit | 磁盘IO | numeric |  | 15.0 | 45.0 | 7.5 |  | MEDIUM | UNKNOWN | 0 | 1 | manual_approval_required_due_to_risk_or_unknown_modifiability |

## 结论

B1 到 B2 的参数名、动作类型、范围、风险等级和审批标记已打通。下一步需要 Huang 的 B4 验证模块消费 `b2_tuning_recommendations_real_week4.csv`，并在授权窗口执行单轮验证。
