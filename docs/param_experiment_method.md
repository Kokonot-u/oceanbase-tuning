# 参数影响实验方法

## 流程

1. 导出或确认 `outputs/ob_parameters.tsv`。
2. 运行 `python3 scripts/select_param_candidates.py` 生成候选参数。
3. 运行 `python3 scripts/choose_top5_params.py` 生成 5 个核心参数与梯度。
4. 运行 `python3 scripts/generate_test_matrix.py` 展开 TPC-C/TPC-H 实验矩阵。
5. 人工核对官方文档、参数范围、风险等级和是否需要重启。
6. 记录原始值，必要时手工执行参数修改。
7. 运行 workload，采集实验前后指标。
8. 汇总结果并恢复参数。

## 安全要求

所有脚本默认不执行 `ALTER SYSTEM SET`。参数修改只通过模板输出 SQL，由操作者确认后手工执行。实验后必须恢复原始值，并在 `experiment_log` 中记录。

## 指标

TPC-C 关注 QPS、平均延迟、P95/P99 和错误数。TPC-H 关注 22 条查询耗时、总耗时、平均耗时和失败查询数。系统侧记录 CPU、内存、网络、磁盘 IO 和 PIDs。
