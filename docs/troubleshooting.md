# Troubleshooting

## OceanBase 容器未启动

- 现象：`collect_metrics.sh` 提示 `container obstandalone does not exist or is not running`。
- 可能原因：Docker 未启动、容器名不是 obstandalone、compose 尚未启动。
- 检查命令：`docker ps --format '{{.Names}}'`
- 修复命令：`bash scripts/start_ob.sh`
- 是否影响交付：影响真实指标采集，不影响 dry-run 流程。

## 2881 端口不通

- 现象：obclient/mysql 连接失败。
- 可能原因：observer 未启动、端口映射不同、租户未初始化。
- 检查命令：`nc -vz 127.0.0.1 2881`
- 修复命令：检查 `docker/README.md` 并重新执行部署步骤。
- 是否影响交付：影响真实 SQL 和 benchmark。

## obclient 不存在

- 现象：`connect_ob.sh` 找不到 obclient。
- 可能原因：本机未安装 OceanBase 客户端。
- 检查命令：`command -v obclient`
- 修复命令：安装 obclient，或使用 mysql 客户端连接 MySQL 模式租户。
- 是否影响交付：影响手工执行 SQL，不影响 CSV 生成。

## BenchmarkSQL 未安装

- 现象：`run_tpcc_test.sh` 输出 `status=dry_run`。
- 可能原因：`BENCHMARKSQL_HOME` 未配置或工具目录不存在。
- 检查命令：`ls "$BENCHMARKSQL_HOME"`
- 修复命令：下载 BenchmarkSQL，配置 JDBC driver 和 `configs/tpcc_config.example.properties`。
- 是否影响交付：影响真实 TPC-C 结果，dry-run 已明确标注。

## tpch-obs 未安装

- 现象：`run_tpch_test.sh` 输出 22 条 `status=dry_run`。
- 可能原因：`TPCH_HOME` 未配置或工具目录不存在。
- 检查命令：`ls "$TPCH_HOME"`
- 修复命令：准备 OceanBase 适配版 tpch-obs 并设置 `TPCH_HOME`。
- 是否影响交付：影响真实 TPC-H 结果，dry-run 已明确标注。

## 参数表不存在

- 现象：候选筛选输出空模板。
- 可能原因：缺少 `outputs/ob_parameters.tsv` 和 `output/ob_parameters.tsv`。
- 检查命令：`find . -iname '*parameter*' -o -iname '*param*' -o -iname '*.tsv' -o -iname '*.csv'`
- 修复命令：运行 `bash scripts/export_params.sh` 或恢复第一周导出文件。
- 是否影响交付：影响候选参数真实性。

## CSV 字段不匹配

- 现象：Python 脚本提示缺少字段。
- 可能原因：参数表不是 NAME/VALUE/INFO/SECTION/EDIT_LEVEL 格式。
- 检查命令：`head -1 outputs/ob_parameters.tsv`
- 修复命令：调整导出 SQL 或字段映射。
- 是否影响交付：影响自动筛选。

## 权限不足

- 现象：脚本无法写入 outputs/docs。
- 可能原因：目录权限异常。
- 检查命令：`ls -ld outputs docs`
- 修复命令：`chmod u+w outputs docs`
- 是否影响交付：影响文件生成。

## 本机资源不足

- 现象：Benchmark 运行慢、容器退出、内存不足。
- 可能原因：warehouse 或 TPC-H scale 过大。
- 检查命令：`docker stats obstandalone --no-stream`
- 修复命令：TPC-C 从 warehouses=1/5/10 开始，TPC-H 从 100MB/1GB 开始。
- 是否影响交付：影响真实长测，不影响流程交付。

## SQL 执行失败

- 现象：系统视图查询失败。
- 可能原因：租户权限不足、OceanBase 版本视图名差异、未连接 sys 租户。
- 检查命令：`SELECT VERSION();`
- 修复命令：确认用户、租户和版本，必要时调整 SQL。
- 是否影响交付：影响真实系统指标采集。

- BenchmarkSQL 未安装，实验 1 已生成 dry-run 结果：outputs/tpcc_result_1.csv

- BenchmarkSQL 未安装，实验 1 已生成 dry-run 结果：outputs/tpcc_result_1.csv

- tpch-obs 未安装，实验 2 已生成 dry-run 结果：outputs/tpch_result_2.csv
