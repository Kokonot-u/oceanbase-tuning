# TPC-H 设置指南

TPC-H 用于 OLAP 查询测试，覆盖扫描、过滤、Join、聚合和排序等分析型负载，适合观察 SQL 执行和 IO 参数对长查询的影响。

## 工具准备

优先使用 OceanBase 适配版 tpch-obs，也可以先用本地 tpch 工具验证 22 条标准查询流程。连接配置参考 `configs/tpch_config.example.env`。

## 数据规模

标准任务可使用 10GB 数据集。本机 Docker 单节点建议先使用 100MB 或 1GB，确认加载、查询和指标采集流程稳定后，再尝试 10GB。

## 记录方式

每条查询记录 query_id、elapsed_ms、status、note，同时汇总总耗时、平均耗时、失败查询数和系统侧 CPU、内存、磁盘 IO。

## 常见问题

tpch-obs 未安装时，`scripts/run_tpch_test.sh` 会生成 22 条 `status=dry_run` 查询记录，说明流程可运行但没有真实查询耗时。
