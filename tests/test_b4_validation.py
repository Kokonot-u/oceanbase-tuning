"""
测试B4验证模块
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from b4_validation.auto_benchmark import AutoBenchmark, BenchmarkJob
from b4_validation.param_applier import ParamApplier


class TestBenchmarkJob:
    """基准测试任务测试"""

    def test_benchmark_job_creation(self):
        """测试任务创建"""
        job = BenchmarkJob(
            job_id='test_job',
            config={'benchmark_type': 'tpcc'},
            params={'param1': 'value1'}
        )

        assert job.job_id == 'test_job'
        assert job.status == 'pending'
        assert job.result is None
        assert job.params == {'param1': 'value1'}


class TestAutoBenchmark:
    """自动化基准测试测试"""

    @pytest.fixture
    def db_config(self):
        return {
            'host': '127.0.0.1',
            'port': '2881',
            'user': 'test',
            'password': 'test',
            'database': 'test'
        }

    @pytest.fixture
    def auto_benchmark(self, db_config, tmp_path):
        return AutoBenchmark(db_config, str(tmp_path / 'benchmarks'))

    def test_create_job(self, auto_benchmark):
        """测试创建任务"""
        job = auto_benchmark.create_job('test_job', 'tpcc', {'param': 'value'})

        assert job.job_id == 'test_job'
        assert job.status == 'pending'
        assert 'test_job' in auto_benchmark.jobs

    def test_get_job_status(self, auto_benchmark):
        """测试获取任务状态"""
        auto_benchmark.create_job('test_job')
        assert auto_benchmark.get_job_status('test_job') == 'pending'
        assert auto_benchmark.get_job_status('nonexistent') == 'not_found'


class TestParamApplier:
    """参数应用器测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库连接器"""
        db = Mock()
        db.execute_update = Mock()
        db.execute_query = Mock()
        return db

    @pytest.fixture
    def applier(self, mock_db):
        return ParamApplier(mock_db)

    def test_apply_param(self, applier, mock_db):
        """测试应用单个参数"""
        mock_db.execute_query.return_value = pd.DataFrame({
            'edit_level': ['dynamic'],
            'min': [None],
            'max': [None]
        })

        result = applier.apply_param('test_param', 'test_value')

        assert result is True
        assert 'test_param' in applier.applied_params
        mock_db.execute_update.assert_called_once()

    def test_apply_params(self, applier, mock_db):
        """测试批量应用参数"""
        mock_db.execute_query.return_value = pd.DataFrame({
            'edit_level': ['dynamic'],
            'min': [None],
            'max': [None]
        })

        params = {
            'param1': 'value1',
            'param2': 'value2'
        }
        results = applier.apply_params(params)

        assert len(results) == 2
        assert all(results.values())
        assert mock_db.execute_update.call_count == 2

    def test_validate_param_readonly(self, applier, mock_db):
        """测试只读参数验证"""
        mock_db.execute_query.return_value = pd.DataFrame({
            'edit_level': ['readonly'],
            'min': [None],
            'max': [None]
        })

        result = applier._validate_param('readonly_param', 'value')
        assert result is False

    def test_validate_param_out_of_range(self, applier, mock_db):
        """测试参数超出范围"""
        mock_db.execute_query.return_value = pd.DataFrame({
            'edit_level': ['dynamic'],
            'min': [0],
            'max': [100]
        })

        result = applier._validate_param('test_param', 150)
        assert result is False

    def test_get_current_value(self, applier, mock_db):
        """测试获取当前参数值"""
        mock_db.execute_query.return_value = pd.DataFrame({
            'value': ['current_value']
        })

        value = applier.get_current_value('test_param')
        assert value == 'current_value'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])