"""
BenchmarkSQL运行器

调用BenchmarkSQL跑TPC-C/TPC-H基准测试，用于评估OceanBase性能。
"""

from typing import Optional, Dict, List, Literal
import subprocess
import json
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from loguru import logger
import xml.etree.ElementTree as ET


@dataclass
class BenchmarkConfig:
    """基准测试配置"""
    benchmark_type: Literal["tpcc", "tpch"] = "tpcc"
    benchmarksql_path: str = "/opt/benchmarksql"
    config_file: str = "config/tpcc.props"
    warehouses: int = 10
    terminals: int = 10
    run_time: int = 300  # 秒
    rampup_time: int = 30  # 秒
    scale_factor: float = 1.0  # for TPCH

@dataclass
class BenchmarkResult:
    """基准测试结果"""
    benchmark_type: str
    tpmc: Optional[float] = None
    tpmc_throughput: Optional[float] = None
    tpmc_rt_avg: Optional[float] = None
    tpmc_rt_95th: Optional[float] = None
    tpmc_rt_99th: Optional[float] = None
    error_rate: Optional[float] = None
    transactions: Optional[int] = None
    runtime: Optional[float] = None
    raw_data: Optional[Dict] = None
    error: Optional[str] = None


class BenchmarkRunner:
    """BenchmarkSQL运行器"""

    def __init__(self, config: Optional[BenchmarkConfig] = None):
        """
        初始化运行器

        Args:
            config: 基准测试配置
        """
        self.config = config or BenchmarkConfig()
        self.benchmarksql_path = Path(self.config.benchmarksql_path)

    def generate_config(self, db_host: str, db_port: int, db_user: str,
                       db_password: str, db_name: str) -> Path:
        """
        生成BenchmarkSQL配置文件

        Args:
            db_host: 数据库主机
            db_port: 数据库端口
            db_user: 数据库用户
            db_password: 数据库密码
            db_name: 数据库名

        Returns:
            配置文件路径
        """
        if self.config.benchmark_type == "tpcc":
            content = f"""db={db_host}
driver=com.mysql.jdbc.Driver
conn=jdbc:mysql://{db_host}:{db_port}/{db_name}?useSSL=false
user={db_user}
password={db_password}

warehouses={self.config.warehouses}
loadWorkers=10
terminals={self.config.terminals}
runMins={self.config.run_time / 60}
runTxnsPerTerminal=0
limitTxnsPerTerminal=0
terminalWarehouseFixed=true

//To run specified transactions per terminal- runMins must equal zero
//runTxnsPerTerminal=10

//To run specified transactions total
//runTxns={self.config.run_time * 10}

number of A nodes per warehouse = 10
number of C nodes per warehouse = 10
number of D nodes per warehouse = 10
number of M nodes per warehouse = 10
number of W nodes per warehouse = 10

resultDirectory=/tmp/benchmarksql/results

osCollectorScripts=./scripts/collector.dist
"""
        else:  # TPC-H
            content = f"""db={db_host}
driver=com.mysql.jdbc.Driver
conn=jdbc:mysql://{db_host}:{db_port}/{db_name}?useSSL=false
user={db_user}
password={db_password}

scaleFactor={self.config.scale_factor}
queryStreams={self.config.terminals}
dataDirectory=./data

osCollectorScripts=./scripts/collector.dist
"""

        config_path = self.benchmarksql_path / self.config.config_file
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w') as f:
            f.write(content)

        logger.info(f"Generated config file: {config_path}")
        return config_path

    def run_benchmark(self, db_host: str, db_port: int, db_user: str,
                     db_password: str, db_name: str) -> BenchmarkResult:
        """
        运行基准测试

        Args:
            db_host: 数据库主机
            db_port: 数据库端口
            db_user: 数据库用户
            db_password: 数据库密码
            db_name: 数据库名

        Returns:
            基准测试结果
        """
        config_path = self.generate_config(db_host, db_port, db_user, db_password, db_name)

        try:
            if self.config.benchmark_type == "tpcc":
                return self._run_tpcc(config_path)
            else:
                return self._run_tpch(config_path)
        except Exception as e:
            logger.error(f"Benchmark run failed: {e}")
            return BenchmarkResult(
                benchmark_type=self.config.benchmark_type,
                error=str(e)
            )

    def _run_tpcc(self, config_path: Path) -> BenchmarkResult:
        """运行TPC-C测试"""
        # 运行BenchmarkSQL
        cmd = f"cd {self.benchmarksql_path} && ./runBenchmark.sh {config_path}"

        logger.info(f"Running TPC-C benchmark: {cmd}")
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.config.run_time + 300  # 额外超时时间
        )

        # 解析结果
        return self._parse_tpcc_result(result.stdout, result.stderr)

    def _run_tpch(self, config_path: Path) -> BenchmarkResult:
        """运行TPC-H测试"""
        # TPC-H通常分两步：生成数据 + 运行查询
        logger.info("Running TPC-H benchmark")

        # 生成数据
        generate_cmd = f"cd {self.benchmarksql_path} && ./runDataGen.sh {config_path}"
        subprocess.run(generate_cmd, shell=True, timeout=3600)

        # 运行查询
        run_cmd = f"cd {self.benchmarksql_path} && ./runQuery.sh {config_path}"
        result = subprocess.run(
            run_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.config.run_time + 300
        )

        return self._parse_tpch_result(result.stdout, result.stderr)

    def _parse_tpcc_result(self, stdout: str, stderr: str) -> BenchmarkResult:
        """解析TPC-C结果"""
        try:
            # TPC-C结果通常输出到stdout，格式如下：
            # "Measured tpmC (NewOrders): xxxx"
            # "Measured tpmC throughput: xxxx"

            result = BenchmarkResult(benchmark_type="tpcc")

            # 提取TPMC
            for line in stdout.split('\n'):
                if "Measured tpmC (NewOrders)" in line:
                    result.tpmc = float(line.split(':')[-1].strip())
                elif "Measured tpmC throughput" in line:
                    result.tpmc_throughput = float(line.split(':')[-1].strip())
                elif "Average Response Time" in line:
                    result.tpmc_rt_avg = float(line.split(':')[-1].strip().split()[0])
                elif "95th Percentile" in line:
                    result.tpmc_rt_95th = float(line.split(':')[-1].strip().split()[0])
                elif "99th Percentile" in line:
                    result.tpmc_rt_99th = float(line.split(':')[-1].strip().split()[0])
                elif "Error rate" in line:
                    result.error_rate = float(line.split(':')[-1].strip().replace('%', ''))

            result.raw_data = {"stdout": stdout, "stderr": stderr}

            logger.info(f"TPC-C Result: TPMC={result.tpmc}, Throughput={result.tpmc_throughput}")
            return result

        except Exception as e:
            logger.error(f"Failed to parse TPC-C result: {e}")
            return BenchmarkResult(
                benchmark_type="tpcc",
                error=f"Parse error: {e}",
                raw_data={"stdout": stdout, "stderr": stderr}
            )

    def _parse_tpch_result(self, stdout: str, stderr: str) -> BenchmarkResult:
        """解析TPC-H结果"""
        try:
            result = BenchmarkResult(benchmark_type="tpch")

            # TPC-H通常返回每个查询的执行时间
            query_times = {}
            for line in stdout.split('\n'):
                if 'Query Q' in line and 'time' in line.lower():
                    parts = line.split()
                    query_name = parts[1]
                    time_value = float(parts[-1])
                    query_times[query_name] = time_value

            result.raw_data = query_times
            result.transactions = len(query_times)

            logger.info(f"TPC-H Result: {len(query_times)} queries completed")
            return result

        except Exception as e:
            logger.error(f"Failed to parse TPC-H result: {e}")
            return BenchmarkResult(
                benchmark_type="tpch",
                error=f"Parse error: {e}",
                raw_data={"stdout": stdout, "stderr": stderr}
            )

    def parse_xml_result(self, xml_path: Path) -> BenchmarkResult:
        """
        解析XML格式的基准测试结果

        Args:
            xml_path: XML结果文件路径

        Returns:
            基准测试结果
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            result = BenchmarkResult(benchmark_type=self.config.benchmark_type)

            # 解析性能指标
            for metric in root.findall('.//metric'):
                name = metric.get('name')
                value = float(metric.get('value'))

                if name == 'tpmc':
                    result.tpmc = value
                elif name == 'throughput':
                    result.tpmc_throughput = value
                elif name == 'response_time_avg':
                    result.tpmc_rt_avg = value
                elif name == 'response_time_95th':
                    result.tpmc_rt_95th = value
                elif name == 'response_time_99th':
                    result.tpmc_rt_99th = value
                elif name == 'error_rate':
                    result.error_rate = value
                elif name == 'transactions':
                    result.transactions = int(value)
                elif name == 'runtime':
                    result.runtime = value

            return result

        except Exception as e:
            logger.error(f"Failed to parse XML result: {e}")
            return BenchmarkResult(
                benchmark_type=self.config.benchmark_type,
                error=f"XML parse error: {e}"
            )

    def compare_results(self, baseline: BenchmarkResult,
                        current: BenchmarkResult) -> Dict[str, float]:
        """
        比较两次基准测试结果

        Args:
            baseline: 基准结果
            current: 当前结果

        Returns:
            性能变化百分比
        """
        if baseline.benchmark_type != current.benchmark_type:
            raise ValueError("Cannot compare different benchmark types")

        changes = {}

        if baseline.tpmc and current.tpmc:
            changes['tpmc_change'] = (current.tpmc - baseline.tpmc) / baseline.tpmc * 100

        if baseline.tpmc_throughput and current.tpmc_throughput:
            changes['throughput_change'] = (current.tpmc_throughput - baseline.tpmc_throughput) / baseline.tpmc_throughput * 100

        if baseline.tpmc_rt_avg and current.tpmc_rt_avg:
            changes['avg_rt_change'] = (current.tpmc_rt_avg - baseline.tpmc_rt_avg) / baseline.tpmc_rt_avg * 100

        if baseline.tpmc_rt_95th and current.tpmc_rt_95th:
            changes['95th_rt_change'] = (current.tpmc_rt_95th - baseline.tpmc_rt_95th) / baseline.tpmc_rt_95th * 100

        return changes

    def export_to_dataframe(self, results: List[BenchmarkResult]) -> pd.DataFrame:
        """
        将多个基准测试结果导出为DataFrame

        Args:
            results: 基准测试结果列表

        Returns:
            结果DataFrame
        """
        data = []
        for i, result in enumerate(results):
            row = {
                'run_id': i,
                'benchmark_type': result.benchmark_type,
                'tpmc': result.tpmc,
                'throughput': result.tpmc_throughput,
                'avg_response_time': result.tpmc_rt_avg,
                '95th_response_time': result.tpmc_rt_95th,
                '99th_response_time': result.tpmc_rt_99th,
                'error_rate': result.error_rate,
                'transactions': result.transactions,
                'runtime': result.runtime,
                'error': result.error
            }
            data.append(row)

        return pd.DataFrame(data)

    def save_results(self, results: List[BenchmarkResult], output_path: Path) -> None:
        """
        保存基准测试结果

        Args:
            results: 结果列表
            output_path: 输出路径
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix == '.json':
            with open(output_path, 'w') as f:
                json.dump([r.__dict__ for r in results], f, indent=2)
        elif output_path.suffix == '.csv':
            df = self.export_to_dataframe(results)
            df.to_csv(output_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {output_path.suffix}")

        logger.info(f"Saved results to {output_path}")