# 首轮 5 个参数影响测试报告

## 实验背景

B 组第二周任务是在第一周 OceanBase 关键参数表基础上，选择核心参数并构建参数影响测试流程。当前环境为 Mac Docker OceanBase 单节点。

## 实验目标

筛选性能相关参数，选择 5 个核心参数，设计梯度，准备 TPC-C/TPC-H 自动化测试，采集吞吐、延迟、CPU、内存、磁盘 IO 和错误数，形成参数配置-性能指标数据集。

## 实验环境

- OceanBase：Docker 单节点，MySQL 模式。
- 主机：Mac 本机。
- 负载：BenchmarkSQL/TPC-C、TPC-H/tpch-obs。
- 当前限制：未假设三节点、三副本、多 Zone 或高可用能力。

## 数据来源

参数源为 `outputs/ob_parameters.tsv`，由第一周导出。候选参数由 `scripts/select_param_candidates.py` 从 name、info、section、edit_level 自动评分生成。

## 参数候选筛选方法

按 CPU 调度、内存管理、磁盘 IO、SQL 执行四类关键词筛选。字段权重为 name 高于 section，高于 info；动态生效参数额外加分。

## 5 个核心参数选择依据

`scripts/choose_top5_params.py` 按类别覆盖、score、edit_level 和风险等级选择。高风险参数不纳入首轮。无法确认风险的参数标记为 medium。

## 参数梯度设计

每个参数生成 4 档梯度，包含保守值、当前值或接近当前值、较激进值。所有梯度均需人工确认官方范围。

## 工作负载设计

TPC-C 关注 OLTP 并发事务和延迟分位。TPC-H 关注 22 条分析查询的执行耗时和失败查询数。工具缺失时只生成 dry-run 结果。

## 指标采集方法

系统指标由 `docker stats obstandalone --no-stream` 采集到 `outputs/metrics_log.csv`。SQL 审计和 sysstat SQL 已放在 `sql/04_collect_sql_audit.sql`、`sql/05_collect_sysstat.sql`。

## 实验结果表格

真实 BenchmarkSQL/TPC-H 长时间测试尚未完成。当前已生成 dry-run 流程产物，真实结果应在安装工具并运行后进入 `outputs/param_perf_dataset.csv`。

| 类型 | 文件 | 当前状态 | 说明 |
| -- | -- | -- | -- |
| 候选参数 | outputs/param_candidates.csv | 已生成 | 来自真实参数表 |
| Top5 参数 | outputs/selected_5_params.csv | 已生成 | 梯度需人工确认 |
| 实验矩阵 | outputs/param_test_matrix.csv | 已生成 | 覆盖 TPC-C/TPC-H |
| TPC-C 结果 | outputs/tpcc_result_*.csv | dry-run | BenchmarkSQL 未安装时生成 |
| TPC-H 结果 | outputs/tpch_result_*.csv | dry-run | tpch-obs 未安装时生成 |

## 参数影响趋势分析

当前没有真实数值指标，不能给出真实性能趋势。图表脚本会在真实 QPS/延迟数据出现后生成趋势图。

## 风险与限制

单节点环境不能验证多副本和跨节点事务；dry-run 不能代表性能；参数修改存在稳定性风险，必须记录原始值并恢复。

## 当前完成情况

已完成：脚本、数据结构、候选筛选、测试矩阵、dry-run 流程、文档和模板。

待完成：真实 BenchmarkSQL/TPC-H 长时间测试。

原因：本机资源、BenchmarkSQL/TPC-H 工具安装和执行时间限制。

下一步命令：

```bash
python3 scripts/select_param_candidates.py
python3 scripts/choose_top5_params.py
python3 scripts/generate_test_matrix.py
bash scripts/run_param_experiment.sh 1
python3 scripts/summarize_results.py
```
