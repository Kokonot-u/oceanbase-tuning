# OceanBase 智能参数调优项目

本项目面向 OceanBase 数据库性能诊断与智能调优场景，围绕参数采集、基准测试、参数影响分析、智能调参、容量预测和自动化验证，构建一套可复现的实验与原型系统。

项目当前以课程/阶段性研发交付为主，重点不是替代 OceanBase 官方调优工具，而是在官方参数体系和最佳实践基础上，探索机器学习与强化学习方法在数据库参数调优中的落地方式。

## 项目目标

- 建立 OceanBase 参数、工作负载、性能指标之间的实验数据链路。
- 基于真实参数表和 baseline 结果，筛选关键性能参数。
- 设计参数影响因子分析方法，为后续调优和验证提供候选集合。
- 设计智能调优策略，将连续型、枚举型、布尔型参数统一到可执行动作空间。
- 构建容量预测与自动化验证模块，形成参数推荐后的评估闭环。

## 模块划分

| 模块 | 方向 | 主要职责 | 典型产出 |
|---|---|---|---|
| A 组 | 基础环境与数据支持 | OceanBase 环境、数据采集、实验支撑 | 部署脚本、连接验证、基础数据 |
| B1 | 参数影响因子分析 | 参数筛选、特征工程、重要性排序 | 参数候选集、TopK 参数、影响因子报告 |
| B2 | 智能参数调优 | 强化学习建模、动作空间、奖励函数、推荐策略 | 动作空间接口、离线调优建议 |
| B3 | 容量预测 | 资源趋势分析、容量预测建模 | 容量预测结果、趋势图、预测报告 |
| B4 | 自动化验证 | 参数变更验证、benchmark 执行、回滚校验 | 验证报告、实验记录、对比结果 |

## 当前目录

```text
.
├── b1_b2/          # B1/B2 模块聚合入口
├── b3_b4/          # B3/B4 模块聚合入口
├── config/         # 数据库连接配置示例
├── docker/         # OceanBase 本地 Docker 部署和管理脚本
├── docs/           # 项目过程文档、实验报告、接口文档
├── logs/           # 真实实验原始运行日志
├── outputs/        # 实验结果和脚本默认读写目录
├── scripts/        # 参数导出、benchmark、结果构建脚本
├── sql/            # OceanBase 参数导出与指标采集 SQL
├── src/            # 各模块源码
├── tests/          # 自动化测试
└── tools/          # BenchmarkSQL 等外部工具
```

说明：

- `b1_b2/` 是 B1/B2 的模块化入口，集中保存对应代码、文档、接口和精选结果。
- `b3_b4/` 是 B3/B4 的模块化入口，集中保存对应代码、文档、接口和精选结果。
- `outputs/` 是全项目实验结果目录，部分脚本会直接读写该目录，不建议随意移动。
- `logs/` 保存真实实验原始日志，用于结果追溯。



## 快速开始

安装依赖：

```bash
pip install -r requirements.txt
```

验证 OceanBase 连接：

```bash
python docker/scripts/verify_connection.py
```

运行 Week4 B1/B2 结果构建：s

```bash
python scripts/real_week4/build_b1_b2_week4_outputs.py
```

运行测试：

```bash
python -m pytest tests/test_week4_b1_b2.py -q
```

## OceanBase 本地环境

本项目提供 Docker 脚本用于本地 OceanBase 单节点实验环境：

```bash
cd docker
docker compose up -d
docker exec -it ob-node bash
bash /scripts/install_ob.sh
```

连接验证：

```bash
python docker/scripts/verify_connection.py
```

详细部署过程见：

```text
docker/README.md
docs/benchmarksql_setup_guide.md
```

## 当前边界

- 当前实验以小规模 baseline 和离线分析为主，尚未形成大规模参数搜索数据集。
- B2 调优结果目前是离线推荐，真实执行前需要 B4 自动化验证、人工审批和 rollback 校验。
- TPC-H 当前使用脚本生成数据，正式对比实验建议切换到官方 `dbgen`。
- `outputs/` 与 `logs/` 保留为实验可追溯材料，不建议直接删除。

## 后续计划

- 接入更标准的 TPC-H `dbgen` 数据生成流程。
- 扩展参数变更实验，积累真实参数-性能样本。
- 对齐 B1/B2/B3/B4 接口，形成推荐、预测、验证的闭环。
- 将离线推荐逐步接入受控实验环境，验证收益和风险。
