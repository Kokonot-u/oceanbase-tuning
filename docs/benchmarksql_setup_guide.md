# BenchmarkSQL / TPC-C 设置指南

BenchmarkSQL 用于执行 TPC-C 风格 OLTP 基准测试，可观察订单、新订单、支付等事务在不同参数配置下的吞吐和延迟变化。

## OceanBase MySQL 模式连接

参考 `configs/tpcc_config.example.properties`：

```properties
db=oceanbase
driver=com.mysql.cj.jdbc.Driver
conn=jdbc:mysql://127.0.0.1:2881/tpcc
user=root@sys
password=
warehouses=5
loadWorkers=4
terminals=4
runMins=5
```

## 本机轻量建议

Mac Docker 单节点建议从 warehouses 1、5、10 开始，runMins 3-10，terminals 1-4。标准任务中的 100 warehouse 更适合资源更充足的环境，不建议在本机单节点直接长时间运行。

## 结果记录

保存 QPS、平均延迟、P95、P99、错误数、开始时间、结束时间和参数配置。脚本统一输出 `outputs/tpcc_result_${experiment_id}.csv`。

## 常见问题

BenchmarkSQL 未安装时，`scripts/run_tpcc_test.sh` 会生成 `status=dry_run` 的示例结果，并在 `docs/troubleshooting.md` 记录原因。dry-run 只验证流程，不代表真实性能。
