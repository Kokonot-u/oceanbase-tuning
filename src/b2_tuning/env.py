"""
OceanBase调优环境

基于Gymnasium实现的强化学习环境，用于OceanBase参数调优。
"""

from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from gymnasium import Env, spaces
from loguru import logger
import time


class OceanBaseTuningEnv(Env):
    """
    OceanBase参数调优环境

    状态空间: 当前参数配置 + 系统性能指标
    动作空间: 调整参数值（增加、减少、不变）
    奖励: 性能改善幅度 - 调整成本
    """

    metadata = {'render_modes': ['human']}

    def __init__(self,
                 param_space: Dict[str, Dict[str, Any]],
                 reward_mode: str = "tpmc",
                 max_steps: int = 50,
                 early_stop_patience: int = 10):
        """
        初始化环境

        Args:
            param_space: 参数搜索空间定义
            reward_mode: 奖励模式 ("tpmc", "latency", "throughput", "composite")
            max_steps: 最大步数
            early_stop_patience: 早停耐心值
        """
        super().__init__()

        self.param_space = param_space
        self.reward_mode = reward_mode
        self.max_steps = max_steps
        self.early_stop_patience = early_stop_patience

        # 初始化参数值
        self.current_params = self._init_params()
        self.baseline_params = self.current_params.copy()
        self.baseline_performance = None

        # 状态空间: 性能指标 + 参数值
        self.performance_dim = 5  # tpmc, latency, cpu_usage, memory_usage, io_usage
        self.param_dim = len(param_space)

        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.performance_dim + self.param_dim,),
            dtype=np.float32
        )

        # 动作空间: 每个参数可以增加、减少或不变
        # 离散动作: 0=不变, 1=增加, 2=减少
        self.action_space = spaces.MultiDiscrete([3] * self.param_dim)

        # 环境状态
        self.current_step = 0
        self.best_reward = -np.inf
        self.patience_counter = 0
        self.performance_history = []

        # 数据库连接器（需要外部注入）
        self.db_connector = None
        self.benchmark_runner = None

    def _init_params(self) -> Dict[str, float]:
        """初始化参数值为默认值"""
        return {
            name: info.get('default', info.get('min', 0))
            for name, info in self.param_space.items()
        }

    def reset(self, seed: Optional[int] = None,
              options: Optional[Dict] = None) -> Tuple[np.ndarray, Dict]:
        """
        重置环境

        Args:
            seed: 随机种子
            options: 额外选项

        Returns:
            初始观测值和信息字典
        """
        super().reset(seed=seed)

        self.current_step = 0
        self.current_params = self._init_params()
        self.baseline_params = self.current_params.copy()
        self.performance_history = []
        self.best_reward = -np.inf
        self.patience_counter = 0

        # 获取初始性能
        self.baseline_performance = self._get_performance(self.current_params)

        obs = self._get_observation()
        info = {
            'params': self.current_params.copy(),
            'performance': self.baseline_performance,
            'step': self.current_step
        }

        logger.info("Environment reset with initial configuration")
        return obs, info

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        执行一步动作

        Args:
            action: 动作数组，每个元素为0(不变)/1(增加)/2(减少)

        Returns:
            观测值、奖励、终止、截断、信息字典
        """
        self.current_step += 1

        # 应用动作
        self._apply_action(action)

        # 获取新性能
        new_performance = self._get_performance(self.current_params)

        # 计算奖励
        reward = self._calculate_reward(new_performance)

        # 更新历史
        self.performance_history.append(new_performance)

        # 检查终止条件
        terminated = self._check_termination()
        truncated = self.current_step >= self.max_steps

        obs = self._get_observation()

        info = {
            'params': self.current_params.copy(),
            'performance': new_performance,
            'reward': reward,
            'step': self.current_step,
            'best_reward': self.best_reward
        }

        if terminated or truncated:
            logger.info(f"Episode ended at step {self.current_step}, best reward: {self.best_reward:.2f}")

        return obs, reward, terminated, truncated, info

    def _apply_action(self, action: np.ndarray) -> None:
        """
        应用动作到参数

        Args:
            action: 动作数组
        """
        param_names = list(self.param_space.keys())

        for i, act in enumerate(action):
            param_name = param_names[i]
            param_info = self.param_space[param_name]

            if act == 1:  # 增加
                step_size = self._get_step_size(param_info)
                self.current_params[param_name] = min(
                    self.current_params[param_name] + step_size,
                    param_info.get('max', float('inf'))
                )
            elif act == 2:  # 减少
                step_size = self._get_step_size(param_info)
                self.current_params[param_name] = max(
                    self.current_params[param_name] - step_size,
                    param_info.get('min', 0)
                )
            # act == 0: 不变

    def _get_step_size(self, param_info: Dict[str, Any]) -> float:
        """获取参数调整步长"""
        param_min = param_info.get('min', 0)
        param_max = param_info.get('max', param_info.get('default', 100))
        return (param_max - param_min) * 0.1  # 10%步长

    def _get_observation(self) -> np.ndarray:
        """
        获取当前观测值

        Returns:
            观测数组 [性能指标, 参数值]
        """
        performance = self._get_performance(self.current_params)

        # 归一化参数值
        normalized_params = []
        param_names = list(self.param_space.keys())

        for name in param_names:
            param_info = self.param_space[name]
            value = self.current_params[name]
            min_val = param_info.get('min', 0)
            max_val = param_info.get('max', value)

            if max_val > min_val:
                normalized = (value - min_val) / (max_val - min_val)
            else:
                normalized = 0

            normalized_params.append(normalized)

        # 性能指标归一化（使用baseline作为参考）
        if self.baseline_performance:
            norm_performance = [
                performance.get('tpmc', 0) / max(self.baseline_performance.get('tpmc', 1), 1),
                self.baseline_performance.get('latency', 1) / max(performance.get('latency', 1), 1),
                1 - performance.get('cpu_usage', 0),  # 越小越好
                1 - performance.get('memory_usage', 0),  # 越小越好
                1 - performance.get('io_usage', 0)  # 越小越好
            ]
        else:
            norm_performance = [0.0] * self.performance_dim

        obs = np.array(norm_performance + normalized_params, dtype=np.float32)
        return obs

    def _get_performance(self, params: Dict[str, float]) -> Dict[str, float]:
        """
        获取指定参数配置下的性能指标

        Args:
            params: 参数配置

        Returns:
            性能指标字典
        """
        # 这里需要实际连接数据库或运行基准测试
        # 在实际实现中，这里会调用 benchmark_runner 或数据库查询

        # 模拟实现（实际使用时需要替换）
        if self.benchmark_runner is not None:
            # 运行实际基准测试
            result = self.benchmark_runner.run_with_params(params)
            return {
                'tpmc': result.get('tpmc', 0),
                'latency': result.get('latency', 1),
                'cpu_usage': result.get('cpu_usage', 0.5),
                'memory_usage': result.get('memory_usage', 0.5),
                'io_usage': result.get('io_usage', 0.5)
            }

        # 模拟性能函数（用于测试）
        # 性能与某些参数相关
        cache_size = params.get('block_cache_size', 2147483648)
        thread_count = params.get('net_thread_count', 4)

        # 简单的模拟函数
        tpmc = 1000 + (cache_size / 1073741824) * 100 + thread_count * 50
        latency = max(1, 10000 / tpmc)
        cpu_usage = 0.3 + (thread_count / 16) * 0.5
        memory_usage = min(1, (cache_size + 2147483648) / 8589934592)
        io_usage = 0.2 + (tpmc / 2000) * 0.3

        return {
            'tpmc': tpmc,
            'latency': latency,
            'cpu_usage': min(1, cpu_usage),
            'memory_usage': min(1, memory_usage),
            'io_usage': min(1, io_usage)
        }

    def _calculate_reward(self, performance: Dict[str, float]) -> float:
        """
        计算奖励

        Args:
            performance: 性能指标

        Returns:
            奖励值
        """
        if not self.baseline_performance:
            return 0.0

        tpmc_improvement = (performance['tpmc'] - self.baseline_performance['tpmc']) / max(self.baseline_performance['tpmc'], 1)
        latency_improvement = (self.baseline_performance['latency'] - performance['latency']) / max(self.baseline_performance['latency'], 1)

        if self.reward_mode == "tpmc":
            reward = tpmc_improvement * 100
        elif self.reward_mode == "latency":
            reward = latency_improvement * 100
        elif self.reward_mode == "throughput":
            reward = tpmc_improvement * 80 + latency_improvement * 20
        else:  # composite
            reward = (
                tpmc_improvement * 50 +
                latency_improvement * 30 +
                (1 - performance['cpu_usage']) * 10 +
                (1 - performance['memory_usage']) * 10
            ) * 100

        # 更新最佳奖励
        if reward > self.best_reward:
            self.best_reward = reward
            self.patience_counter = 0
        else:
            self.patience_counter += 1

        return reward

    def _check_termination(self) -> bool:
        """检查是否应该终止"""
        # 早停
        if self.patience_counter >= self.early_stop_patience:
            logger.info(f"Early stopping triggered at step {self.current_step}")
            return True

        return False

    def render(self, mode: str = 'human') -> None:
        """
        渲染环境

        Args:
            mode: 渲染模式
        """
        if mode == 'human':
            print(f"Step: {self.current_step}/{self.max_steps}")
            print(f"Current Params: {self.current_params}")
            if self.performance_history:
                perf = self.performance_history[-1]
                print(f"Performance: TPMC={perf.get('tpmc', 0):.1f}, "
                      f"Latency={perf.get('latency', 0):.2f}ms, "
                      f"CPU={perf.get('cpu_usage', 0):.1%}")
            print(f"Best Reward: {self.best_reward:.2f}")
            print("-" * 50)

    def close(self) -> None:
        """清理环境资源"""
        logger.info("Environment closed")

    def get_best_params(self) -> Dict[str, float]:
        """
        获取最佳参数配置

        Returns:
            最佳参数字典
        """
        return self.current_params

    def set_db_connector(self, connector) -> None:
        """
        设置数据库连接器

        Args:
            connector: 数据库连接器实例
        """
        self.db_connector = connector

    def set_benchmark_runner(self, runner) -> None:
        """
        设置基准测试运行器

        Args:
            runner: 基准测试运行器实例
        """
        self.benchmark_runner = runner

    def export_history(self) -> List[Dict[str, Any]]:
        """
        导出性能历史记录

        Returns:
            历史记录列表
        """
        return self.performance_history


class ParamActionSpace:
    """
    参数动作空间定义工具

    将参数空间转换为适合强化学习的动作表示
    """

    @staticmethod
    def continuous_to_discrete(param_info: Dict[str, Any],
                               n_bins: int = 5) -> spaces.Discrete:
        """
        将连续参数空间转换为离散动作空间

        Args:
            param_info: 参数信息
            n_bins: 离散化档位数

        Returns:
            离散动作空间
        """
        return spaces.Discrete(n_bins)

    @staticmethod
    def create_multi_discrete(param_space: Dict[str, Dict[str, Any]],
                             action_types: str = "tune") -> spaces.MultiDiscrete:
        """
        创建多重离散动作空间

        Args:
            param_space: 参数空间定义
            action_types: 动作类型 ("tune"=调参, "set"=设值)

        Returns:
            多重离散动作空间
        """
        n_params = len(param_space)

        if action_types == "tune":
            # 每个参数: 不变、增加、减少
            n_actions = 3
        else:  # set
            # 每个参数: 设为min、default、max
            n_actions = 3

        return spaces.MultiDiscrete([n_actions] * n_params)

    @staticmethod
    def create_box(param_space: Dict[str, Dict[str, Any]]) -> spaces.Box:
        """
        创建连续动作空间

        Args:
            param_space: 参数空间定义

        Returns:
            Box动作空间
        """
        n_params = len(param_space)
        return spaces.Box(low=-1, high=1, shape=(n_params,), dtype=np.float32)