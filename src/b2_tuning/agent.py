"""
强化学习Agent

基于Stable-Baselines3实现的离线强化学习Agent，用于OceanBase参数调优。
"""

from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from pathlib import Path
import json
from dataclasses import dataclass, asdict
from loguru import logger
import mlflow
import mlflow.pytorch

try:
    import torch
    from stable_baselines3 import (
        PPO, DQN, SAC, TD3, A2C,
        DDPG, HER, TQC
    )
    from stable_baselines3.common.callbacks import (
        BaseCallback, EvalCallback,
        StopTrainingOnRewardThreshold,
        CheckpointCallback
    )
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    logger.warning("Stable-Baselines3 not available")


@dataclass
class AgentConfig:
    """Agent配置"""
    algorithm: str = "ppo"
    learning_rate: float = 3e-4
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.01
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    use_sde: bool = False
    sde_sample_freq: int = -1
    target_kl: float = 0.01
    tensorboard_log: Optional[str] = None
    policy: str = "MlpPolicy"
    verbose: int = 1


class MLflowCallback(BaseCallback):
    """MLflow记录回调"""

    def __init__(self, experiment_name: str = "ob_tuning"):
        super().__init__()
        self.experiment_name = experiment_name

    def _on_training_start(self) -> None:
        mlflow.set_experiment(self.experiment_name)
        mlflow.start_run()

    def _on_step(self) -> bool:
        # 记录当前步的指标
        if len(self.locals) > 0 and 'rewards' in self.locals:
            mlflow.log_metrics({
                'reward': np.mean(self.locals.get('rewards', [0])),
            }, step=self.num_timesteps)
        return True

    def _on_training_end(self) -> None:
        mlflow.end_run()


class RewardThresholdCallback(BaseCallback):
    """奖励阈值回调"""

    def __init__(self, threshold: float, patience: int = 5):
        super().__init__()
        self.threshold = threshold
        self.patience = patience
        self.patience_counter = 0
        self.best_mean_reward = -np.inf

    def _on_step(self) -> bool:
        if len(self.training_env.get_attr('performance_history')[0]) > 0:
            current_reward = np.mean(self.episode_rewards[-100:]) if len(self.episode_rewards) > 0 else 0

            if current_reward > self.best_mean_reward:
                self.best_mean_reward = current_reward
                self.patience_counter = 0
            else:
                self.patience_counter += 1

            logger.info(f"Current reward: {current_reward:.2f}, Best: {self.best_mean_reward:.2f}")

            if self.patience_counter >= self.patience and self.best_mean_reward >= self.threshold:
                logger.info(f"Reward threshold reached: {self.best_mean_reward:.2f}")
                return False  # 停止训练

        return True


class RLAgent:
    """
    OceanBase参数调优强化学习Agent
    """

    ALGORITHMS = {
        'ppo': PPO,
        'dqn': DQN,
        'sac': SAC,
        'td3': TD3,
        'a2c': A2C,
        'ddpg': DDPG,
        'tqc': TQC,
    }

    def __init__(self, env, config: Optional[AgentConfig] = None):
        """
        初始化Agent

        Args:
            env: Gym环境
            config: Agent配置
        """
        if not SB3_AVAILABLE:
            raise ImportError("Stable-Baselines3 is not installed")

        self.env = env
        self.config = config or AgentConfig()
        self.model = None
        self.training_log = []

        # 环境包装
        self._wrap_env()

    def _wrap_env(self) -> None:
        """包装环境"""
        self.wrapped_env = Monitor(self.env)
        self.wrapped_env = DummyVecEnv([lambda: self.wrapped_env])
        self.wrapped_env = VecNormalize(self.wrapped_env, norm_obs=True, norm_reward=True)

    def build_model(self) -> None:
        """构建模型"""
        algo_class = self.ALGORITHMS.get(self.config.algorithm)

        if algo_class is None:
            raise ValueError(f"Unknown algorithm: {self.config.algorithm}. "
                           f"Available: {list(self.ALGORITHMS.keys())}")

        # 根据算法类型设置参数
        policy_kwargs = {
            'net_arch': [256, 256],
            'activation_fn': torch.nn.ReLU,
        }

        common_params = {
            'policy': self.config.policy,
            'env': self.wrapped_env,
            'learning_rate': self.config.learning_rate,
            'tensorboard_log': self.config.tensorboard_log,
            'verbose': self.config.verbose,
            'policy_kwargs': policy_kwargs,
        }

        # 算法特定参数
        if self.config.algorithm in ['ppo', 'a2c']:
            common_params.update({
                'n_steps': self.config.n_steps,
                'gamma': self.config.gamma,
                'gae_lambda': self.config.gae_lambda,
                'ent_coef': self.config.ent_coef,
                'vf_coef': self.config.vf_coef,
                'max_grad_norm': self.config.max_grad_norm,
                'use_sde': self.config.use_sde,
                'sde_sample_freq': self.config.sde_sample_freq,
            })

            if self.config.algorithm == 'ppo':
                common_params.update({
                    'batch_size': self.config.batch_size,
                    'n_epochs': self.config.n_epochs,
                    'clip_range': self.config.clip_range,
                    'target_kl': self.config.target_kl,
                })

        elif self.config.algorithm == 'dqn':
            common_params.update({
                'batch_size': self.config.batch_size,
                'gamma': self.config.gamma,
                'learning_starts': 1000,
                'buffer_size': 50000,
            })

        elif self.config.algorithm in ['sac', 'td3', 'tqc', 'ddpg']:
            common_params.update({
                'batch_size': self.config.batch_size,
                'gamma': self.config.gamma,
                'learning_starts': 1000,
                'buffer_size': 100000,
                'train_freq': 1,
                'gradient_steps': 1,
            })

        self.model = algo_class(**common_params)
        logger.info(f"Built {self.config.algorithm.upper()} model")

    def train(self, total_timesteps: int, callbacks: Optional[List[BaseCallback]] = None,
              use_mlflow: bool = True) -> None:
        """
        训练模型

        Args:
            total_timesteps: 总训练步数
            callbacks: 回调列表
            use_mlflow: 是否使用MLflow记录
        """
        if self.model is None:
            self.build_model()

        # 准备回调
        all_callbacks = []

        if use_mlflow:
            all_callbacks.append(MLflowCallback(experiment_name="ob_tuning"))

        if callbacks:
            all_callbacks.extend(callbacks)

        logger.info(f"Starting training for {total_timesteps} timesteps...")

        self.model.learn(
            total_timesteps=total_timesteps,
            callback=all_callbacks if all_callbacks else None
        )

        logger.info("Training completed")

    def predict(self, observation: np.ndarray,
                deterministic: bool = True) -> Tuple[np.ndarray, Any]:
        """
        预测动作

        Args:
            observation: 观测值
            deterministic: 是否确定性预测

        Returns:
            动作和状态
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        observation = self.wrapped_env.normalize_obs(observation)
        action, state = self.model.predict(observation, deterministic=deterministic)
        return action, state

    def evaluate(self, n_episodes: int = 10) -> Dict[str, float]:
        """
        评估模型

        Args:
            n_episodes: 评估回合数

        Returns:
            评估指标字典
        """
        episode_rewards = []
        episode_lengths = []

        for _ in range(n_episodes):
            obs, _ = self.env.reset()
            done = False
            episode_reward = 0
            episode_length = 0

            while not done:
                action, _ = self.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = self.env.step(action)
                done = terminated or truncated
                episode_reward += reward
                episode_length += 1

            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)

        return {
            'mean_reward': np.mean(episode_rewards),
            'std_reward': np.std(episode_rewards),
            'max_reward': np.max(episode_rewards),
            'min_reward': np.min(episode_rewards),
            'mean_length': np.mean(episode_lengths),
        }

    def save(self, path: str) -> None:
        """
        保存模型

        Args:
            path: 保存路径
        """
        if self.model is None:
            raise RuntimeError("No model to save")

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.model.save(path)

        # 保存环境归一化统计
        self.wrapped_env.save(str(Path(path).parent / "vec_normalize.pkl"))

        # 保存配置
        config_path = Path(path).parent / "agent_config.json"
        with open(config_path, 'w') as f:
            json.dump(asdict(self.config), f, indent=2)

        logger.info(f"Model saved to {path}")

    def load(self, path: str) -> None:
        """
        加载模型

        Args:
            path: 模型路径
        """
        algo_class = self.ALGORITHMS.get(self.config.algorithm)
        if algo_class is None:
            raise ValueError(f"Unknown algorithm: {self.config.algorithm}")

        self.model = algo_class.load(path)
        self.wrapped_env = VecNormalize.load(
            str(Path(path).parent / "vec_normalize.pkl"),
            self.wrapped_env
        )

        logger.info(f"Model loaded from {path}")

    def export_best_params(self) -> Dict[str, float]:
        """
        导出最佳参数配置

        Returns:
            最佳参数字典
        """
        return self.env.get_best_params()

    def tune_hyperparameters(self, trial, env_config: Dict) -> float:
        """
        使用Optuna进行超参数调优

        Args:
            trial: Optuna trial对象
            env_config: 环境配置

        Returns:
            平均奖励
        """
        # 定义搜索空间
        learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-3, log=True)
        batch_size = trial.suggest_categorical('batch_size', [32, 64, 128, 256])
        n_epochs = trial.suggest_int('n_epochs', 5, 20)
        gamma = trial.suggest_float('gamma', 0.9, 0.999)

        # 更新配置
        self.config.learning_rate = learning_rate
        self.config.batch_size = batch_size
        self.config.n_epochs = n_epochs
        self.config.gamma = gamma

        # 重新构建并训练
        self.build_model()
        self.model.learn(total_timesteps=10000)

        # 评估
        eval_results = self.evaluate(n_episodes=5)
        return eval_results['mean_reward']


class OfflineRLAgent:
    """
    离线强化学习Agent

    使用历史数据进行离线训练，支持 Conservative Q-Learning (CQL)
    和其他离线RL算法。
    """

    def __init__(self, dataset_path: str):
        """
        初始化离线Agent

        Args:
            dataset_path: 历史数据集路径
        """
        self.dataset_path = Path(dataset_path)
        self.dataset = None
        self.model = None

    def load_dataset(self) -> None:
        """加载离线数据集"""
        try:
            import pandas as pd
            self.dataset = pd.read_csv(self.dataset_path)
            logger.info(f"Loaded offline dataset: {len(self.dataset)} transitions")
        except Exception as e:
            logger.error(f"Failed to load dataset: {e}")
            raise

    def create_offline_buffer(self) -> None:
        """创建离线经验回放缓冲区"""
        if self.dataset is None:
            self.load_dataset()

        # 将DataFrame转换为适合RL的数据格式
        # 这里需要根据具体数据结构实现
        pass

    def train_cql(self, total_timesteps: int) -> None:
        """
        使用CQL算法训练

        Args:
            total_timesteps: 训练步数
        """
        # 这里可以实现CQL算法
        # 或者使用现有的库如 d3rlpy
        pass

    def train_bcq(self, total_timesteps: int) -> None:
        """
        使用BCQ算法训练

        Args:
            total_timesteps: 训练步数
        """
        # 这里可以实现BCQ算法
        pass


class EnsembleAgent:
    """
    集成Agent

    结合多个Agent进行决策投票或平均
    """

    def __init__(self, agents: List[RLAgent]):
        """
        初始化集成Agent

        Args:
            agents: Agent列表
        """
        self.agents = agents

    def predict(self, observation: np.ndarray,
                method: str = "vote") -> Tuple[np.ndarray, Any]:
        """
        预测动作

        Args:
            observation: 观测值
            method: 集成方法 ("vote", "average", "weighted")

        Returns:
            动作和状态
        """
        actions = []
        weights = []

        for agent in self.agents:
            action, _ = agent.predict(observation, deterministic=True)
            actions.append(action)
            # 可以使用Agent的性能作为权重
            weights.append(1.0)

        actions = np.array(actions)

        if method == "vote":
            # 投票：选择最常见的动作
            from scipy.stats import mode
            final_action = mode(actions, axis=0, keepdims=True).mode[0]
        elif method == "average":
            # 平均
            final_action = np.mean(actions, axis=0)
        else:  # weighted
            # 加权平均
            weights = np.array(weights).reshape(-1, 1)
            final_action = np.average(actions, axis=0, weights=weights.flatten())

        return final_action.astype(np.int32), None