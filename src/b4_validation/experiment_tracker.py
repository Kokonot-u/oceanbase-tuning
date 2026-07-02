"""
实验追踪器

使用MLflow记录和对比实验结果。
"""

from typing import Optional, Dict, Any, List
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from loguru import logger

try:
    import mlflow
    import mlflow.pytorch
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logger.warning("MLflow not available")


@dataclass
class ExperimentConfig:
    """实验配置"""
    experiment_name: str = "oceanbase_tuning"
    run_name: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    params: Optional[Dict[str, Any]] = None


class ExperimentTracker:
    """
    MLflow实验追踪器

    记录和对比OceanBase调优实验
    """

    def __init__(self, tracking_uri: Optional[str] = None,
                 experiment_name: str = "oceanbase_tuning"):
        """
        初始化实验追踪器

        Args:
            tracking_uri: MLflow追踪URI
            experiment_name: 实验名称
        """
        if not MLFLOW_AVAILABLE:
            raise ImportError("MLflow is required")

        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)

        self.experiment_name = experiment_name
        self.client = MlflowClient()

        # 确保实验存在
        self._ensure_experiment()

        self.active_run = None

    def _ensure_experiment(self) -> None:
        """确保实验存在"""
        try:
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                mlflow.create_experiment(self.experiment_name)
                logger.info(f"Created experiment: {self.experiment_name}")
        except Exception as e:
            logger.error(f"Failed to ensure experiment: {e}")

    def start_run(self, run_name: Optional[str] = None,
                 tags: Optional[Dict[str, str]] = None) -> str:
        """
        开始一个新的实验运行

        Args:
            run_name: 运行名称
            tags: 标签

        Returns:
            运行ID
        """
        run_name = run_name or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.active_run = mlflow.start_run(
            run_name=run_name,
            experiment_id=mlflow.get_experiment_by_name(self.experiment_name).experiment_id
        )

        if tags:
            mlflow.set_tags(tags)

        logger.info(f"Started run: {run_name} (ID: {self.active_run.info.run_id})")
        return self.active_run.info.run_id

    def log_params(self, params: Dict[str, Any]) -> None:
        """
        记录参数

        Args:
            params: 参数字典
        """
        if self.active_run is None:
            logger.warning("No active run to log params")
            return

        # MLflow参数必须是字符串或数值
        for key, value in params.items():
            try:
                if isinstance(value, (dict, list)):
                    # 复杂类型记录为JSON字符串
                    mlflow.log_param(key, json.dumps(value))
                else:
                    mlflow.log_param(key, str(value))
            except Exception as e:
                logger.warning(f"Failed to log param {key}: {e}")

        logger.info(f"Logged {len(params)} parameters")

    def log_metrics(self, metrics: Dict[str, float],
                   step: Optional[int] = None) -> None:
        """
        记录指标

        Args:
            metrics: 指标字典
            step: 步骤
        """
        if self.active_run is None:
            logger.warning("No active run to log metrics")
            return

        mlflow.log_metrics(metrics, step=step)
        logger.info(f"Logged {len(metrics)} metrics")

    def log_benchmark_results(self, results: Dict[str, float]) -> None:
        """
        记录基准测试结果

        Args:
            results: 基准测试结果
        """
        benchmark_metrics = {
            'tpmc': results.get('tpmc', 0),
            'throughput': results.get('throughput', 0),
            'avg_latency_ms': results.get('latency', 0),
            'p95_latency_ms': results.get('p95_latency', 0),
            'p99_latency_ms': results.get('p99_latency', 0),
            'error_rate_pct': results.get('error_rate', 0),
            'transactions': results.get('transactions', 0),
        }

        self.log_metrics(benchmark_metrics)

    def log_resource_metrics(self, metrics: Dict[str, float]) -> None:
        """
        记录资源指标

        Args:
            metrics: 资源指标
        """
        resource_metrics = {
            'cpu_usage_pct': metrics.get('cpu_usage', 0),
            'memory_usage_pct': metrics.get('memory_usage', 0),
            'io_usage_pct': metrics.get('io_usage', 0),
            'network_usage_pct': metrics.get('network_usage', 0),
        }

        self.log_metrics(resource_metrics)

    def log_artifact(self, file_path: str, artifact_path: Optional[str] = None) -> None:
        """
        记录文件作为artifact

        Args:
            file_path: 文件路径
            artifact_path: artifact路径
        """
        if self.active_run is None:
            logger.warning("No active run to log artifact")
            return

        mlflow.log_artifact(file_path, artifact_path)
        logger.info(f"Logged artifact: {file_path}")

    def log_model(self, model, model_name: str = "model") -> None:
        """
        记录模型

        Args:
            model: 模型对象
            model_name: 模型名称
        """
        if self.active_run is None:
            logger.warning("No active run to log model")
            return

        try:
            # 尝试PyTorch模型
            import torch
            mlflow.pytorch.log_model(model, model_name)
            logger.info(f"Logged PyTorch model: {model_name}")
        except:
            try:
                # 尝试sklearn模型
                mlflow.sklearn.log_model(model, model_name)
                logger.info(f"Logged sklearn model: {model_name}")
            except:
                logger.warning("Failed to log model")

    def end_run(self, status: str = "FINISHED") -> None:
        """
        结束当前运行

        Args:
            status: 状态 (FINISHED, FAILED, KILLED)
        """
        if self.active_run is None:
            logger.warning("No active run to end")
            return

        run_id = self.active_run.info.run_id
        mlflow.end_run()
        self.active_run = None

        logger.info(f"Ended run: {run_id} with status: {status}")

    def compare_runs(self, run_ids: List[str],
                     metric_names: List[str]) -> pd.DataFrame:
        """
        对比多个运行

        Args:
            run_ids: 运行ID列表
            metric_names: 要对比的指标名称

        Returns:
            对比结果DataFrame
        """
        import pandas as pd

        comparison = []

        for run_id in run_ids:
            run = self.client.get_run(run_id)
            run_data = {
                'run_id': run_id,
                'run_name': run.data.tags.get('mlflow.runName', ''),
            }

            # 添加指标
            for metric_name in metric_names:
                if metric_name in run.data.metrics:
                    run_data[metric_name] = run.data.metrics[metric_name]

            # 添加参数
            for param_name, param_value in run.data.params.items():
                if param_name not in run_data:
                    run_data[param_name] = param_value

            comparison.append(run_data)

        return pd.DataFrame(comparison)

    def get_best_run(self, metric_name: str,
                    maximize: bool = True) -> Optional[str]:
        """
        获取最佳运行

        Args:
            metric_name: 指标名称
            maximize: 是否最大化

        Returns:
            最佳运行ID
        """
        experiment = mlflow.get_experiment_by_name(self.experiment_name)
        runs = self.client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=[f"metrics.{metric_name} {'DESC' if maximize else 'ASC'}"]
        )

        if runs:
            best_run = runs[0]
            logger.info(f"Best run for {metric_name}: {best_run.info.run_id} "
                       f"(value: {best_run.data.metrics.get(metric_name, 'N/A')})")
            return best_run.info.run_id

        return None

    def get_run_history(self, run_id: str,
                       metric_name: str) -> pd.DataFrame:
        """
        获取运行的指标历史

        Args:
            run_id: 运行ID
            metric_name: 指标名称

        Returns:
            历史数据DataFrame
        """
        import pandas as pd

        history = self.client.get_metric_history(run_id, metric_name)

        data = [{'step': h.step, 'value': h.value, 'timestamp': h.timestamp}
                for h in history]

        return pd.DataFrame(data)

    def search_runs(self, filter_string: str = "",
                    max_results: int = 1000) -> List:
        """
        搜索运行

        Args:
            filter_string: 过滤字符串
            max_results: 最大结果数

        Returns:
            运行列表
        """
        experiment = mlflow.get_experiment_by_name(self.experiment_name)
        return self.client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=filter_string,
            max_results=max_results
        )

    def delete_run(self, run_id: str) -> None:
        """
        删除运行

        Args:
            run_id: 运行ID
        """
        self.client.delete_run(run_id)
        logger.info(f"Deleted run: {run_id}")

    def restore_run(self, run_id: str) -> None:
        """
        恢复已删除的运行

        Args:
            run_id: 运行ID
        """
        self.client.restore_run(run_id)
        logger.info(f"Restored run: {run_id}")

    def export_runs(self, output_path: str,
                   filter_string: str = "") -> None:
        """
        导出运行数据

        Args:
            output_path: 输出路径
            filter_string: 过滤字符串
        """
        runs = self.search_runs(filter_string)

        export_data = []

        for run in runs:
            run_data = {
                'run_id': run.info.run_id,
                'run_name': run.data.tags.get('mlflow.runName', ''),
                'start_time': run.info.start_time,
                'end_time': run.info.end_time,
                'status': run.info.status,
                'params': run.data.params,
                'metrics': run.data.metrics,
                'tags': run.data.tags,
            }
            export_data.append(run_data)

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        logger.info(f"Exported {len(export_data)} runs to {output_path}")


def create_comparison_report(tracker: ExperimentTracker,
                            run_ids: List[str],
                            output_path: str) -> None:
    """
    创建实验对比报告

    Args:
        tracker: 实验追踪器
        run_ids: 运行ID列表
        output_path: 输出路径
    """
    import pandas as pd

    # 获取运行信息
    runs = [tracker.client.get_run(rid) for rid in run_ids]

    # 创建报告
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>实验对比报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .best { background-color: #d4edda; }
    </style>
</head>
<body>
    <h1>OceanBase调优实验对比报告</h1>
    <p>生成时间: {timestamp}</p>

    <h2>运行概览</h2>
    <table>
        <tr>
            <th>运行名称</th>
            <th>运行ID</th>
            <th>TPMC</th>
            <th>平均延迟(ms)</th>
            <th>CPU使用率</th>
            <th>内存使用率</th>
            <th>状态</th>
        </tr>
"""

    # 找出最佳TPMC
    tpmc_values = [run.data.metrics.get('tpmc', 0) for run in runs]
    max_tpmc = max(tpmc_values) if tpmc_values else 0

    for run in runs:
        tpmc = run.data.metrics.get('tpmc', 0)
        is_best = tpmc == max_tpmc

        html += f"""
        <tr class="{'best' if is_best else ''}">
            <td>{run.data.tags.get('mlflow.runName', 'N/A')}</td>
            <td>{run.info.run_id[:8]}</td>
            <td>{tpmc:.2f if tpmc else 'N/A'}</td>
            <td>{run.data.metrics.get('avg_latency_ms', 0):.2f}</td>
            <td>{run.data.metrics.get('cpu_usage_pct', 0):.1f}%</td>
            <td>{run.data.metrics.get('memory_usage_pct', 0):.1f}%</td>
            <td>{run.info.status}</td>
        </tr>
"""

    html += """
    </table>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html.format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    logger.info(f"Comparison report saved to {output_path}")