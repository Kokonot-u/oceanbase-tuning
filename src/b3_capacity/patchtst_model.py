"""
PatchTST时序预测模型

实现PatchTST（Patch Time Series Transformer）用于OceanBase资源预测。
"""

from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from loguru import logger

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    logger.warning("PyTorch not available")

try:
    from darts import TimeSeries
    from darts.models import NBEATSModel, TCNModel, TransformerModel
    from darts.dataprocessing.transformers import Scaler
    from darts.metrics import mae, mse, mape
    DARTS_AVAILABLE = True
except ImportError:
    DARTS_AVAILABLE = False
    logger.warning("Darts not available")


@dataclass
class ModelConfig:
    """模型配置"""
    input_len: int = 96  # 输入序列长度
    output_len: int = 24  # 输出预测长度
    patch_len: int = 16  # Patch长度
    stride: int = 8  # Patch步长
    n_layers: int = 3  # Transformer层数
    n_heads: int = 4  # 注意力头数
    d_model: int = 128  # 模型维度
    d_ff: int = 512  # 前馈网络维度
    dropout: float = 0.1  # Dropout率
    batch_size: int = 32
    learning_rate: float = 1e-4
    epochs: int = 100
    early_stopping_patience: int = 10


class PatchTSTDataset(Dataset):
    """PatchTST数据集"""

    def __init__(self, data: np.ndarray, input_len: int, output_len: int):
        """
        初始化数据集

        Args:
            data: 时序数据 (n_samples, n_features)
            input_len: 输入长度
            output_len: 输出长度
        """
        self.data = torch.FloatTensor(data)
        self.input_len = input_len
        self.output_len = output_len

    def __len__(self) -> int:
        return len(self.data) - self.input_len - self.output_len

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        获取样本

        Returns:
            (输入序列, 输出序列)
        """
        x = self.data[idx:idx + self.input_len]
        y = self.data[idx + self.input_len:idx + self.input_len + self.output_len]
        return x, y


class PatchEmbedding(nn.Module):
    """Patch嵌入层"""

    def __init__(self, patch_len: int, stride: int, d_model: int):
        super().__init__()
        self.patch_len = patch_len
        self.stride = stride

        self.patch_embedding = nn.Linear(patch_len, d_model)
        self.dropout = nn.Dropout(0.1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, seq_len, n_features)

        Returns:
            (batch_size, n_patches, d_model)
        """
        batch_size, seq_len, n_features = x.shape

        # 重塑为patches: (batch_size * n_features, n_patches, patch_len)
        x = x.transpose(1, 2)  # (batch_size, n_features, seq_len)
        x = x.unfold(dimension=2, size=self.patch_len, step=self.stride)  # (batch_size, n_features, n_patches, patch_len)
        x = x.permute(0, 2, 3, 1)  # (batch_size, n_patches, patch_len, n_features)
        x = x.reshape(batch_size, -1, self.patch_len)  # 合并features

        # Patch embedding
        x = self.patch_embedding(x)
        x = self.dropout(x)

        return x


class PositionalEncoding(nn.Module):
    """位置编码"""

    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))

        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)

        self.register_buffer('pe', pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, seq_len, d_model)

        Returns:
            (batch_size, seq_len, d_model)
        """
        return x + self.pe[:, :x.size(1), :]


class PatchTST(nn.Module):
    """
    PatchTST模型

    基于Patch化的时序Transformer模型
    """

    def __init__(self, config: ModelConfig, n_features: int):
        super().__init__()

        self.config = config
        self.n_features = n_features

        # Patch embedding
        self.patch_embedding = PatchEmbedding(
            patch_len=config.patch_len,
            stride=config.stride,
            d_model=config.d_model
        )

        # Positional encoding
        self.pos_encoding = PositionalEncoding(config.d_model)

        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.n_heads,
            dim_feedforward=config.d_ff,
            dropout=config.dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.n_layers
        )

        # Projection head
        self.fc = nn.Sequential(
            nn.Linear(config.d_model, config.d_ff),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.d_ff, n_features)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch_size, input_len, n_features)

        Returns:
            (batch_size, output_len, n_features)
        """
        batch_size, _, _ = x.shape

        # Patch embedding
        x = self.patch_embedding(x)  # (batch_size, n_patches, d_model)

        # Positional encoding
        x = self.pos_encoding(x)

        # Transformer encoding
        x = self.transformer(x)

        # Global pooling
        x = x.mean(dim=1)  # (batch_size, d_model)

        # Projection to output
        output = self.fc(x)  # (batch_size, n_features)

        # 扩展到输出长度
        output = output.unsqueeze(1).repeat(1, self.config.output_len, 1)

        return output


class PatchTSTModel:
    """
    PatchTST模型包装器

    提供训练、预测和评估功能
    """

    def __init__(self, config: Optional[ModelConfig] = None):
        """
        初始化模型

        Args:
            config: 模型配置
        """
        if not PYTORCH_AVAILABLE:
            raise ImportError("PyTorch is required for PatchTSTModel")

        self.config = config or ModelConfig()
        self.model = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.scaler = None
        self.feature_names = []

    def prepare_data(self, data: pd.DataFrame, target_columns: List[str],
                     timestamp_column: str = 'timestamp') -> Tuple[np.ndarray, np.ndarray]:
        """
        准备训练数据

        Args:
            data: 原始数据
            target_columns: 目标列名
            timestamp_column: 时间戳列名

        Returns:
            (特征, 目标)
        """
        self.feature_names = target_columns

        # 确保数据按时间排序
        data = data.sort_values(timestamp_column).reset_index(drop=True)

        # 提取目标变量
        targets = data[target_columns].values

        # 简单归一化 (实际应用中应使用更复杂的scaler)
        self.scaler = {
            'mean': targets.mean(axis=0),
            'std': targets.std(axis=0) + 1e-6
        }
        targets_normalized = (targets - self.scaler['mean']) / self.scaler['std']

        return targets_normalized, targets_normalized

    def build_model(self, n_features: int) -> None:
        """构建模型"""
        self.model = PatchTST(self.config, n_features).to(self.device)
        logger.info(f"Built PatchTST model with {sum(p.numel() for p in self.model.parameters())} parameters")

    def train(self, data: pd.DataFrame, target_columns: List[str],
              validation_split: float = 0.2) -> Dict[str, float]:
        """
        训练模型

        Args:
            data: 训练数据
            target_columns: 目标列名
            validation_split: 验证集比例

        Returns:
            训练历史
        """
        # 准备数据
        x, _ = self.prepare_data(data, target_columns)

        # 划分训练集和验证集
        split_idx = int(len(x) * (1 - validation_split))
        train_data = x[:split_idx]
        val_data = x[split_idx:]

        # 创建数据集
        train_dataset = PatchTSTDataset(train_data, self.config.input_len, self.config.output_len)
        val_dataset = PatchTSTDataset(val_data, self.config.input_len, self.config.output_len)

        # 创建数据加载器
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=0
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.batch_size,
            shuffle=False,
            num_workers=0
        )

        # 构建模型
        self.build_model(len(target_columns))

        # 优化器和损失函数
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate)
        criterion = nn.MSELoss()

        # 训练循环
        best_val_loss = float('inf')
        patience_counter = 0
        history = {'train_loss': [], 'val_loss': []}

        for epoch in range(self.config.epochs):
            # 训练
            self.model.train()
            train_loss = 0

            for batch_x, batch_y in train_loader:
                batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)

                optimizer.zero_grad()
                output = self.model(batch_x)
                loss = criterion(output, batch_y)
                loss.backward()

                # 梯度裁剪
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)

                optimizer.step()

                train_loss += loss.item()

            train_loss /= len(train_loader)

            # 验证
            self.model.eval()
            val_loss = 0

            with torch.no_grad():
                for batch_x, batch_y in val_loader:
                    batch_x, batch_y = batch_x.to(self.device), batch_y.to(self.device)
                    output = self.model(batch_x)
                    loss = criterion(output, batch_y)
                    val_loss += loss.item()

            val_loss /= len(val_loader)

            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)

            logger.info(f"Epoch {epoch+1}/{self.config.epochs} - Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}")

            # 早停
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self.save_best_state()
            else:
                patience_counter += 1

            if patience_counter >= self.config.early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch+1}")
                break

        logger.info(f"Training completed. Best val loss: {best_val_loss:.6f}")
        return history

    def predict(self, data: pd.DataFrame, target_columns: List[str],
                n_steps: int = 24) -> np.ndarray:
        """
        预测未来资源使用

        Args:
            data: 历史数据
            target_columns: 目标列名
            n_steps: 预测步数

        Returns:
            预测结果 (n_steps, n_features)
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        self.model.eval()

        # 准备输入数据
        x, _ = self.prepare_data(data, target_columns)

        # 取最后input_len个点作为输入
        input_data = torch.FloatTensor(x[-self.config.input_len:]).unsqueeze(0).to(self.device)

        with torch.no_grad():
            # 预测
            output = self.model(input_data)  # (1, output_len, n_features)
            output = output.squeeze(0).cpu().numpy()

        # 反归一化
        output = output * self.scaler['std'] + self.scaler['mean']

        # 取前n_steps
        return output[:n_steps]

    def save(self, path: str) -> None:
        """
        保存模型

        Args:
            path: 保存路径
        """
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        save_dict = {
            'model_state_dict': self.model.state_dict(),
            'config': self.config,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
        }

        torch.save(save_dict, path)
        logger.info(f"Model saved to {path}")

    def load(self, path: str) -> None:
        """
        加载模型

        Args:
            path: 模型路径
        """
        save_dict = torch.load(path, map_location=self.device)

        self.config = save_dict['config']
        self.scaler = save_dict['scaler']
        self.feature_names = save_dict['feature_names']

        self.build_model(len(self.feature_names))
        self.model.load_state_dict(save_dict['model_state_dict'])

        logger.info(f"Model loaded from {path}")

    def save_best_state(self) -> None:
        """保存最佳模型状态（内部使用）"""
        self.best_state = self.model.state_dict()

    def load_best_state(self) -> None:
        """加载最佳模型状态"""
        if hasattr(self, 'best_state'):
            self.model.load_state_dict(self.best_state)


class EnsembleForecaster:
    """
    集成预测器

    结合多个模型的预测结果
    """

    def __init__(self, models: List[PatchTSTModel]):
        """
        初始化集成预测器

        Args:
            models: 模型列表
        """
        self.models = models

    def predict(self, data: pd.DataFrame, target_columns: List[str],
                n_steps: int = 24, method: str = 'average') -> np.ndarray:
        """
        集成预测

        Args:
            data: 历史数据
            target_columns: 目标列名
            n_steps: 预测步数
            method: 集成方法 ("average", "weighted", "voting")

        Returns:
            预测结果
        """
        predictions = []

        for model in self.models:
            pred = model.predict(data, target_columns, n_steps)
            predictions.append(pred)

        predictions = np.array(predictions)

        if method == 'average':
            return predictions.mean(axis=0)
        elif method == 'weighted':
            weights = np.ones(len(self.models)) / len(self.models)
            return np.average(predictions, axis=0, weights=weights)
        else:  # voting
            # 对于分类问题可以使用投票，这里使用中位数
            return np.median(predictions, axis=0)


def create_forecaster_from_darts(data: pd.DataFrame, target_column: str,
                                  model_type: str = 'transformer') -> Any:
    """
    使用Darts库创建预测模型

    Args:
        data: 时序数据
        target_column: 目标列
        model_type: 模型类型

    Returns:
        Darts模型实例
    """
    if not DARTS_AVAILABLE:
        raise ImportError("Darts is required")

    # 创建TimeSeries
    series = TimeSeries.from_dataframe(data, time_col='timestamp', value_cols=target_column)

    # 归一化
    scaler = Scaler()
    series_scaled = scaler.fit_transform(series)

    # 创建模型
    if model_type == 'nbeats':
        model = NBEATSModel(
            input_chunk_length=96,
            output_chunk_length=24,
            n_epochs=100,
            random_state=42
        )
    elif model_type == 'tcn':
        model = TCNModel(
            input_chunk_length=96,
            output_chunk_length=24,
            n_epochs=100,
            random_state=42
        )
    else:  # transformer
        model = TransformerModel(
            input_chunk_length=96,
            output_chunk_length=24,
            d_model=64,
            nhead=4,
            num_encoder_layers=3,
            num_decoder_layers=3,
            n_epochs=100,
            random_state=42
        )

    model.fit(series_scaled)

    return {'model': model, 'scaler': scaler}