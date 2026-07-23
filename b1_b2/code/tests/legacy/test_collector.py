"""
测试数据采集器
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from collector.ob_collector import OBCollector


class TestOBCollector:
    """数据采集器测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库连接器"""
        db = Mock()
        return db

    @pytest.fixture
    def collector(self, mock_db):
        """创建采集器"""
        return OBCollector(mock_db)

    def test_collect_cpu_usage(self, collector, mock_db):
        """测试CPU采集"""
        mock_db.execute_query.return_value = pd.DataFrame({
            'svr_ip': ['127.0.0.1'],
            'svr_port': [2882],
            'cpu_usage': [50.0],
            'cpu_time_in_us': [1000000],
            'iops': [1000],
        })

        result = collector.collect_cpu_usage()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        mock_db.execute_query.assert_called_once()

    def test_collect_memory_usage(self, collector, mock_db):
        """测试内存采集"""
        mock_db.execute_query.return_value = pd.DataFrame({
            'svr_ip': ['127.0.0.1'],
            'svr_port': [2882],
            'mem_total': [8589934592],
            'mem_used': [4294967296],
            'mem_limit': [8589934592],
            'usage': [50.0],
        })

        result = collector.collect_memory_usage()
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_collect_sql_stats(self, collector, mock_db):
        """测试SQL统计采集"""
        mock_db.execute_query.return_value = pd.DataFrame({
            'tenant_id': [1],
            'plan_id': [1],
            'sql_id': ['abc123'],
            'execute_times': [100],
            'elapsed_time': [1000000],
        })

        result = collector.collect_sql_stats()
        assert isinstance(result, pd.DataFrame)

    def test_collect_slow_queries(self, collector, mock_db):
        """测试慢查询采集"""
        mock_db.execute_query.return_value = pd.DataFrame({
            'tenant_id': [1],
            'query_sql': ['SELECT * FROM test;'],
            'elapsed_time': [2000000],
            'execute_times': [1],
        })

        result = collector.collect_slow_queries(limit=10)
        assert isinstance(result, pd.DataFrame)

    def test_collect_performance_metrics(self, collector, mock_db):
        """测试完整性能指标采集"""
        mock_db.execute_query.return_value = pd.DataFrame()

        metrics = collector.collect_performance_metrics()
        assert 'cpu_usage' in metrics
        assert 'memory_usage' in metrics
        assert 'sql_stats' in metrics
        assert 'slow_queries' in metrics
        assert 'lock_waits' in metrics
        assert 'parameters' in metrics

        # 验证调用次数
        assert mock_db.execute_query.call_count >= 6


if __name__ == '__main__':
    pytest.main([__file__, '-v'])