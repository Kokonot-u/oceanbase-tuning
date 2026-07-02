"""
容量规划报告生成器

生成OceanBase容量规划报告，包含Matplotlib/Seaborn可视化图表。
"""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from loguru import logger

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import seaborn as sns
    from matplotlib.gridspec import GridSpec
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib/Seaborn not available")

# 设置中文字体支持（可选）
try:
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass


@dataclass
class CapacityAlert:
    """容量告警"""
    metric: str
    current_value: float
    threshold: float
    severity: str  # "info", "warning", "critical"
    recommendation: str
    predicted_exhaustion: Optional[datetime] = None


@dataclass
class CapacitySummary:
    """容量规划摘要"""
    period_start: datetime
    period_end: datetime
    current_usage: Dict[str, float]
    peak_usage: Dict[str, float]
    average_usage: Dict[str, float]
    growth_rate: Dict[str, float]
    alerts: List[CapacityAlert]


class CapacityReportGenerator:
    """
    容量规划报告生成器

    生成包含分析和可视化的容量规划报告
    """

    ALERT_THRESHOLDS = {
        'cpu_usage': {'warning': 70, 'critical': 85},
        'memory_usage': {'warning': 75, 'critical': 90},
        'io_usage': {'warning': 70, 'critical': 85},
        'network_usage': {'warning': 60, 'critical': 80},
        'disk_usage': {'warning': 80, 'critical': 90},
    }

    def __init__(self, style: str = 'whitegrid'):
        """
        初始化报告生成器

        Args:
            style: Seaborn样式
        """
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("Matplotlib/Seaborn are required")

        self.style = style
        sns.set_style(style)
        self.figures = {}

    def generate_summary(self, data: pd.DataFrame,
                         predictions: Optional[pd.DataFrame] = None) -> CapacitySummary:
        """
        生成容量规划摘要

        Args:
            data: 历史资源数据
            predictions: 预测数据

        Returns:
            容量摘要
        """
        metrics = ['cpu_usage', 'memory_usage', 'io_usage', 'network_usage']
        current_usage = {}
        peak_usage = {}
        average_usage = {}
        growth_rate = {}

        for metric in metrics:
            if metric in data.columns:
                current_usage[metric] = data[metric].iloc[-1]
                peak_usage[metric] = data[metric].max()
                average_usage[metric] = data[metric].mean()

                # 计算增长率（最近30天 vs 前30天）
                if len(data) > 60:
                    recent = data[metric].iloc[-30:].mean()
                    previous = data[metric].iloc[-60:-30].mean()
                    growth_rate[metric] = ((recent - previous) / previous * 100) if previous > 0 else 0
                else:
                    growth_rate[metric] = 0

        # 生成告警
        alerts = self._generate_alerts(current_usage, growth_rate, predictions)

        summary = CapacitySummary(
            period_start=data['timestamp'].min(),
            period_end=data['timestamp'].max(),
            current_usage=current_usage,
            peak_usage=peak_usage,
            average_usage=average_usage,
            growth_rate=growth_rate,
            alerts=alerts
        )

        return summary

    def _generate_alerts(self, current_usage: Dict[str, float],
                        growth_rate: Dict[str, float],
                        predictions: Optional[pd.DataFrame]) -> List[CapacityAlert]:
        """生成容量告警"""
        alerts = []

        for metric, thresholds in self.ALERT_THRESHOLDS.items():
            if metric in current_usage:
                current = current_usage[metric]
                growth = growth_rate.get(metric, 0)

                if current >= thresholds['critical']:
                    severity = 'critical'
                    recommendation = f"{metric}已达{current:.1f}%，需立即扩容或优化"
                elif current >= thresholds['warning']:
                    severity = 'warning'
                    recommendation = f"{metric}为{current:.1f}%，建议制定扩容计划"
                elif growth > 20:  # 增长率超过20%
                    severity = 'warning'
                    recommendation = f"{metric}增长率{growth:.1f}%，需关注容量规划"
                else:
                    continue

                # 计算预计耗尽时间
                predicted_exhaustion = None
                if predictions is not None and metric in predictions.columns:
                    exhaustion_idx = predictions[predictions[metric] >= thresholds['critical']].index
                    if len(exhaustion_idx) > 0:
                        predicted_exhaustion = predictions.loc[exhaustion_idx[0], 'timestamp']

                alerts.append(CapacityAlert(
                    metric=metric,
                    current_value=current,
                    threshold=thresholds['warning'],
                    severity=severity,
                    recommendation=recommendation,
                    predicted_exhaustion=predicted_exhaustion
                ))

        return alerts

    def plot_usage_overview(self, data: pd.DataFrame, save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制资源使用概览图

        Args:
            data: 资源数据
            save_path: 保存路径

        Returns:
            图形对象
        """
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('OceanBase资源使用概览', fontsize=16, fontweight='bold')

        metrics = [
            ('cpu_usage', 'CPU使用率 (%)', axes[0, 0]),
            ('memory_usage', '内存使用率 (%)', axes[0, 1]),
            ('io_usage', 'IO使用率 (%)', axes[1, 0]),
            ('network_usage', '网络使用率 (%)', axes[1, 1])
        ]

        for metric, title, ax in metrics:
            if metric in data.columns:
                ax.plot(data['timestamp'], data[metric], linewidth=1, alpha=0.7)
                ax.fill_between(data['timestamp'], data[metric], alpha=0.3)

                # 添加告警线
                if metric in self.ALERT_THRESHOLDS:
                    thresholds = self.ALERT_THRESHOLDS[metric]
                    ax.axhline(y=thresholds['warning'], color='orange', linestyle='--', alpha=0.5, label='警告阈值')
                    ax.axhline(y=thresholds['critical'], color='red', linestyle='--', alpha=0.5, label='严重阈值')

                ax.set_title(title, fontsize=12)
                ax.set_ylabel('使用率 (%)')
                ax.grid(True, alpha=0.3)
                ax.legend(loc='upper right')

                # 格式化x轴
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                ax.xaxis.set_major_locator(mdates.MonthLocator())
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        if save_path:
            self._save_figure(fig, save_path)

        self.figures['usage_overview'] = fig
        return fig

    def plot_heatmap(self, data: pd.DataFrame, save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制使用率热力图

        Args:
            data: 资源数据
            save_path: 保存路径

        Returns:
            图形对象
        """
        # 准备热力图数据（按小时和星期几聚合）
        data_copy = data.copy()
        data_copy['hour'] = pd.to_datetime(data_copy['timestamp']).dt.hour
        data_copy['day_of_week'] = pd.to_datetime(data_copy['timestamp']).dt.dayofweek

        heatmap_data = data_copy.groupby(['day_of_week', 'hour']).agg({
            'cpu_usage': 'mean',
            'memory_usage': 'mean',
            'io_usage': 'mean',
            'network_usage': 'mean'
        }).reset_index()

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('资源使用热力图（星期 x 小时）', fontsize=16, fontweight='bold')

        days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

        for idx, metric in enumerate(['cpu_usage', 'memory_usage', 'io_usage', 'network_usage']):
            ax = axes[idx // 2, idx % 2]

            pivot_data = heatmap_data.pivot(index='day_of_week', columns='hour', values=metric)

            sns.heatmap(pivot_data, cmap='YlOrRd', cbar_kws={'label': '使用率 (%)'},
                       xticklabels=range(24), yticklabels=days, ax=ax)

            ax.set_title(f'{metric.replace("_", " ").title()}', fontsize=12)
            ax.set_xlabel('小时')
            ax.set_ylabel('星期')

        plt.tight_layout()

        if save_path:
            self._save_figure(fig, save_path)

        self.figures['heatmap'] = fig
        return fig

    def plot_distribution(self, data: pd.DataFrame, save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制使用率分布图

        Args:
            data: 资源数据
            save_path: 保存路径

        Returns:
            图形对象
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('资源使用率分布', fontsize=16, fontweight='bold')

        metrics = ['cpu_usage', 'memory_usage', 'io_usage', 'network_usage']

        for idx, metric in enumerate(metrics):
            ax = axes[idx // 2, idx % 2]

            if metric in data.columns:
                values = data[metric].dropna()

                # 直方图 + 核密度估计
                ax.hist(values, bins=50, alpha=0.7, density=True, edgecolor='black')
                from scipy import stats
                kde = stats.gaussian_kde(values)
                x_range = np.linspace(values.min(), values.max(), 200)
                ax.plot(x_range, kde(x_range), 'r-', linewidth=2, label='KDE')

                # 添加统计信息
                ax.axvline(values.mean(), color='green', linestyle='--', label=f'均值: {values.mean():.1f}%')
                ax.axvline(values.median(), color='blue', linestyle='--', label=f'中位数: {values.median():.1f}%')

                ax.set_xlabel('使用率 (%)')
                ax.set_ylabel('密度')
                ax.set_title(f'{metric.replace("_", " ").title()} 分布')
                ax.legend()
                ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            self._save_figure(fig, save_path)

        self.figures['distribution'] = fig
        return fig

    def plot_forecast(self, historical_data: pd.DataFrame,
                     forecast_data: pd.DataFrame,
                     save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制预测对比图

        Args:
            historical_data: 历史数据
            forecast_data: 预测数据
            save_path: 保存路径

        Returns:
            图形对象
        """
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('资源使用预测', fontsize=16, fontweight='bold')

        metrics = [
            ('cpu_usage', 'CPU使用率 (%)', axes[0, 0]),
            ('memory_usage', '内存使用率 (%)', axes[0, 1]),
            ('io_usage', 'IO使用率 (%)', axes[1, 0]),
            ('network_usage', '网络使用率 (%)', axes[1, 1])
        ]

        for metric, title, ax in metrics:
            # 绘制历史数据
            if metric in historical_data.columns:
                ax.plot(historical_data['timestamp'], historical_data[metric],
                       label='历史数据', color='blue', alpha=0.7)

                # 绘制预测数据
                if metric in forecast_data.columns:
                    ax.plot(forecast_data['timestamp'], forecast_data[metric],
                           label='预测数据', color='red', linestyle='--', alpha=0.7)

                    # 绘制置信区间（如果有）
                    if f'{metric}_lower' in forecast_data.columns:
                        ax.fill_between(forecast_data['timestamp'],
                                       forecast_data[f'{metric}_lower'],
                                       forecast_data[f'{metric}_upper'],
                                       alpha=0.2, color='red', label='置信区间')

                # 添加告警线
                if metric in self.ALERT_THRESHOLDS:
                    thresholds = self.ALERT_THRESHOLDS[metric]
                    ax.axhline(y=thresholds['critical'], color='red', linestyle=':', alpha=0.5)

                ax.set_title(title, fontsize=12)
                ax.set_ylabel('使用率 (%)')
                ax.legend(loc='upper left')
                ax.grid(True, alpha=0.3)

                # 格式化x轴
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        if save_path:
            self._save_figure(fig, save_path)

        self.figures['forecast'] = fig
        return fig

    def plot_capacity_trend(self, data: pd.DataFrame,
                           save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制容量趋势图（含增长趋势线）

        Args:
            data: 资源数据
            save_path: 保存路径

        Returns:
            图形对象
        """
        # 计算移动平均和增长趋势
        data_copy = data.copy().sort_values('timestamp').reset_index(drop=True)

        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('资源容量趋势分析', fontsize=16, fontweight='bold')

        metrics = ['cpu_usage', 'memory_usage', 'io_usage', 'network_usage']

        for idx, metric in enumerate(metrics):
            ax = axes[idx // 2, idx % 2]

            if metric in data_copy.columns:
                x = np.arange(len(data_copy))
                y = data_copy[metric].values

                # 绘制原始数据
                ax.plot(data_copy['timestamp'], y, alpha=0.5, label='原始数据', linewidth=1)

                # 绘制7天移动平均
                ma7 = data_copy[metric].rolling(window=7*24, min_periods=1).mean()
                ax.plot(data_copy['timestamp'], ma7, label='7天移动平均', linewidth=2)

                # 线性趋势
                from scipy import stats
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                trend_line = slope * x + intercept
                ax.plot(data_copy['timestamp'], trend_line,
                       label=f'趋势 (斜率: {slope:.4f})', linestyle='--', linewidth=2)

                ax.set_title(f'{metric.replace("_", " ").title()} 趋势', fontsize=12)
                ax.set_ylabel('使用率 (%)')
                ax.legend(loc='upper left')
                ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            self._save_figure(fig, save_path)

        self.figures['capacity_trend'] = fig
        return fig

    def plot_alert_summary(self, summary: CapacitySummary,
                          save_path: Optional[str] = None) -> plt.Figure:
        """
        绘制告警摘要图

        Args:
            summary: 容量摘要
            save_path: 保存路径

        Returns:
            图形对象
        """
        if not summary.alerts:
            logger.info("No alerts to display")
            return None

        fig, ax = plt.subplots(figsize=(12, 6))

        # 准备数据
        metrics = [alert.metric for alert in summary.alerts]
        current_values = [alert.current_value for alert in summary.alerts]
        severities = [alert.severity for alert in summary.alerts]

        # 颜色映射
        severity_colors = {'info': 'green', 'warning': 'orange', 'critical': 'red'}
        colors = [severity_colors.get(sev, 'gray') for sev in severities]

        # 绘制柱状图
        bars = ax.barh(metrics, current_values, color=colors, alpha=0.7)

        # 添加阈值线
        for alert in summary.alerts:
            metric = alert.metric
            threshold = alert.threshold
            ax.axvline(x=threshold, color='orange', linestyle='--', alpha=0.5)

            # 添加预测耗尽时间
            if alert.predicted_exhaustion:
                ax.text(threshold, metrics.index(metric),
                       f'预计耗尽: {alert.predicted_exhaustion.strftime("%Y-%m-%d")}',
                       verticalalignment='center', fontsize=8)

        ax.set_xlabel('使用率 (%)')
        ax.set_title('容量告警摘要', fontsize=14, fontweight='bold')
        ax.set_xlim(0, 100)
        ax.grid(True, axis='x', alpha=0.3)

        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=severity_colors[k], label=k.upper())
                          for k in severity_colors]
        ax.legend(handles=legend_elements, loc='lower right')

        plt.tight_layout()

        if save_path:
            self._save_figure(fig, save_path)

        self.figures['alert_summary'] = fig
        return fig

    def generate_report(self, data: pd.DataFrame,
                       predictions: Optional[pd.DataFrame] = None,
                       output_dir: str = 'reports') -> str:
        """
        生成完整的容量规划报告

        Args:
            data: 历史数据
            predictions: 预测数据
            output_dir: 输出目录

        Returns:
            报告路径
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_dir = output_path / f'capacity_report_{timestamp}'
        report_dir.mkdir(exist_ok=True)

        # 生成摘要
        summary = self.generate_summary(data, predictions)

        # 生成图表
        self.plot_usage_overview(data, str(report_dir / '01_usage_overview.png'))
        self.plot_heatmap(data, str(report_dir / '02_heatmap.png'))
        self.plot_distribution(data, str(report_dir / '03_distribution.png'))
        self.plot_capacity_trend(data, str(report_dir / '04_capacity_trend.png'))

        if predictions is not None:
            self.plot_forecast(data, predictions, str(report_dir / '05_forecast.png'))

        if summary.alerts:
            self.plot_alert_summary(summary, str(report_dir / '06_alert_summary.png'))

        # 生成HTML报告
        html_path = report_dir / 'index.html'
        self._generate_html_report(summary, data, predictions, html_path)

        # 生成Markdown报告
        md_path = report_dir / 'report.md'
        self._generate_markdown_report(summary, data, predictions, md_path)

        logger.info(f"Capacity report generated at {report_dir}")
        return str(report_dir)

    def _generate_html_report(self, summary: CapacitySummary,
                             data: pd.DataFrame,
                             predictions: Optional[pd.DataFrame],
                             output_path: Path) -> None:
        """生成HTML格式报告"""
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OceanBase容量规划报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; }}
        h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #007bff; margin-top: 30px; }}
        .summary-card {{ display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0; }}
        .metric {{ flex: 1; min-width: 200px; background: #f8f9fa; padding: 15px; border-radius: 8px; }}
        .metric h3 {{ margin: 0 0 10px 0; color: #666; font-size: 14px; }}
        .metric .value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .alert {{ padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .alert.warning {{ background-color: #fff3cd; border-left: 5px solid #ffc107; }}
        .alert.critical {{ background-color: #f8d7da; border-left: 5px solid #dc3545; }}
        .chart {{ margin: 20px 0; text-align: center; }}
        .chart img {{ max-width: 100%; border: 1px solid #ddd; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #007bff; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>OceanBase容量规划报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>数据范围: {summary.period_start.strftime('%Y-%m-%d')} 至 {summary.period_end.strftime('%Y-%m-%d')}</p>

        <h2>资源使用概览</h2>
        <div class="summary-card">
        """

        # 添加指标卡片
        for metric, value in summary.current_usage.items():
            peak = summary.peak_usage.get(metric, 0)
            growth = summary.growth_rate.get(metric, 0)
            html += f"""
            <div class="metric">
                <h3>{metric.replace('_', ' ').title()}</h3>
                <div class="value">{value:.1f}%</div>
                <small>峰值: {peak:.1f}% | 增长率: {growth:+.1f}%</small>
            </div>
            """

        html += """
        </div>

        <h2>容量告警</h2>
        """

        # 添加告警
        for alert in summary.alerts:
            alert_class = alert.severity
            exhaustion_text = ""
            if alert.predicted_exhaustion:
                exhaustion_text = f"<br><strong>预计耗尽:</strong> {alert.predicted_exhaustion.strftime('%Y-%m-%d')}"

            html += f"""
            <div class="alert {alert_class}">
                <strong>{alert.metric.upper()}</strong> - 当前值: {alert.current_value:.1f}%, 阈值: {alert.threshold}%<br>
                <strong>建议:</strong> {alert.recommendation}{exhaustion_text}
            </div>
            """

        # 添加图表
        charts = [
            ('资源使用概览', '01_usage_overview.png'),
            ('使用率热力图', '02_heatmap.png'),
            ('使用率分布', '03_distribution.png'),
            ('容量趋势', '04_capacity_trend.png'),
        ]

        if predictions is not None:
            charts.append(('预测对比', '05_forecast.png'))

        if summary.alerts:
            charts.append(('告警摘要', '06_alert_summary.png'))

        for title, filename in charts:
            html += f"""
            <h2>{title}</h2>
            <div class="chart">
                <img src="{filename}" alt="{title}">
            </div>
            """

        html += """
    </div>
</body>
</html>
        """

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"HTML report saved to {output_path}")

    def _generate_markdown_report(self, summary: CapacitySummary,
                                  data: pd.DataFrame,
                                  predictions: Optional[pd.DataFrame],
                                  output_path: Path) -> None:
        """生成Markdown格式报告"""
        md = f"""# OceanBase容量规划报告

**生成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**数据范围:** {summary.period_start.strftime('%Y-%m-%d')} 至 {summary.period_end.strftime('%Y-%m-%d')}

## 资源使用概览

| 指标 | 当前值 | 峰值 | 平均值 | 增长率 |
|------|--------|------|--------|--------|
"""

        for metric in ['cpu_usage', 'memory_usage', 'io_usage', 'network_usage']:
            if metric in summary.current_usage:
                current = summary.current_usage[metric]
                peak = summary.peak_usage.get(metric, 0)
                avg = summary.average_usage.get(metric, 0)
                growth = summary.growth_rate.get(metric, 0)
                md += f"| {metric.replace('_', ' ').title()} | {current:.1f}% | {peak:.1f}% | {avg:.1f}% | {growth:+.1f}% |\n"

        md += "\n## 容量告警\n\n"

        if not summary.alerts:
            md += "✅ 当前无容量告警\n"
        else:
            for alert in summary.alerts:
                emoji = "🟢" if alert.severity == "info" else "🟡" if alert.severity == "warning" else "🔴"
                md += f"{emoji} **{alert.metric.upper()}** - 当前值: {alert.current_value:.1f}%\n"
                md += f"   - 建议操作: {alert.recommendation}\n"
                if alert.predicted_exhaustion:
                    md += f"   - 预计耗尽: {alert.predicted_exhaustion.strftime('%Y-%m-%d')}\n"
                md += "\n"

        md += "\n## 图表\n\n"

        charts = [
            '01_usage_overview.png',
            '02_heatmap.png',
            '03_distribution.png',
            '04_capacity_trend.png',
        ]

        if predictions is not None:
            charts.append('05_forecast.png')

        for chart in charts:
            md += f"![{chart}]({chart})\n\n"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md)

        logger.info(f"Markdown report saved to {output_path}")

    def _save_figure(self, fig: plt.Figure, path: str) -> None:
        """保存图形"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, bbox_inches='tight')
        logger.debug(f"Saved figure to {path}")

    def close_all(self) -> None:
        """关闭所有图形"""
        plt.close('all')
        self.figures = {}