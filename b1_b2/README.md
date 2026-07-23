# B1/B2 - OceanBase 智能参数调优

负责人：Wang  
范围：B1 参数影响因子分析、B2 深度强化学习智能调优

本目录是 B1/B2 模块的独立维护入口，集中放 Wang 负责的代码、接口、文档和关键结果。  
根目录旧 `scripts/`、`tests/` 的 B1/B2 相关内容已迁入本目录；这里是便于导师和组内同学查看的模块视图。

## 目录结构

```text
b1_b2/
├── config/
├── code/
│   ├── configs/
│   ├── src/
│   │   ├── b1_analysis/
│   │   └── b2_tuning/
│   ├── sql/
│   ├── scripts/
│   │   ├── real_week2/
│   │   ├── real_week4/
│   │   └── legacy/
│   └── tests/
├── docs/
│   ├── week2/
│   ├── week3/
│   └── week4/
├── interfaces/
│   ├── week3/
│   └── week4/
├── presentations/
│   └── week3/
├── logs/
│   └── week2/
└── results/
    ├── week2/
    └── week4/
```

## 关键产出

### Week 2

- `results/week2/param_candidates_real.csv`：347 个性能相关候选参数。
- `results/week2/top100_performance_params_real.csv`：Top100 性能参数。
- `results/week2/top5_params_real.csv`：B1/B2 初始 Top5 参数。
- `results/week2/param_perf_dataset_real.csv`：轻量 SQL、TPC-C、TPC-H baseline。
- `docs/week2/week2_real_experiment_report.md`：第二周真实实验报告。

### Week 3

- `docs/week3/paper_notes_db_tuning.md`：DB-BERT、OtterTune、CDBTune 论文精读笔记。
- `interfaces/week3/b1_b2_interface_definition_v0.1.md`：B1/B2 接口定义。
- `presentations/week3/oceanbase_b1_b2_tech_solution.html`：HTML 技术方案汇报页。

### Week 4

- `results/week4/b1_feature_matrix_real_week4.csv`：B1 特征矩阵。
- `results/week4/b1_top30_parameter_importance_real_week4.csv`：Top30 参数影响因子权重。
- `interfaces/week4/b2_action_space_real_week4.csv`：B2 动作空间接口。
- `results/week4/b2_tuning_recommendations_real_week4.csv`：B2 离线调优建议。
- `docs/week4/b1_parameter_impact_report_real_week4.md`：B1 参数影响报告。
- `docs/week4/b2_offline_rl_evaluation_real_week4.md`：B2 离线 RL 评估报告。
- `docs/week4/b1_b2_integration_test_report_real_week4.md`：B1-B2 内部联调报告。

## 给 B3/B4 的文件

给 B3 容量预测：

- `results/week4/b1_feature_matrix_real_week4.csv`
- `results/week4/b1_top30_parameter_importance_real_week4.csv`
- `results/week2/param_perf_dataset_real.csv`

给 B4 自动化验证：

- `results/week4/b2_tuning_recommendations_real_week4.csv`
- `interfaces/week4/b2_action_space_real_week4.csv`
- `results/week2/param_perf_dataset_real.csv`
- `docs/week4/b1_b2_integration_test_report_real_week4.md`

## 当前边界

当前 week4 结果基于 week2 真实 baseline 和参数候选表构建，尚未在共享 `test` 租户执行真实参数修改。  
B2 输出是离线策略建议，进入真实执行前需要 B4 验证、人工审批和 rollback 校验。
