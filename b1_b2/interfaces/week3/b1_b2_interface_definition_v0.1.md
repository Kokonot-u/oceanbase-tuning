# OceanBase 智能运维项目 B1/B2 接口定义文档 v0.1

负责人：Wang  
模块范围：B 组 B1 参数影响因子分析、B2 深度强化学习智能调优  
对齐文档：A 组提供的《OceanBase 智能运维项目跨组接口定义文档 v0.1》  
日期：2026-07-09

## 1. 文档目的

本文档用于明确 B1/B2 模块在第三周阶段的数据输入、内部流转、对外输出、文件命名和字段定义。

B1/B2 的核心目标是：基于 A 组提供的正常负载数据、系统表数据、异常标签数据，以及第二周已有的参数-性能初始数据，完成参数影响因子分析和强化学习调优接口设计，为后续参数实验、性能复盘和 C 组容量预测提供统一数据格式。

本文档遵循跨组接口 v0.1 中已确认的规则：

- 时间格式统一为 `YYYY-MM-DD HH:MM:SS`。
- 默认时区为 `Asia/Shanghai`。
- 默认采样粒度为 60 秒。
- 参数配置数据使用 `parameter_config_{experiment_id}.csv`。
- 参数-性能结果数据使用 `parameter_performance_{experiment_id}.csv`。
- 所有跨组交付文件需要在 Release 目录中配套 `README_dataset.md` 和 `data_schema.yaml`。

## 2. B1/B2 模块边界

| 模块 | 输入 | 输出 | 主要职责 |
| -- | -- | -- | -- |
| B1 参数影响因子分析 | A 组正常负载数据、系统表数据、异常标签、B 组参数测试结果 | 参数候选表、特征矩阵、特征重要性表、参数影响分析报告 | 构建参数-性能样本，筛选关键参数和关键指标，解释参数对性能的影响方向 |
| B2 强化学习智能调优 | B1 特征矩阵、参数搜索空间、历史实验结果、性能目标 | RL 状态空间、动作空间、奖励函数定义、调优建议表、参数配置实验表 | 将参数调优问题建模为强化学习过程，生成可执行或可审核的参数调优方案 |

## 3. 数据流转关系

```text
A组 normal_load / system_tables / anomaly_labels
        |
        v
B1 参数-性能样本构造
        |
        v
B1 特征工程与影响因子分析
        |
        +--> B1 输出 feature_matrix / feature_importance / parameter_candidates
        |
        v
B2 强化学习调优建模
        |
        +--> B2 输出 rl_state_space / rl_action_space / reward_definition
        |
        v
B组 parameter_config / parameter_performance
        |
        +--> A组用于异常分析复盘
        +--> C组用于容量预测和资源需求分析
```

## 4. 目录结构规范

B 组第三周建议采用以下目录结构：

```text
release/
├── README_dataset.md
├── data_schema.yaml
├── parameter_tests/
│   ├── parameter_config_exp001.csv
│   └── parameter_performance_exp001.csv
├── b1_feature_analysis/
│   ├── b1_parameter_candidates_exp001.csv
│   ├── b1_feature_matrix_exp001.csv
│   ├── b1_feature_importance_exp001.csv
│   └── b1_parameter_impact_report_exp001.md
├── b2_rl_tuning/
│   ├── b2_param_search_space_exp001.yaml
│   ├── b2_rl_state_space_exp001.csv
│   ├── b2_rl_action_space_exp001.csv
│   ├── b2_reward_definition_exp001.yaml
│   └── b2_tuning_recommendations_exp001.csv
└── docs/
    └── b1_b2_interface_definition_v0.1.md
```

当前项目内建议落地到：

```text
docs/real_week3/
outputs/real_week3/
scripts/real_week3/
```

## 5. B 组对外接口一：参数配置数据

该接口沿用跨组接口文档第 10 节，用于记录每次参数实验实际采用或计划采用的参数配置。

### 5.1 文件命名

```text
parameter_config_{experiment_id}.csv
```

示例：

```text
parameter_config_exp001.csv
```

### 5.2 字段定义

| 字段名 | 类型 | 是否必填 | 说明 |
| -- | -- | -- | -- |
| `experiment_id` | string | 是 | 实验编号 |
| `parameter_name` | string | 是 | 参数名称 |
| `parameter_value` | string | 是 | 参数取值 |
| `parameter_category` | string | 否 | 参数类别，如 CPU / memory / io / sql |
| `workload_type` | string | 是 | 负载类型，如 TPC-C / TPC-H / lightweight_sql |
| `workload_scale` | string | 是 | 负载规模，如 1w / 100w / 10g / 1warehouse |
| `start_time` | datetime | 是 | 实验开始时间 |
| `end_time` | datetime | 是 | 实验结束时间 |
| `operator` | string | 是 | 执行人 |
| `remark` | string | 否 | 备注 |

### 5.3 示例

```csv
experiment_id,parameter_name,parameter_value,parameter_category,workload_type,workload_scale,start_time,end_time,operator,remark
exp001,cpu_quota_concurrency,8,CPU,TPC-C,1warehouse,2026-07-09 14:00:00,2026-07-09 15:00:00,Wang,planned tuning experiment
exp001,memstore_limit_percentage,40,memory,TPC-C,1warehouse,2026-07-09 14:00:00,2026-07-09 15:00:00,Wang,planned tuning experiment
```

### 5.4 与当前项目文件映射

| 当前文件 | 可转换目标 |
| -- | -- |
| `outputs/real_week2/param_test_matrix_real.csv` | `parameter_config_{experiment_id}.csv` |
| `outputs/real_week2/top5_params_real.csv` | `b1_parameter_candidates_{experiment_id}.csv` / `parameter_config_{experiment_id}.csv` |

## 6. B 组对外接口二：参数-性能结果数据

该接口沿用跨组接口文档第 11 节，用于记录某组参数配置下的性能表现。

### 6.1 文件命名

```text
parameter_performance_{experiment_id}.csv
```

示例：

```text
parameter_performance_exp001.csv
```

### 6.2 字段定义

| 字段名 | 类型 | 是否必填 | 说明 |
| -- | -- | -- | -- |
| `experiment_id` | string | 是 | 实验编号 |
| `parameter_name` | string | 是 | 参数名称，baseline 可填 `baseline` |
| `parameter_value` | string | 是 | 参数取值，baseline 可填 `current_real_values` |
| `workload_type` | string | 是 | 负载类型 |
| `workload_scale` | string | 是 | 负载规模 |
| `qps` | float | 否 | 每秒查询数 |
| `tps` | float | 否 | 每秒事务数 |
| `avg_latency_ms` | float | 否 | 平均响应时间 |
| `p95_latency_ms` | float | 否 | P95 延迟 |
| `p99_latency_ms` | float | 否 | P99 延迟 |
| `transaction_success_rate` | float | 否 | 事务成功率 |
| `cpu_usage` | float | 否 | CPU 使用率，取值范围 0 到 1 |
| `memory_usage` | float | 否 | 内存使用率，取值范围 0 到 1 |
| `disk_usage` | float | 否 | 磁盘使用率，取值范围 0 到 1 |
| `active_session_num` | float | 否 | 活跃会话数 |
| `wait_event_time` | float | 否 | 等待事件耗时 |
| `error_count` | int | 否 | 错误数量 |
| `remark` | string | 否 | 备注 |

### 6.3 示例

```csv
experiment_id,parameter_name,parameter_value,workload_type,workload_scale,qps,tps,avg_latency_ms,p95_latency_ms,p99_latency_ms,transaction_success_rate,cpu_usage,memory_usage,disk_usage,active_session_num,wait_event_time,error_count,remark
exp001,baseline,current_real_values,TPC-C,1warehouse,,1.826,312.3,716.0,726.0,1.0,,,,,,0,real BenchmarkSQL baseline
exp001,baseline,current_real_values,TPC-H,22queries,6.5269,,153.213,192.592,285.852,1.0,,,,,,0,real TPCH 22-query baseline
```

### 6.4 与当前项目文件映射

| 当前文件 | 可转换目标 |
| -- | -- |
| `outputs/real_week2/param_perf_dataset_real.csv` | `parameter_performance_{experiment_id}.csv` |
| `outputs/real_week2/tpcc_benchmarksql_real.csv` | `parameter_performance_{experiment_id}.csv` |
| `outputs/real_week2/tpch_22_summary_real.csv` | `parameter_performance_{experiment_id}.csv` |
| `outputs/real_week2/workload_summary_real.csv` | `parameter_performance_{experiment_id}.csv` |

## 7. B1 内部接口一：参数候选表

该接口用于记录 B1 从 OceanBase 参数表、参数说明和历史实验中筛选出的候选参数。

### 7.1 文件命名

```text
b1_parameter_candidates_{experiment_id}.csv
```

### 7.2 字段定义

| 字段名 | 类型 | 是否必填 | 说明 |
| -- | -- | -- | -- |
| `experiment_id` | string | 是 | 实验编号 |
| `parameter_name` | string | 是 | 参数名称 |
| `parameter_category` | string | 是 | 参数类别，枚举：CPU / memory / io / sql / cache / other |
| `current_value` | string | 是 | 当前值 |
| `default_value` | string | 否 | 默认值 |
| `value_range` | string | 否 | 参数取值范围 |
| `scope` | string | 否 | 参数作用域，如 tenant / cluster / server |
| `edit_level` | string | 否 | 是否动态生效 |
| `risk_level` | string | 是 | 风险等级，枚举：low / medium / high |
| `can_modify` | string | 是 | 是否建议直接修改，枚举：yes / no / unknown |
| `score` | float | 是 | 候选参数评分 |
| `evidence_source` | string | 是 | 证据来源，如 SHOW PARAMETERS / docs / experiment |
| `expected_effect` | string | 否 | 预期影响 |
| `remark` | string | 否 | 备注 |

### 7.3 与当前项目文件映射

```text
outputs/real_week2/param_candidates_real.csv
outputs/real_week2/top100_performance_params_real.csv
outputs/real_week2/top5_params_real.csv
```

## 8. B1 内部接口二：特征矩阵

该接口用于将 A 组监控指标、系统表数据、B 组参数配置和 workload 结果对齐为机器学习可用样本。

### 8.1 文件命名

```text
b1_feature_matrix_{experiment_id}.csv
```

### 8.2 字段定义

| 字段名 | 类型 | 是否必填 | 说明 |
| -- | -- | -- | -- |
| `sample_id` | string | 是 | 样本编号 |
| `experiment_id` | string | 是 | 实验编号 |
| `timestamp` | datetime | 是 | 聚合时间点 |
| `workload_type` | string | 是 | 负载类型 |
| `workload_scale` | string | 是 | 负载规模 |
| `parameter_name` | string | 是 | 参数名称 |
| `parameter_value_numeric` | float | 否 | 数值化后的参数值 |
| `parameter_value_raw` | string | 是 | 原始参数值 |
| `cpu_usage` | float | 否 | CPU 使用率 |
| `memory_usage` | float | 否 | 内存使用率 |
| `disk_usage` | float | 否 | 磁盘使用率 |
| `active_session_num` | float | 否 | 活跃会话数 |
| `wait_event_time` | float | 否 | 等待事件耗时 |
| `qps` | float | 否 | QPS |
| `tps` | float | 否 | TPS |
| `avg_latency_ms` | float | 否 | 平均延迟 |
| `p95_latency_ms` | float | 否 | P95 延迟 |
| `p99_latency_ms` | float | 否 | P99 延迟 |
| `error_count` | int | 否 | 错误数 |
| `target_metric` | string | 是 | 建模目标，如 `avg_latency_ms` / `tps` |
| `target_value` | float | 是 | 建模目标值 |
| `anomaly_label` | int | 否 | 正常为 0，异常为 1 |
| `anomaly_type` | string | 否 | 异常类型 |

### 8.3 样本构造规则

- 以 `experiment_id + workload_type + workload_scale + timestamp` 对齐参数配置与性能结果。
- 对正常负载数据按 60 秒窗口聚合。
- 延迟指标保留 `avg_latency_ms`、`p95_latency_ms`、`p99_latency_ms`。
- 参数值优先保留原始字符串，同时尽量生成 `parameter_value_numeric`。
- 若某指标缺失，不直接删除样本，先保留空值，并在 `README_dataset.md` 中说明缺失原因。

## 9. B1 内部接口三：特征重要性表

该接口用于输出 B1 的参数影响因子分析结果，可由 Scikit-learn / XGBoost / RandomForest / SHAP 等方法生成。

### 9.1 文件命名

```text
b1_feature_importance_{experiment_id}.csv
```

### 9.2 字段定义

| 字段名 | 类型 | 是否必填 | 说明 |
| -- | -- | -- | -- |
| `experiment_id` | string | 是 | 实验编号 |
| `target_metric` | string | 是 | 目标指标 |
| `feature_name` | string | 是 | 特征名称 |
| `feature_type` | string | 是 | 特征类型，枚举：parameter / metric / workload / time |
| `importance_score` | float | 是 | 重要性得分 |
| `rank` | int | 是 | 排名 |
| `method` | string | 是 | 方法，如 xgboost / random_forest / mutual_info / shap |
| `direction` | string | 否 | 影响方向，枚举：positive / negative / unknown |
| `interpretation` | string | 否 | 自然语言解释 |

### 9.3 示例

```csv
experiment_id,target_metric,feature_name,feature_type,importance_score,rank,method,direction,interpretation
exp001,avg_latency_ms,cpu_quota_concurrency,parameter,0.31,1,xgboost,negative,提高并发配额可能降低排队延迟，但过高会增加 CPU 争用
exp001,avg_latency_ms,memstore_limit_percentage,parameter,0.22,2,xgboost,unknown,影响写入冻结与内存水位，需要结合内存使用率判断
```

## 10. B2 内部接口一：参数搜索空间

该接口用于定义强化学习或搜索算法可以调整的参数范围。

### 10.1 文件命名

```text
b2_param_search_space_{experiment_id}.yaml
```

### 10.2 字段定义

```yaml
experiment_id: exp001
version: v0.1
owner: Wang
parameters:
  - name: cpu_quota_concurrency
    category: CPU
    current_value: 4
    min_value: 1
    max_value: 20
    candidate_values: [4, 8]
    value_type: int
    risk_level: low
    dynamic_effective: true
    rollback_value: 4
  - name: memstore_limit_percentage
    category: memory
    current_value: 0
    min_value: 0
    max_value: 100
    candidate_values: [20, 40]
    value_type: int
    risk_level: medium
    dynamic_effective: unknown
    rollback_value: 0
```

### 10.3 约束规则

- 高风险参数默认不进入自动执行动作空间，只进入人工审核列表。
- 共享租户环境下，所有参数变更必须标记为 `planned`，不能自动执行。
- 每个参数必须提供 `rollback_value`。

## 11. B2 内部接口二：RL 状态空间

该接口用于定义强化学习环境中的 state，即当前参数和性能状态。

### 11.1 文件命名

```text
b2_rl_state_space_{experiment_id}.csv
```

### 11.2 字段定义

| 字段名 | 类型 | 是否必填 | 说明 |
| -- | -- | -- | -- |
| `state_id` | string | 是 | 状态编号 |
| `experiment_id` | string | 是 | 实验编号 |
| `step` | int | 是 | 调优步数 |
| `timestamp` | datetime | 是 | 状态记录时间 |
| `workload_type` | string | 是 | 负载类型 |
| `workload_scale` | string | 是 | 负载规模 |
| `parameter_vector_json` | JSON string | 是 | 当前参数向量 |
| `metric_vector_json` | JSON string | 是 | 当前性能指标向量 |
| `baseline_metric_json` | JSON string | 否 | baseline 指标 |
| `normalized_state_json` | JSON string | 否 | 归一化后的状态向量 |
| `is_terminal` | int | 是 | 是否终止状态，0/1 |

### 11.3 状态向量建议

```text
state = [
  normalized_parameter_values,
  qps_or_tps_ratio_to_baseline,
  avg_latency_ratio_to_baseline,
  p95_latency_ratio_to_baseline,
  p99_latency_ratio_to_baseline,
  cpu_usage,
  memory_usage,
  disk_usage,
  active_session_num_normalized,
  wait_event_time_normalized,
  error_count
]
```

## 12. B2 内部接口三：RL 动作空间

该接口用于定义每一步调优动作。

### 12.1 文件命名

```text
b2_rl_action_space_{experiment_id}.csv
```

### 12.2 字段定义

| 字段名 | 类型 | 是否必填 | 说明 |
| -- | -- | -- | -- |
| `action_id` | string | 是 | 动作编号 |
| `experiment_id` | string | 是 | 实验编号 |
| `parameter_name` | string | 是 | 参数名称 |
| `action_type` | string | 是 | 动作类型：keep / increase / decrease / set_value |
| `old_value` | string | 是 | 调整前取值 |
| `new_value` | string | 是 | 调整后取值 |
| `risk_level` | string | 是 | 风险等级 |
| `requires_approval` | int | 是 | 是否需要人工确认，0/1 |
| `rollback_sql` | string | 是 | 回滚 SQL |
| `status` | string | 是 | planned / executed / skipped / rolled_back |
| `remark` | string | 否 | 备注 |

### 12.3 动作编码

| action_type | 含义 |
| -- | -- |
| `keep` | 参数不变 |
| `increase` | 按预设步长增加 |
| `decrease` | 按预设步长减少 |
| `set_value` | 设置为候选值 |

## 13. B2 内部接口四：奖励函数定义

该接口用于固定 B2 强化学习的优化目标，避免不同实验间奖励不可比。

### 13.1 文件命名

```text
b2_reward_definition_{experiment_id}.yaml
```

### 13.2 建议格式

```yaml
experiment_id: exp001
version: v0.1
reward_mode: composite
baseline:
  throughput_metric: tps
  latency_metric: p95_latency_ms
formula:
  throughput_weight: 0.45
  latency_weight: 0.35
  error_weight: 0.10
  risk_weight: 0.10
definition: >
  reward = 45 * throughput_improvement
         + 35 * latency_improvement
         - 10 * error_penalty
         - 10 * risk_penalty
constraints:
  max_error_count: 0
  p99_latency_regression_limit: 0.20
  require_rollback_sql: true
```

### 13.3 指标计算

```text
throughput_improvement = (new_tps - baseline_tps) / max(baseline_tps, 1)
latency_improvement = (baseline_p95_latency_ms - new_p95_latency_ms) / max(baseline_p95_latency_ms, 1)
error_penalty = 1 if error_count > 0 else 0
risk_penalty = 0 for low, 0.5 for medium, 1 for high
```

## 14. B2 对外接口：调优建议表

该接口用于将 B2 的输出转化为人工可审核的调优建议。该表不等价于实际执行记录，实际执行后仍需生成 `parameter_config_{experiment_id}.csv` 和 `parameter_performance_{experiment_id}.csv`。

### 14.1 文件命名

```text
b2_tuning_recommendations_{experiment_id}.csv
```

### 14.2 字段定义

| 字段名 | 类型 | 是否必填 | 说明 |
| -- | -- | -- | -- |
| `recommendation_id` | string | 是 | 建议编号 |
| `experiment_id` | string | 是 | 实验编号 |
| `parameter_name` | string | 是 | 参数名称 |
| `current_value` | string | 是 | 当前值 |
| `recommended_value` | string | 是 | 建议值 |
| `expected_effect` | string | 是 | 预期收益 |
| `target_metric` | string | 是 | 目标指标 |
| `expected_improvement_pct` | float | 否 | 预期提升比例 |
| `risk_level` | string | 是 | 风险等级 |
| `requires_approval` | int | 是 | 是否需要人工确认 |
| `rollback_sql` | string | 是 | 回滚 SQL |
| `evidence` | string | 是 | 证据来源 |
| `status` | string | 是 | proposed / approved / rejected / executed |
| `remark` | string | 否 | 备注 |

### 14.3 示例

```csv
recommendation_id,experiment_id,parameter_name,current_value,recommended_value,expected_effect,target_metric,expected_improvement_pct,risk_level,requires_approval,rollback_sql,evidence,status,remark
rec001,exp001,cpu_quota_concurrency,4,8,提高事务并发处理能力,tps,10.0,low,1,"ALTER SYSTEM SET cpu_quota_concurrency = '4';",B1 feature importance + RL policy,proposed,shared tenant requires manual approval
```

## 15. B1/B2 与 A 组输入接口

B1/B2 依赖 A 组输出以下数据：

| A 组文件类型 | B1 用途 | B2 用途 |
| -- | -- | -- |
| `normal_load_{workload}_{scale}_{start_date}_{duration}.csv` | 构造正常性能基线、提取 workload 特征 | 作为 baseline state |
| `system_table_{table_name}_{start_date}_{duration}.csv` | 提取 CPU、内存、SQL、等待事件等指标 | 构造 state 中的 metric vector |
| `anomaly_labels_{experiment_date}.csv` | 标记异常样本，分析参数对异常指标的影响 | 用于 reward 中的错误/风险惩罚 |

B1/B2 对 A 组输入数据的最低字段要求：

- 必须包含 `experiment_id`，用于与 B 组参数实验关联。
- 必须包含统一时间字段，如 `timestamp` 或 `collect_time`。
- 必须包含 `workload_type` 和 `workload_scale`。
- 指标类数据必须包含 `metric_name`、`metric_value` 或等价字段。
- 异常标签必须包含 `anomaly_type`、`start_time`、`end_time`。

## 16. B1/B2 与 C 组输出接口

B1/B2 向 C 组提供以下数据：

| B 组输出 | C 组用途 |
| -- | -- |
| `parameter_performance_{experiment_id}.csv` | 判断不同参数配置对资源使用和吞吐/延迟的影响 |
| `b1_feature_importance_{experiment_id}.csv` | 选择容量预测输入特征 |
| `b1_feature_matrix_{experiment_id}.csv` | 作为容量预测或资源需求建模的辅助样本 |
| `b2_tuning_recommendations_{experiment_id}.csv` | 评估参数调优后的资源容量变化 |

建议 C 组优先使用字段：

```text
timestamp
workload_type
workload_scale
cpu_usage
memory_usage
disk_usage
active_session_num
qps
tps
avg_latency_ms
p99_latency_ms
parameter_name
parameter_value
```

## 17. 数据清洗与标准化规则

### 17.1 时间对齐

- 所有实验数据统一按 60 秒窗口聚合。
- 参数实验必须记录 `start_time` 和 `end_time`。
- 若参数生效存在延迟，需在 `remark` 中说明，并可增加 warmup 时间。

### 17.2 缺失值处理

| 缺失情况 | 处理方式 |
| -- | -- |
| 单点指标缺失 | 前向填充或保留空值 |
| 连续短缺失 | 插值或前向填充，并记录处理方式 |
| 长时间缺失 | 标记为 invalid，不进入训练 |
| 指标完全缺失 | 从本轮特征集中移除 |

### 17.3 异常值处理

异常值不直接删除，优先增加以下字段：

| 字段名 | 说明 |
| -- | -- |
| `is_outlier` | 是否异常值 |
| `outlier_method` | 异常值识别方法 |
| `clean_strategy` | 清洗策略 |

### 17.4 参数值数值化

| 原始类型 | 示例 | 数值化规则 |
| -- | -- | -- |
| 整数 | `4` | 转为 4 |
| 百分比 | `80%` | 转为 80 |
| 容量 | `1G`, `512M` | 转为 MB 或 bytes，需在 schema 中注明单位 |
| 时间 | `100ms`, `5s`, `2h` | 转为 ms |
| 布尔 | `True`, `False` | 转为 1 / 0 |
| 枚举 | `AUTO`, `ALL` | 保留原始值，并做 one-hot 或 label encoding |

## 18. 当前第二周真实数据到第三周接口的映射

| 第二周真实产物 | 第三周接口文件 |
| -- | -- |
| `outputs/real_week2/param_candidates_real.csv` | `outputs/real_week3/b1_feature_analysis/b1_parameter_candidates_exp001.csv` |
| `outputs/real_week2/top5_params_real.csv` | `outputs/real_week3/b2_rl_tuning/b2_param_search_space_exp001.yaml` |
| `outputs/real_week2/param_test_matrix_real.csv` | `outputs/real_week3/parameter_tests/parameter_config_exp001.csv` |
| `outputs/real_week2/param_perf_dataset_real.csv` | `outputs/real_week3/parameter_tests/parameter_performance_exp001.csv` |
| `outputs/real_week2/figures/latency_comparison.png` | B1/B2 技术方案 PPT 的 baseline 图 |

## 19. 版本管理

| 版本 | 日期 | 修改人 | 修改内容 |
| -- | -- | -- | -- |
| v0.1 | 2026-07-09 | Wang | 初版 B1/B2 接口定义，对齐 A 组跨组接口 v0.1，并补充 B1/B2 内部字段 |

后续版本升级规则：

1. 新增字段：小版本升级，例如 v0.1 到 v0.2。
2. 修改字段含义：必须记录修改原因，并通知 A/C 组。
3. 删除字段：原则上不直接删除，先标记 deprecated。
4. 文件命名规则变化：必须同步更新 `README_dataset.md`、`data_schema.yaml` 和 Release 说明。

## 20. 待确认事项

| 事项 | 需要确认对象 | 当前建议 |
| -- | -- | -- |
| A 组是否统一输出 `experiment_id` | A 组 | 必须保留，否则 B 组无法关联参数实验 |
| A 组系统表是否提供 CPU/memory/disk/session/wait event 指标 | A 组 | 至少提供跨组文档第 12 节中 C 组也需要的基础字段 |
| 参数实验是否能在独立租户执行 | 老师/环境负责人 | 共享 `test` 租户只生成计划，不自动执行 |
| C 组是否需要 B1 特征重要性表 | C 组 | 建议需要，可辅助容量预测特征筛选 |
| B2 调优建议是否允许自动执行 | 全组确认 | v0.1 阶段默认人工审核 |

