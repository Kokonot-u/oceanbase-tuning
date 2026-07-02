# 自动化验证框架设计

## 目标

将参数选择、矩阵生成、负载执行、指标采集、结果汇总、图表和报告生成串成可复现流程。

## 输入

`outputs/selected_5_params.csv`、`outputs/param_test_matrix.csv`、TPC-C 配置、TPC-H 配置和 OceanBase 连接信息。

## 执行步骤

环境检查、参数原始值记录、参数修改、workload 执行、指标采集、结果汇总、参数恢复、报告生成。

## 输出

`outputs/param_perf_dataset.csv`、`outputs/param_perf_summary.csv`、`outputs/figures/`、`docs/first_round_param_test_report.md`。

## 安全机制

默认 dry-run、人工确认、参数恢复、日志记录。总控脚本不会自动执行 `ALTER SYSTEM SET`。

## 后续扩展

接入 Prometheus、GitHub Actions、多节点环境和异常注入数据，增强真实实验覆盖。
