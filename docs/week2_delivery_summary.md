# 第二周交付总结

## 任务对应关系

| 任务 | 要求 | 当前交付物 | 状态 | 说明 |
| -- | -- | -- | -- | -- |
| BenchmarkSQL/TPC-C | 自动化测试能力 | scripts/run_tpcc_test.sh, docs/benchmarksql_setup_guide.md | 已完成流程 | 工具缺失时 dry-run |
| TPC-H | 自动化测试能力 | scripts/run_tpch_test.sh, docs/tpch_setup_guide.md | 已完成流程 | 工具缺失时 dry-run |
| 参数候选筛选 | 从参数表筛选候选 | scripts/select_param_candidates.py, outputs/param_candidates.csv | 已完成 | 使用真实参数表 |
| 选择 5 个参数 | 覆盖四类机制 | scripts/choose_top5_params.py, outputs/selected_5_params.csv | 已完成 | 梯度需人工确认 |
| 参数梯度 | 每参数 3-5 档 | outputs/selected_5_params.csv | 已完成 | 4 档 |
| 执行负载 | TPC-C/TPC-H | scripts/run_param_experiment.sh | 已完成流程 | 真实运行待工具安装 |
| 指标采集 | CPU/内存/IO 等 | scripts/collect_metrics.sh, outputs/metrics_log.csv | 已完成脚本 | 容器未运行时明确报错 |
| 数据集 | 参数配置-性能指标 | outputs/param_perf_dataset.csv | 已完成模板 | dry-run 保留 status |
| 首轮报告 | 5 参数影响测试报告 | docs/first_round_param_test_report.md | 已完成 | 未伪造真实结果 |
| 容量预测 | 实验方案和基线 | docs/capacity_prediction_plan.md, scripts/capacity_forecast_baseline.py | 已完成 | 数据不足时生成模板 |
| 自动化验证 | 框架设计 | docs/automation_validation_framework.md | 已完成 | 包含安全机制 |

## 如何运行

```bash
pip install -r requirements.txt
python3 scripts/select_param_candidates.py
python3 scripts/choose_top5_params.py
python3 scripts/generate_test_matrix.py
bash scripts/run_param_experiment.sh 1
python3 scripts/summarize_results.py
python3 scripts/plot_param_results.py
python3 scripts/capacity_forecast_baseline.py
```

## 当前限制

未安装 BenchmarkSQL/tpch-obs 或 OceanBase 容器未启动时，脚本生成 dry-run 或明确报错。dry-run 只用于验证流程，不代表真实性能。

## 下一步计划

安装 BenchmarkSQL 和 tpch-obs，启动 OceanBase 单节点，按矩阵逐项执行真实负载，补齐真实 QPS、延迟分位和查询耗时。
