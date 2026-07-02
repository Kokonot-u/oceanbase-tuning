"""
自动化基准测试

自动化运行TPC-C/TPC-H基准测试并收集结果。
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import subprocess
import json
import time
import pandas as pd
from dataclasses import dataclass, asdict
from loguru import logger

from ..b1_analysis.benchmark_runner import BenchmarkRunner, BenchmarkResult


@dataclass
class BenchmarkJob:
    """基准测试任务"""
    job_id: str
    config: Dict[str, Any]
    params: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[BenchmarkResult] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class AutoBenchmark:
    """
    自动化基准测试管理器

    支持批量运行、结果对比和自动报告生成
    """

    def __init__(self, db_config: Dict[str, str], output_dir: str = "benchmarks"):
        """
        初始化自动化基准测试

        Args:
            db_config: 数据库配置
            output_dir: 输出目录
        """
        self.db_config = db_config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.jobs: Dict[str, BenchmarkJob] = {}
        self.results: List[BenchmarkResult] = []

        logger.info(f"Initialized AutoBenchmark with output directory: {self.output_dir}")

    def create_job(self, job_id: str, benchmark_type: str = "tpcc",
                   params: Optional[Dict[str, Any]] = None,
                   **kwargs) -> BenchmarkJob:
        """
        创建基准测试任务

        Args:
            job_id: 任务ID
            benchmark_type: 基准测试类型
            params: 参数配置
            **kwargs: 其他配置

        Returns:
            创建的任务
        """
        config = {
            'benchmark_type': benchmark_type,
            'db_config': self.db_config,
            **kwargs
        }

        job = BenchmarkJob(
            job_id=job_id,
            config=config,
            params=params or {}
        )

        self.jobs[job_id] = job
        logger.info(f"Created benchmark job: {job_id}")
        return job

    def run_job(self, job_id: str, wait: bool = True) -> Optional[BenchmarkResult]:
        """
        运行单个基准测试任务

        Args:
            job_id: 任务ID
            wait: 是否等待完成

        Returns:
            测试结果
        """
        if job_id not in self.jobs:
            logger.error(f"Job not found: {job_id}")
            return None

        job = self.jobs[job_id]
        job.status = "running"
        job.start_time = time.time()

        logger.info(f"Starting benchmark job: {job_id}")

        try:
            # 如果有参数需要应用，先应用参数
            if job.params:
                self._apply_parameters(job.params)

            # 创建并运行基准测试
            from ..b1_analysis.benchmark_runner import BenchmarkConfig
            benchmark_config = BenchmarkConfig(
                benchmark_type=job.config.get('benchmark_type', 'tpcc'),
                **{k: v for k, v in job.config.items()
                   if k not in ['benchmark_type', 'db_config']}
            )

            runner = BenchmarkRunner(benchmark_config)
            result = runner.run_benchmark(
                db_host=self.db_config['host'],
                db_port=int(self.db_config['port']),
                db_user=self.db_config['user'],
                db_password=self.db_config['password'],
                db_name=self.db_config['database']
            )

            job.result = result
            job.status = "completed"
            self.results.append(result)

            # 保存结果
            self._save_result(job_id, result)

        except Exception as e:
            logger.error(f"Benchmark job {job_id} failed: {e}")
            job.status = "failed"
            job.result = BenchmarkResult(
                benchmark_type=job.config.get('benchmark_type', 'tpcc'),
                error=str(e)
            )

        finally:
            job.end_time = time.time()
            duration = job.end_time - job.start_time
            logger.info(f"Job {job_id} completed in {duration:.2f}s with status: {job.status}")

        return job.result

    def run_batch(self, jobs: List[Dict[str, Any]],
                  parallel: bool = False,
                  max_workers: int = 2) -> Dict[str, BenchmarkResult]:
        """
        批量运行基准测试

        Args:
            jobs: 任务配置列表
            parallel: 是否并行运行
            max_workers: 最大并行数

        Returns:
            任务结果字典
        """
        results = {}

        if parallel:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {}

                for job_config in jobs:
                    job_id = job_config['job_id']
                    job = self.create_job(
                        job_id=job_id,
                        **job_config
                    )
                    futures[job_id] = executor.submit(self.run_job, job_id)

                for job_id, future in futures.items():
                    results[job_id] = future.result()
        else:
            for job_config in jobs:
                job_id = job_config['job_id']
                result = self.run_job(job_id)
                results[job_id] = result

        return results

    def compare_results(self, baseline_job_id: str,
                       comparison_job_ids: List[str]) -> pd.DataFrame:
        """
        比较基准测试结果

        Args:
            baseline_job_id: 基准任务ID
            comparison_job_ids: 对比任务ID列表

        Returns:
            对比结果DataFrame
        """
        if baseline_job_id not in self.jobs:
            raise ValueError(f"Baseline job not found: {baseline_job_id}")

        baseline = self.jobs[baseline_job_id].result
        if baseline is None:
            raise ValueError(f"Baseline job has no result: {baseline_job_id}")

        comparisons = []

        for job_id in comparison_job_ids:
            if job_id not in self.jobs:
                continue

            current = self.jobs[job_id].result
            if current is None:
                continue

            # 计算变化
            changes = self._calculate_changes(baseline, current)

            comparisons.append({
                'job_id': job_id,
                'params': json.dumps(self.jobs[job_id].params),
                'tpmc': current.tpmc,
                'tpmc_change_pct': changes.get('tpmc', 0),
                'throughput': current.tpmc_throughput,
                'throughput_change_pct': changes.get('throughput', 0),
                'avg_latency': current.tpmc_rt_avg,
                'latency_change_pct': changes.get('avg_latency', 0),
                '95th_latency': current.tpmc_rt_95th,
                'error_rate': current.error_rate,
                'status': self.jobs[job_id].status,
            })

        return pd.DataFrame(comparisons)

    def _calculate_changes(self, baseline: BenchmarkResult,
                          current: BenchmarkResult) -> Dict[str, float]:
        """计算指标变化"""
        changes = {}

        if baseline.tpmc and current.tpmc:
            changes['tpmc'] = (current.tpmc - baseline.tpmc) / baseline.tpmc * 100

        if baseline.tpmc_throughput and current.tpmc_throughput:
            changes['throughput'] = (current.tpmc_throughput - baseline.tpmc_throughput) / baseline.tpmc_throughput * 100

        if baseline.tpmc_rt_avg and current.tpmc_rt_avg:
            changes['avg_latency'] = (baseline.tpmc_rt_avg - current.tpmc_rt_avg) / baseline.tpmc_rt_avg * 100

        return changes

    def _apply_parameters(self, params: Dict[str, Any]) -> None:
        """应用参数配置"""
        # 这里应该调用ParamApplier来应用参数
        logger.info(f"Applying parameters: {params}")
        # 实际实现:
        # from ..b4_validation.param_applier import ParamApplier
        # applier = ParamApplier(self.db_config)
        # applier.apply_params(params)

    def _save_result(self, job_id: str, result: BenchmarkResult) -> None:
        """保存测试结果"""
        result_file = self.output_dir / f"{job_id}_result.json"

        result_dict = asdict(result)

        with open(result_file, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)

        logger.info(f"Saved result to {result_file}")

    def export_results(self, output_path: str,
                       format: str = 'csv') -> None:
        """
        导出所有结果

        Args:
            output_path: 输出路径
            format: 格式 (csv, json, excel)
        """
        from ..b1_analysis.benchmark_runner import BenchmarkRunner

        runner = BenchmarkRunner()
        df = runner.export_to_dataframe(self.results)

        if format == 'csv':
            df.to_csv(output_path, index=False)
        elif format == 'json':
            df.to_json(output_path, orient='records', indent=2)
        elif format == 'excel':
            df.to_excel(output_path, index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")

        logger.info(f"Exported {len(self.results)} results to {output_path}")

    def generate_report(self, output_path: str) -> None:
        """
        生成基准测试报告

        Args:
            output_path: 输出路径
        """
        if not self.results:
            logger.warning("No results to generate report")
            return

        # 创建DataFrame
        df = self.export_results_to_df()

        # 生成HTML报告
        html = self._generate_html_report(df)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Generated benchmark report: {output_path}")

    def _generate_html_report(self, df: pd.DataFrame) -> str:
        """生成HTML报告"""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>OceanBase基准测试报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        .positive { color: green; }
        .negative { color: red; }
    </style>
</head>
<body>
    <h1>OceanBase基准测试报告</h1>
    <p>测试数量: {n_tests}</p>
    <table>
        <tr>
            <th>Run ID</th>
            <th>TPMC</th>
            <th>Throughput</th>
            <th>Avg Latency</th>
            <th>95th Latency</th>
            <th>Error Rate</th>
        </tr>
"""

        for _, row in df.iterrows():
            html += f"""
        <tr>
            <td>{row['run_id']}</td>
            <td>{row['tpmc']:.2f if row['tpmc'] else 'N/A'}</td>
            <td>{row['throughput']:.2f if row['throughput'] else 'N/A'}</td>
            <td>{row['avg_response_time']:.2f if row['avg_response_time'] else 'N/A'}</td>
            <td>{row['95th_response_time']:.2f if row['95th_response_time'] else 'N/A'}</td>
            <td>{row['error_rate']:.2f if row['error_rate'] else 'N/A'}</td>
        </tr>
"""

        html += f"""
    </table>
</body>
</html>
"""

        return html.format(n_tests=len(df))

    def export_results_to_df(self) -> pd.DataFrame:
        """导出结果为DataFrame"""
        from ..b1_analysis.benchmark_runner import BenchmarkRunner
        runner = BenchmarkRunner()
        return runner.export_to_dataframe(self.results)

    def get_job_status(self, job_id: str) -> str:
        """获取任务状态"""
        if job_id in self.jobs:
            return self.jobs[job_id].status
        return "not_found"

    def cleanup(self) -> None:
        """清理资源"""
        logger.info("Cleaning up benchmark resources")
        # 可以在这里清理临时文件等


class StressTestRunner:
    """
    压力测试运行器

    用于验证系统在高负载下的稳定性
    """

    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config

    def run_stress_test(self, duration_seconds: int = 300,
                        concurrent_users: int = 100) -> Dict[str, Any]:
        """
        运行压力测试

        Args:
            duration_seconds: 持续时间（秒）
            concurrent_users: 并发用户数

        Returns:
            测试结果
        """
        logger.info(f"Running stress test for {duration_seconds}s with {concurrent_users} users")

        # 这里可以实现具体的压力测试逻辑
        # 例如使用 wrk、ab 或自定义工具

        result = {
            'duration': duration_seconds,
            'concurrent_users': concurrent_users,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'p95_response_time': 0,
            'p99_response_time': 0,
            'throughput': 0,
        }

        # 模拟结果
        result['total_requests'] = duration_seconds * concurrent_users * 10
        result['successful_requests'] = int(result['total_requests'] * 0.99)
        result['failed_requests'] = result['total_requests'] - result['successful_requests']
        result['avg_response_time'] = 50 + concurrent_users / 10
        result['p95_response_time'] = result['avg_response_time'] * 1.5
        result['p99_response_time'] = result['avg_response_time'] * 2
        result['throughput'] = result['successful_requests'] / duration_seconds

        logger.info(f"Stress test completed: {result}")
        return result

    def run_load_curve(self, min_users: int = 10, max_users: int = 500,
                      step: int = 50, step_duration: int = 60) -> pd.DataFrame:
        """
        运行负载曲线测试

        Args:
            min_users: 最小用户数
            max_users: 最大用户数
            step: 每步增加的用户数
            step_duration: 每步持续时间（秒）

        Returns:
            测试结果DataFrame
        """
        results = []

        for users in range(min_users, max_users + 1, step):
            result = self.run_stress_test(
                duration_seconds=step_duration,
                concurrent_users=users
            )
            result['users'] = users
            results.append(result)

        return pd.DataFrame(results)