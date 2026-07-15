# Week 2 Deliverables

第二周产出按组整理，方便导师在 GitHub 上查看。

## A 组

- 目录：`A_group/`
- 当前状态：已预留目录，等待 A 组同学补充第二周产出。

## B 组

- 目录：`B_group/`
- 内容：OceanBase 真实实验链路、参数导出、Top100/Top5 参数筛选，以及 TPC-C/TPC-H/轻量 SQL baseline。

## B 组 Baseline 摘要

| Workload | 吞吐 | 平均延迟 | P95 | P99 | 说明 |
| -- | --: | --: | --: | --: | -- |
| 轻量 SQL | 7.17 ops/s | 139.228 ms | 178.12 ms | 239.711 ms | 真实 SQL 链路验证 |
| TPC-C / BenchmarkSQL | 1.826 txn/s | 312.3 ms | 716.0 ms | 726.0 ms | 1 warehouse / 1 terminal / 20 transactions |
| TPC-H 22 查询 | 6.5269 q/s | 153.213 ms | 192.592 ms | 285.852 ms | 小规模确定性数据集，非官方 dbgen |
