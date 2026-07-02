"""
资源数据模拟器

生成模拟的历史资源数据（CPU、内存、IO、网络），用于容量规划。
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger


@dataclass
class SimulationConfig:
    """模拟配置"""
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    interval_minutes: int = 60  # 采样间隔（分钟）
    base_cpu: float = 30.0  # 基础CPU使用率(%)
    base_memory: float = 50.0  # 基础内存使用率(%)
    base_io: float = 20.0  # 基础IO使用率(%)
    base_network: float = 10.0  # 基础网络使用率(%)
    trend_growth: float = 0.01  # 月增长率
    seasonality_amplitude: float = 0.15  # 季节性振幅
    noise_level: float = 0.05  # 噪声水平
    event_probability: float = 0.02  # 突发事件概率


class ResourceDataSimulator:
    """
    资源数据模拟器

    生成符合实际业务特征的OceanBase资源使用历史数据
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        """
        初始化模拟器

        Args:
            config: 模拟配置
        """
        self.config = config or SimulationConfig()

    def generate(self) -> pd.DataFrame:
        """
        生成完整的资源使用数据

        Returns:
            包含CPU、内存、IO、网络等指标的DataFrame
        """
        # 生成时间序列
        timestamps = self._generate_timestamps()
        n = len(timestamps)

        # 生成基础趋势
        trend = self._generate_trend(n)

        # 生成季节性
        seasonality = self._generate_seasonality(n, timestamps)

        # 生成噪声
        noise = np.random.normal(0, self.config.noise_level, n)

        # 生成突发事件
        events = self._generate_events(n)

        # 组合生成各项指标
        data = {
            'timestamp': timestamps,
            'cpu_usage': self._generate_metric(
                self.config.base_cpu, trend, seasonality, noise, events
            ),
            'memory_usage': self._generate_metric(
                self.config.base_memory, trend * 0.8, seasonality * 0.6, noise * 0.5, events * 0.3
            ),
            'io_usage': self._generate_metric(
                self.config.base_io, trend, seasonality, noise, events
            ),
            'network_usage': self._generate_metric(
                self.config.base_network, trend, seasonality, noise, events
            ),
            'disk_io_read': self._generate_io_metric('read', n),
            'disk_io_write': self._generate_io_metric('write', n),
            'net_bytes_in': self._generate_network_metric('in', n),
            'net_bytes_out': self._generate_network_metric('out', n),
            'active_connections': self._generate_connections(n),
        }

        df = pd.DataFrame(data)

        # 添加业务相关特征
        df = self._add_business_features(df)

        logger.info(f"Generated {len(df)} data points from {df['timestamp'].min()} to {df['timestamp'].max()}")
        return df

    def _generate_timestamps(self) -> pd.DatetimeIndex:
        """生成时间戳序列"""
        start = pd.to_datetime(self.config.start_date)
        end = pd.to_datetime(self.config.end_date)

        return pd.date_range(
            start=start,
            end=end,
            freq=f"{self.config.interval_minutes}min"
        )

    def _generate_trend(self, n: int) -> np.ndarray:
        """生成增长趋势"""
        # 将月增长率转换为时间步增长率
        steps_per_month = 30 * 24 * 60 // self.config.interval_minutes
        step_growth = self.config.trend_growth / steps_per_month

        trend = np.cumsum(np.full(n, step_growth))
        return trend

    def _generate_seasonality(self, n: int, timestamps: pd.DatetimeIndex) -> np.ndarray:
        """生成季节性（日周期 + 周周期）"""
        hour = timestamps.hour
        day_of_week = timestamps.dayofweek

        # 日周期（白天高，夜间低）
        daily_pattern = np.sin((hour - 6) * np.pi / 12) * 0.1

        # 周周期（工作日高，周末低）
        weekly_pattern = (1 - (day_of_week >= 5).astype(float)) * 0.05

        return daily_pattern + weekly_pattern

    def _generate_events(self, n: int) -> np.ndarray:
        """生成突发事件（如促销活动、系统故障等）"""
        events = np.zeros(n)

        # 随机选择事件发生时间点
        event_indices = np.random.choice(
            n,
            size=int(n * self.config.event_probability),
            replace=False
        )

        for idx in event_indices:
            # 生成持续影响
            duration = np.random.randint(1, 24)  # 持续1-24个时间点
            magnitude = np.random.uniform(0.1, 0.4)

            events[idx:idx+duration] += magnitude

        return events

    def _generate_metric(self, base: float, trend: np.ndarray,
                         seasonality: np.ndarray, noise: np.ndarray,
                         events: np.ndarray) -> np.ndarray:
        """生成单个指标"""
        value = base + trend * base + seasonality * base + noise * base + events * base
        return np.clip(value, 0, 100)  # 限制在0-100%

    def _generate_io_metric(self, io_type: str, n: int) -> np.ndarray:
        """生成IO指标（读/写字节数）"""
        if io_type == 'read':
            base = 10_000_000  # 10MB/s
        else:
            base = 5_000_000  # 5MB/s

        # 与IO使用率相关
        io_usage = self.config.base_io / 100

        # 添加随机波动
        variation = np.random.normal(1, 0.3, n)

        return base * io_usage * variation

    def _generate_network_metric(self, net_type: str, n: int) -> np.ndarray:
        """生成网络指标（入/出流量）"""
        if net_type == 'in':
            base = 1_000_000  # 1MB/s
        else:
            base = 500_000  # 500KB/s

        # 与网络使用率相关
        net_usage = self.config.base_network / 100

        variation = np.random.normal(1, 0.4, n)

        return base * net_usage * variation

    def _generate_connections(self, n: int) -> np.ndarray:
        """生成活跃连接数"""
        base = 100
        variation = np.random.normal(1, 0.2, n)
        return base * variation.astype(int)

    def _add_business_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加业务相关特征"""
        # 时间特征
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_month'] = df['timestamp'].dt.day
        df['month'] = df['timestamp'].dt.month
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['is_business_hour'] = ((df['hour'] >= 9) & (df['hour'] < 18)).astype(int)

        # 派生指标
        df['cpu_memory_ratio'] = df['cpu_usage'] / (df['memory_usage'] + 1e-6)
        df['io_network_ratio'] = df['io_usage'] / (df['network_usage'] + 1e-6)

        # 突发事件标识
        cpu_mean = df['cpu_usage'].rolling(window=24, min_periods=1).mean()
        cpu_std = df['cpu_usage'].rolling(window=24, min_periods=1).std()
        df['is_spike'] = ((df['cpu_usage'] - cpu_mean) > (2 * cpu_std)).astype(int)

        return df

    def generate_peak_scenarios(self, n_scenarios: int = 5) -> List[pd.DataFrame]:
        """
        生成峰值场景数据

        Args:
            n_scenarios: 场景数量

        Returns:
            场景数据列表
        """
        scenarios = []

        peak_multipliers = [1.5, 2.0, 2.5, 3.0, 4.0][:n_scenarios]

        for multiplier in peak_multipliers:
            config = SimulationConfig(
                start_date=self.config.start_date,
                end_date=(pd.to_datetime(self.config.start_date) + timedelta(days=7)).strftime('%Y-%m-%d'),
                interval_minutes=self.config.interval_minutes,
                base_cpu=min(95, self.config.base_cpu * multiplier),
                base_memory=min(95, self.config.base_memory * multiplier * 0.8),
                base_io=min(95, self.config.base_io * multiplier),
                base_network=min(95, self.config.base_network * multiplier * 0.5),
                noise_level=self.config.noise_level * 0.5,  # 降低噪声以保持峰值特征
            )

            simulator = ResourceDataSimulator(config)
            scenarios.append(simulator.generate())

        return scenarios

    def save(self, data: pd.DataFrame, output_path: str) -> None:
        """
        保存模拟数据

        Args:
            data: 模拟数据
            output_path: 输出路径
        """
        from pathlib import Path

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if output_path.endswith('.csv'):
            data.to_csv(output_path, index=False)
        elif output_path.endswith('.parquet'):
            data.to_parquet(output_path, index=False)
        else:
            # 默认保存为CSV
            data.to_csv(output_path, index=False)

        logger.info(f"Saved simulated data to {output_path}")

    @classmethod
    def from_real_data(cls, data: pd.DataFrame, config: Optional[SimulationConfig] = None):
        """
        基于真实数据创建模拟器

        Args:
            data: 真实数据
            config: 模拟配置

        Returns:
            配置好的模拟器
        """
        # 从真实数据推断配置参数
        config = config or SimulationConfig()

        if 'cpu_usage' in data.columns:
            config.base_cpu = data['cpu_usage'].mean()
            config.noise_level = data['cpu_usage'].std() / config.base_cpu

        if 'memory_usage' in data.columns:
            config.base_memory = data['memory_usage'].mean()

        if 'io_usage' in data.columns:
            config.base_io = data['io_usage'].mean()

        if 'network_usage' in data.columns:
            config.base_network = data['network_usage'].mean()

        # 计算增长率
        if len(data) > 30:
            monthly_growth = (data['cpu_usage'].iloc[-30:].mean() -
                             data['cpu_usage'].iloc[:30].mean()) / data['cpu_usage'].iloc[:30].mean()
            config.trend_growth = max(0, monthly_growth)

        return cls(config)


class WorkloadSimulator:
    """
    工作负载模拟器

    模拟不同类型的工作负载（OLTP、OLAP、混合型）
    """

    WORKLOAD_PATTERNS = {
        'oltp': {
            'cpu_pattern': 'bursty',  # 突发型
            'io_pattern': 'random',   # 随机IO
            'network_pattern': 'low', # 低网络
            'cpu_io_ratio': 0.7,      # CPU主导
        },
        'olap': {
            'cpu_pattern': 'steady',  # 稳定型
            'io_pattern': 'sequential', # 顺序IO
            'network_pattern': 'medium', # 中等网络
            'cpu_io_ratio': 0.4,      # IO主导
        },
        'mixed': {
            'cpu_pattern': 'mixed',   # 混合型
            'io_pattern': 'mixed',    # 混合IO
            'network_pattern': 'medium', # 中等网络
            'cpu_io_ratio': 0.5,      # 均衡
        },
        'htap': {
            'cpu_pattern': 'steady_high', # 稳定高负载
            'io_pattern': 'mixed',    # 混合IO
            'network_pattern': 'high', # 高网络
            'cpu_io_ratio': 0.5,      # 均衡
        },
    }

    def __init__(self, workload_type: str = 'mixed'):
        """
        初始化工作负载模拟器

        Args:
            workload_type: 工作负载类型 (oltp, olap, mixed, htap)
        """
        self.workload_type = workload_type
        self.pattern = self.WORKLOAD_PATTERNS.get(workload_type, self.WORKLOAD_PATTERNS['mixed'])

    def generate(self, n_points: int = 1000) -> pd.DataFrame:
        """
        生成工作负载数据

        Args:
            n_points: 数据点数量

        Returns:
            工作负载数据
        """
        timestamps = pd.date_range(
            start='2024-01-01',
            periods=n_points,
            freq='1min'
        )

        # 根据工作负载类型生成不同的模式
        cpu_pattern = self._generate_pattern(self.pattern['cpu_pattern'], n_points)
        io_pattern = self._generate_pattern(self.pattern['io_pattern'], n_points)
        network_pattern = self._generate_pattern(self.pattern['network_pattern'], n_points)

        # 根据CPU/IO比率调整
        if self.pattern['cpu_io_ratio'] > 0.5:
            cpu_base = 50
            io_base = 30
        else:
            cpu_base = 30
            io_base = 50

        data = {
            'timestamp': timestamps,
            'query_per_second': cpu_base * cpu_pattern + np.random.normal(0, 5, n_points),
            'transactions_per_second': io_base * io_pattern + np.random.normal(0, 3, n_points),
            'cpu_usage': np.clip(cpu_base * cpu_pattern / 100 * np.random.uniform(0.8, 1.2, n_points), 0, 100),
            'io_usage': np.clip(io_base * io_pattern / 100 * np.random.uniform(0.8, 1.2, n_points), 0, 100),
            'network_usage': np.clip(20 * network_pattern + np.random.normal(0, 5, n_points), 0, 100),
        }

        return pd.DataFrame(data)

    def _generate_pattern(self, pattern_type: str, n: int) -> np.ndarray:
        """生成特定模式的序列"""
        if pattern_type == 'bursty':
            # 突发型：平静后突发
            pattern = np.ones(n) * 0.3
            for i in range(0, n, 100):
                burst_duration = np.random.randint(10, 30)
                if i + burst_duration < n:
                    pattern[i:i+burst_duration] = np.random.uniform(0.8, 1.2, burst_duration)
        elif pattern_type == 'steady':
            # 稳定型：小幅波动
            pattern = np.random.uniform(0.9, 1.1, n)
        elif pattern_type == 'sequential':
            # 顺序型：持续增长后下降
            pattern = np.sin(np.linspace(0, 4*np.pi, n)) * 0.3 + 1
        else:  # mixed
            # 混合型
            pattern = 0.5 * np.sin(np.linspace(0, 2*np.pi, n)) + 0.5 * np.random.uniform(0.5, 1.5, n)

        return np.clip(pattern, 0.1, 2.0)