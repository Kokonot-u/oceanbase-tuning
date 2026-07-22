# B2 离线强化学习调优框架与评估 - real_week4

负责人：Wang

## 框架实现

- State：workload 类型、baseline throughput、avg/P95/P99 latency、error_count，以及 B1 输出的参数特征。
- Action：B1 Top30 参数映射出的安全动作空间，包含 numeric/enum/bool 三类动作。
- Reward：`0.45 * throughput_gain + 0.35 * p95_reduction + 0.10 * p99_reduction - 0.10 * error_penalty - safety_penalty`。
- Agent：当前交付为离线 surrogate policy，等真实改参样本和 A 组系统指标补齐后接入 DDPG/TD3 训练。

## Baseline

- TPC-C：throughput=1.826, P95=716.0 ms。
- TPC-H：throughput=6.5269, P95=192.592 ms。

## 离线策略 Top10

| policy_id | experiment_id | workload_type | parameter_name | recommended_value | expected_metric | estimated_throughput_gain | estimated_p95_reduction | estimated_reward | requires_approval | evidence |
| -- | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| policy_01_tpc-h | real_week4_offline | TPC-H | log_disk_utilization_limit_threshold | 90 | qps | 0.032064 | 0.075744 | 0.04662 | 0 | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| policy_02_tpc-h | real_week4_offline | TPC-H | log_disk_utilization_threshold | 55 | qps | 0.032064 | 0.075744 | 0.04662 | 0 | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| policy_03_tpc-h | real_week4_offline | TPC-H | log_disk_throttling_maximum_duration | 2 | qps | 0.030464 | 0.072144 | 0.04437 | 0 | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| policy_02_tpc-c | real_week4_offline | TPC-C | log_disk_utilization_threshold | 55 | tps | 0.048096 | 0.050496 | 0.043104 | 0 | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| policy_01_tpc-c | real_week4_offline | TPC-C | log_disk_utilization_limit_threshold | 90 | tps | 0.048096 | 0.050496 | 0.043104 | 0 | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| policy_03_tpc-c | real_week4_offline | TPC-C | log_disk_throttling_maximum_duration | 2 | tps | 0.045696 | 0.048096 | 0.041004 | 0 | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| policy_04_tpc-h | real_week4_offline | TPC-H | enable_clog_encryption | True | qps | 0.024437 | 0.058584 | 0.035895 | 0 | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| policy_05_tpc-h | real_week4_offline | TPC-H | log_disk_throttling_percentage | 60 | qps | 0.023211 | 0.055824 | 0.03417 | 0 | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| policy_06_tpc-h | real_week4_offline | TPC-H | standby_db_preferred_upstream_log_region | 50 | qps | 0.023211 | 0.055824 | 0.03417 | 0 | 日志写入、刷盘和 IO 隔离对写事务路径更敏感。 |
| policy_08_tpc-h | real_week4_offline | TPC-H | vector_index_memory_saving_mode | True | qps | 0.022539 | 0.054312 | 0.033225 | 0 | 内存水位、缓存和冻结行为会影响写入路径与大查询中间结果。 |

## 风险边界

本周没有在共享 `test` 租户执行参数修改。所有推荐均为离线建议，必须经 B4 自动化验证框架和人工审批后才能进入真实执行。
