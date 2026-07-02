"""
测试B3容量规划数据模拟器
"""

import pytest
import pandas as pd
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from b3_capacity.data_simulator import (
    ResourceDataSimulator,
    SimulationConfig,
    WorkloadSimulator
)


class TestResourceDataSimulator:
    """资源数据模拟器测试"""

    def test_default_config(self):
        """测试默认配置"""
        config = SimulationConfig()
        assert config.start_date == "2024-01-01"
        assert config.end_date == "2024-12-31"
        assert config.interval_minutes == 60

    def test_custom_config(self):
        """测试自定义配置"""
        config = SimulationConfig(
            start_date="2024-01-01",
            end_date="2024-01-31",
            interval_minutes=30,
            base_cpu=40.0
        )
        assert config.base_cpu == 40.0
        assert config.interval_minutes == 30

    def test_generate_data(self):
        """测试数据生成"""
        simulator = ResourceDataSimulator()
        data = simulator.generate()

        # 验证数据结构
        assert isinstance(data, pd.DataFrame)
        assert 'timestamp' in data.columns
        assert 'cpu_usage' in data.columns
        assert 'memory_usage' in data.columns
        assert 'io_usage' in data.columns
        assert 'network_usage' in data.columns

        # 验证数据范围
        assert data['cpu_usage'].between(0, 100).all()
        assert data['memory_usage'].between(0, 100).all()

        # 验证时间范围
        assert data['timestamp'].min() <= data['timestamp'].max()

    def test_business_features(self):
        """测试业务特征生成"""
        simulator = ResourceDataSimulator(
            SimulationConfig(end_date="2024-01-31")
        )
        data = simulator.generate()

        assert 'hour' in data.columns
        assert 'day_of_week' in data.columns
        assert 'is_weekend' in data.columns
        assert 'is_business_hour' in data.columns

        # 验证小时范围
        assert data['hour'].between(0, 23).all()

        # 验证星期范围
        assert data['day_of_week'].between(0, 6).all()

    def test_generate_peak_scenarios(self):
        """测试峰值场景生成"""
        simulator = ResourceDataSimulator()
        scenarios = simulator.generate_peak_scenarios(n_scenarios=3)

        assert len(scenarios) == 3
        for scenario in scenarios:
            assert isinstance(scenario, pd.DataFrame)
            assert len(scenario) > 0

    def test_from_real_data(self, tmp_path):
        """测试从真实数据创建模拟器"""
        # 创建模拟真实数据
        real_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H'),
            'cpu_usage': [30 + i * 0.1 for i in range(100)],
            'memory_usage': [50] * 100,
            'io_usage': [20] * 100,
            'network_usage': [10] * 100,
        })

        # 保存
        data_path = tmp_path / 'real_data.csv'
        real_data.to_csv(data_path, index=False)

        # 创建模拟器
        simulator = ResourceDataSimulator.from_real_data(real_data)

        # 验证配置更新
        assert simulator.config.base_cpu > 30  # 应该反映真实数据的平均值


class TestWorkloadSimulator:
    """工作负载模拟器测试"""

    @pytest.mark.parametrize("workload_type", ['oltp', 'olap', 'mixed', 'htap'])
    def test_workload_types(self, workload_type):
        """测试不同工作负载类型"""
        simulator = WorkloadSimulator(workload_type)
        data = simulator.generate(n_points=100)

        assert isinstance(data, pd.DataFrame)
        assert 'timestamp' in data.columns
        assert 'query_per_second' in data.columns
        assert 'cpu_usage' in data.columns
        assert len(data) == 100

    def test_oltp_bursty_pattern(self):
        """测试OLTP的突发模式"""
        simulator = WorkloadSimulator('oltp')
        data = simulator.generate(n_points=200)

        # OLTP应该有更多的波动
        cpu_std = data['cpu_usage'].std()
        assert cpu_std > 5  # 应该有明显的波动

    def test_olap_steady_pattern(self):
        """测试OLAP的稳定模式"""
        simulator = WorkloadSimulator('olap')
        data = simulator.generate(n_points=200)

        # OLAP应该相对稳定
        cpu_std = data['cpu_usage'].std()
        assert cpu_std < 20  # 波动应该小于OLTP


if __name__ == '__main__':
    pytest.main([__file__, '-v'])