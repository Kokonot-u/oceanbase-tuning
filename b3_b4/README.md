# B3 / B4 模块（Huang，B 组）

OceanBase 智能运维项目 B 组 **B3 资源容量预测** 与 **B4 参数调优效果自动化验证**。
对齐《B1/B2 接口定义文档 v0.1》与《第一次跨组联调测试计划 v1.0》。

## 目录结构

```
b3_b4/
├── config.json                 # 统一配置（输入路径 / 预测窗口 / 阈值等）
├── requirements.txt
├── run_all.py                  # 一键跑 B3 + B4
├── inputs/                     # 上游输入（已随包附带）
│   ├── normal_features_tpcc_10w_sample.csv        # A1(Wu) 预处理归一化时序
│   ├── b2_tuning_recommendations_real_week4.csv   # B2(Wang) 调优建议
│   └── baseline_perf/                             # B(Wang) 真实 baseline 性能
├── b3_forecast/                # B3：PatchTST-Lite 容量预测
│   ├── patchtst_lite.py        #   patching + RevIN(可选) + Ridge 线性头，通道独立
│   └── run_b3.py
├── b4_validation/              # B4：调优效果自动化验证框架
│   ├── benchmark_cases.py      #   模块一：基准测试用例封装（TPC-C/TPC-H，sim/real）
│   ├── metrics_collector.py    #   模块二：性能指标自动采集与对比
│   ├── validator.py            #   模块三：测试调度 + 前后对比报告生成
│   └── run_b4.py
└── outputs/                    # 运行后生成
    ├── capacity_forecast_real_week4.csv    # B3 输出（联调计划 §7.2 标准格式）
    ├── b3_backtest_metrics.csv             # B3 RMSE/MAE 基线指标
    ├── b3_forecast_report.md
    ├── validation_report_real_week4.md     # B4 输出（联调计划 §7.1）
    ├── b4_validation_results_real_week4.csv
    └── figures/*.png
```

## 依赖

Python 3.10+，仅需 `pandas / numpy / scikit-learn / matplotlib`（无需 GPU / PyTorch）。

```
pip install -r requirements.txt
```

## 运行

```
cd b3_b4
python run_all.py                 # 一键跑 B3 + B4
python -m b3_forecast.run_b3      # 只跑 B3
python -m b4_validation.run_b4    # 只跑 B4
```

## 数据链路

- B3 ← A1(Wu) `normal_features_*.csv` → 输出 `capacity_forecast_*.csv`
- B4 ← B2(Wang) `b2_tuning_recommendations_*.csv` + 真实 baseline → 输出 `validation_report_*.md`
- `requires_approval=1` 的高风险策略不自动执行，转人工审核（联调用例 JT-04）。
- B4 目前用 `simulation` 模式跑通链路；接真实独立测试租户时切到 `real`（见
  `benchmark_cases.py` 的 `_run_real` 钩子）。

## 关于 B3 模型

任务要求基于 PatchTST 思路做多步预测。本实现为 **PatchTST-Lite**：保留 PatchTST 的
「通道独立 + patching + 实例归一化」核心直觉，用 numpy/sklearn 的线性头实现，
可在无 torch 环境直接运行；接完整 24h/7d 历史后同一套接口即可替换为 torch 版
PatchTST，输出格式不变。
