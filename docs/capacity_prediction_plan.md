# 容量预测实验方案

## 背景与目标

基于参数测试和系统指标采集结果，构建未来 7 天资源容量趋势预测能力，时间粒度为 1 小时级。

## 输入特征

CPU 使用率、内存使用率、磁盘 IO、QPS、平均延迟、活跃会话数和错误数。

## 标签设计

future_cpu_usage、future_memory_usage、future_disk_io。

## 评价指标

MAE、RMSE、MAPE。

## 数据来源

Prometheus、docker stats、GV$SYSSTAT、GV$OB_SQL_AUDIT、参数测试结果。

## 基线模型

moving average、last value、linear regression。当前脚本 `scripts/capacity_forecast_baseline.py` 已实现 docker metrics 的 moving average 模板。

## 后续模型

XGBoost、LSTM、Temporal Fusion Transformer。

## 当前限制

单节点本机数据量少，负载波动不稳定，不适合直接证明生产容量预测效果。后续接入 A 组 24 小时正常负载数据集后，可按小时聚合，补齐活跃会话、错误数和业务 QPS 特征。
