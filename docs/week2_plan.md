# 第二周 B 组参数影响测试计划

## 当前状态

第一周 OceanBase 参数表已导出，原始文件位于 `output/ob_parameters.tsv`，第二周规范化副本位于 `outputs/ob_parameters.tsv`。当前环境为 Mac Docker OceanBase 单节点，用于流程验证、参数研究、指标采集和数据集构建。

## 第二周目标

从第一周 100 个关键参数中筛选候选参数，选择 5 个核心参数，设计 3-5 组梯度，准备 TPC-C 和 TPC-H 自动化测试流程，采集 QPS、平均响应时间、P95/P99、CPU、内存、磁盘 IO、错误数等指标，形成参数配置与性能指标数据集。

## 实验负载

- TPC-C / BenchmarkSQL：验证 OLTP 写入、事务并发和排队延迟。
- TPC-H / tpch-obs：验证 OLAP 查询、扫描、Join、聚合和 IO 压力。
- 本机 fallback：工具缺失时生成 dry-run CSV，验证目录、矩阵和汇总流程。

## 参数筛选方法

`scripts/select_param_candidates.py` 从 `outputs/ob_parameters.tsv` 自动识别字段大小写，根据 name、info、section、edit_level 的关键词命中评分，将参数归类为 CPU 调度、内存管理、磁盘 IO、SQL 执行。

## 5 个参数选择原则

优先覆盖四类性能机制，优先选择动态生效或恢复成本较低的参数，不选择明显可能导致 observer 无法启动的高风险参数。无法确认风险时标记为 medium。

## 梯度设计原则

每个参数生成 4 个保守梯度，包含当前值或接近当前值的一档。梯度为实验占位，真实修改前必须核对官方文档范围、当前租户资源和是否需要重启。

## 指标采集方式

- `scripts/collect_metrics.sh` 采集 `docker stats obstandalone --no-stream`。
- `sql/04_collect_sql_audit.sql` 采集 SQL 审计延迟与错误。
- `sql/05_collect_sysstat.sql` 采集系统统计项。

## 数据集格式

核心数据集为 `outputs/param_perf_dataset.csv`，由 `scripts/summarize_results.py` 合并 TPC-C/TPC-H 结果生成。实验矩阵为 `outputs/param_test_matrix.csv`。

## 单节点限制

单节点环境不能验证三副本、多 Zone、高可用、跨节点分布式事务和真实生产容量上限。本周交付重点是流程、数据结构、自动化和首轮轻量验证。

## 第二周交付物

候选参数、Top5 参数、实验矩阵、TPC-C/TPC-H 脚本、指标采集脚本、结果汇总与图表脚本、容量预测基线、自动化验证框架、首轮测试报告和交付总结。
