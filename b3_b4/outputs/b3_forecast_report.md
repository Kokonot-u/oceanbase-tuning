# B3 资源容量预测 基线效果报告

- experiment_id: `real_week4`
- 模型: PatchTST-Lite (`patchtst-lite-v0.1`) —— patching + RevIN + Ridge 线性头，通道独立
- 输入数据: `inputs/normal_features_tpcc_10w_sample.csv`（A1/Wu 预处理后的归一化时序，240 行）
- 采样粒度: 60 秒；输入窗口 L=48；训练预测步长 H=24
- 预测范围: 短期 24 小时、长期 7 天（多步递归预测）

## 1. 基线预测指标 (walk-forward 回测)

| 指标 metric | RMSE | MAE | 残差std | 训练样本 |
| -- | -- | -- | -- | -- |
| cpu_usage | 2.7373 | 2.2120 | 2.7319 | 169 |
| memory_usage | 1.3465 | 1.0896 | 1.3508 | 169 |
| io_wait | 1.3264 | 1.0816 | 1.3265 | 169 |
| qps | 1.3088 | 1.0273 | 1.3149 | 169 |
| latency_ms | 3.2857 | 2.5676 | 3.9486 | 169 |

> 说明：输入为 Wu 已做 z-score 标准化的特征，故 RMSE/MAE 为标准化尺度下的误差。

## 2. 输出接口

`capacity_forecast_real_week4.csv` 遵循《第一次跨组联调测试计划 §7.2》字段：
`experiment_id, forecast_timestamp, metric_name, forecast_value, confidence_lower, confidence_upper, horizon_type, model_version`。
`horizon_type` 取值 `short_term`（未来 24 小时，按 60 秒逐点）与 `long_term`（未来 7 天，按 3600 秒下采样）。

## 3. 与上下游对接

- 上游 A1(Wu): 直接消费其预处理归一化 CSV，无需再清洗。
- 下游: 预测结果供容量规划与 B4 验证后复盘使用。
- 说明：本 sample 数据量较小，仅用于跑通链路与产出基线指标；接入完整 24h/7d 历史后同一套代码即可给出生产级预测。

## 4. 复现

```
python -m b3_forecast.run_b3
```
