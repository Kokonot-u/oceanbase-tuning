# OceanBase数据库性能智能诊断与优化项目

## 项目简介

本项目旨在通过机器学习和强化学习技术，为OceanBase社区版数据库提供智能化的性能诊断、参数调优和容量规划服务。

## 模块说明

### B组模块划分

#### B1 - 性能分析模块 (src/b1_analysis/)
- **param_loader.py**: 加载100个关键参数定义和默认值
- **benchmark_runner.py**: 调用BenchmarkSQL跑TPC-C/TPC-H基准测试
- **feature_selector.py**: 使用Scikit-learn/XGBoost进行特征选择

#### B2 - 智能调优模块 (src/b2_tuning/)
- **env.py**: Gymnasium环境封装OceanBase参数调优过程
- **agent.py**: 基于Stable-Baselines3的离线强化学习Agent
- **llm_advisor.py**: 利用大模型生成自然语言调优建议

#### B3 - 容量规划模块 (src/b3_capacity/)
- **data_simulator.py**: 生成模拟历史资源数据（CPU/内存/IO/网络）
- **patchtst_model.py**: PatchTST时序预测模型实现
- **report_generator.py**: 生成容量规划报告（Matplotlib/Seaborn可视化）

#### B4 - 验证模块 (src/b4_validation/)
- **auto_benchmark.py**: 自动化基准测试脚本
- **param_applier.py**: 自动应用参数配置到OceanBase
- **experiment_tracker.py**: MLflow实验记录与对比分析

### 数据采集模块 (src/collector/)
- **ob_collector.py**: 从OceanBase系统表采集性能数据

### 工具模块 (src/utils/)
- **db_conn.py**: OceanBase连接工具，支持PyMySQL

## 环境要求

- Python 3.10+
- OceanBase 社区版（MySQL模式租户）
- MLflow 用于实验管理
- Docker (用于本地OceanBase部署)

## 快速开始

### 方式一：Docker部署OceanBase（推荐用于测试）

在macOS（Apple M4）上使用Docker快速部署OceanBase单节点集群：

```bash
# 1. 启动OceanBase容器
cd docker && docker-compose up -d

# 2. 进入容器内部署OceanBase
docker exec -it ob-node bash
bash /scripts/install_ob.sh
exit

# 3. 验证部署
python docker/scripts/verify_connection.py

# 4. 配置数据库连接（验证通过后）
cp config/db_config.yaml.example config/db_config.yaml
# 编辑 config/db_config.yaml 填入连接信息
```

**快捷操作脚本**：
```bash
chmod +x docker/scripts/ob_manager.sh
./docker/scripts/ob_manager.sh start    # 启动
./docker/scripts/ob_manager.sh status   # 查看状态
./docker/scripts/ob_manager.sh connect  # 连接数据库
./docker/scripts/ob_manager.sh logs     # 查看日志
./docker/scripts/ob_manager.sh stop     # 停止
```

详细部署说明请参考 [docker/README.md](docker/README.md)

### 方式二：手动安装Python环境

```bash
# 克隆项目
git clone <your-repo-url> oceanbase-tuning
cd oceanbase-tuning

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置数据库连接
cp config/db_config.yaml.example config/db_config.yaml
# 编辑 config/db_config.yaml 填入你的OceanBase连接信息
```

## 快速开始

### 1. 配置数据库连接

编辑 `config/db_config.yaml`，填入你的OceanBase连接信息：

```yaml
host: "127.0.0.1"
port: 2881
user: "root@sys"
password: "your_password"
database: "oceanbase"
charset: utf8mb4
```

### 2. 测试数据库连接

```bash
pytest tests/test_db_conn.py -v
```

### 3. 运行数据采集

```python
from src.collector.ob_collector import OBCollector
from src.utils.db_conn import DBConnector

with DBConnector() as db:
    collector = OBCollector(db)
    metrics = collector.collect_performance_metrics()
    metrics.to_csv('data/raw/metrics.csv', index=False)
```

### 4. 运行参数调优

```python
from src.b2_tuning.env import OceanBaseTuningEnv
from src.b2_tuning.agent import RLAgent

env = OceanBaseTuningEnv()
agent = RLAgent(env)
agent.train(total_timesteps=100000)
```

### 5. 启动MLflow UI

```bash
mlflow ui --backend-store-uri ./experiments/mlflow
```

访问 http://localhost:5000 查看实验记录。

## 目录结构

```
oceanbase-tuning/
├── README.md                      # 项目说明文档
├── requirements.txt               # Python依赖
├── .gitignore                     # Git忽略配置
├── config/
│   └── db_config.yaml            # 数据库配置
├── data/
│   ├── raw/                      # 原始数据
│   ├── processed/                # 处理后数据
│   ├── benchmark/                # 基准测试结果
│   └── simulated/                # B3模拟历史数据
├── src/
│   ├── collector/                # 数据采集模块
│   ├── b1_analysis/              # B1性能分析
│   ├── b2_tuning/                # B2智能调优
│   ├── b3_capacity/              # B3容量规划
│   ├── b4_validation/            # B4验证模块
│   └── utils/                    # 工具模块
├── experiments/
│   └── mlflow/                   # MLflow实验数据
├── tests/                        # 单元测试
└── notebooks/                    # Jupyter探索性分析
```

## 技术栈

- **数据库连接**: PyMySQL
- **数据处理**: Pandas, Polars, NumPy
- **机器学习**: Scikit-learn, XGBoost, LightGBM
- **深度学习**: PyTorch, Stable-Baselines3
- **强化学习**: Gymnasium
- **时序预测**: Darts, NeuralForecast
- **LLM集成**: Transformers, LangChain
- **可视化**: Matplotlib, Seaborn, Plotly
- **实验管理**: MLflow
- **日志**: Loguru
- **测试**: Pytest
- **Web界面**: Streamlit

## 开发规范

- 使用类型注解
- 遵循PEP 8代码风格
- 编写单元测试
- 使用Loguru进行日志记录
- 使用MLflow追踪实验

## 许可证

MIT License

## 联系方式

如有问题，请提交Issue或联系项目维护者。

## 第二周 B 组参数影响测试交付

当前阶段聚焦 OceanBase 参数影响测试：基于第一周导出的关键参数表，筛选候选参数，选择 5 个核心参数，生成 TPC-C/TPC-H 实验矩阵，采集系统指标，并构建参数配置-性能指标数据集。

### 环境要求

- Python 3.10+
- Docker
- OceanBase Docker 单节点，默认容器名 `obstandalone`
- 可选：BenchmarkSQL、tpch-obs、obclient

### 快速开始

```bash
pip install -r requirements.txt

python3 scripts/select_param_candidates.py
python3 scripts/choose_top5_params.py
python3 scripts/generate_test_matrix.py

bash scripts/collect_metrics.sh
bash scripts/run_param_experiment.sh 1

python3 scripts/summarize_results.py
python3 scripts/plot_param_results.py
python3 scripts/capacity_forecast_baseline.py
```

### 参数候选筛选

`scripts/select_param_candidates.py` 读取 `outputs/ob_parameters.tsv`，自动识别字段大小写，根据 CPU 调度、内存管理、磁盘 IO、SQL 执行四类关键词生成 `outputs/param_candidates.csv`。

### 选择 5 个参数

`scripts/choose_top5_params.py` 读取候选参数，按类别覆盖、score、edit_level 和风险等级生成：

- `outputs/selected_5_params.csv`
- `configs/selected_5_params.yaml`
- `docs/selected_params_explanation.md`

梯度是保守占位，真实修改前必须人工确认官方默认值、范围和是否需要重启。

### 生成测试矩阵

`scripts/generate_test_matrix.py` 将 5 个参数的梯度展开到 TPC-C 和 TPC-H 两类 workload，输出：

- `outputs/param_test_matrix.csv`
- `configs/param_test_matrix.yaml`

### 执行 dry-run 参数实验

`scripts/run_param_experiment.sh` 支持按 `experiment_id` 执行。默认不自动修改 OceanBase 参数，不执行 `ALTER SYSTEM SET`。BenchmarkSQL 或 tpch-obs 缺失时会生成 `status=dry_run` 的 CSV，用于验证流程，不代表真实性能。

### 汇总结果与图表

`scripts/summarize_results.py` 合并 `outputs/tpcc_result_*.csv` 和 `outputs/tpch_result_*.csv`，生成：

- `outputs/param_perf_dataset.csv`
- `outputs/param_perf_summary.csv`

`scripts/plot_param_results.py` 在存在真实数值指标时输出趋势图到 `outputs/figures/`。

### 容量预测基线

`scripts/capacity_forecast_baseline.py` 读取 `outputs/metrics_log.csv`，在数据足够时生成 moving average 基线预测；数据不足时生成模板并说明需要更多时间点。

### 文档位置

- `docs/week2_plan.md`
- `docs/benchmarksql_setup_guide.md`
- `docs/tpch_setup_guide.md`
- `docs/param_experiment_method.md`
- `docs/capacity_prediction_plan.md`
- `docs/automation_validation_framework.md`
- `docs/first_round_param_test_report.md`
- `docs/week2_delivery_summary.md`
- `docs/troubleshooting.md`

### 第二周交付物清单

已补齐 SQL、configs、outputs、scripts 和 docs 的标准结构。当前真实数据包括第一周参数表及基于参数表生成的候选/Top5/实验矩阵；BenchmarkSQL/TPC-H 在工具未安装时只输出 dry-run 结果。
