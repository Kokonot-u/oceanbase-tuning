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
