# -*- coding: utf-8 -*-
"""
PatchTST-Lite：PatchTST 思路的轻量实现（无需 GPU / PyTorch）
==============================================================
参考论文《A Time Series is Worth 64 Words: Long-term Forecasting with
Transformers》(PatchTST) 的两个核心思想，用 numpy + sklearn 复刻：

  1) Channel Independence（通道独立）：每个监控指标单独建一个预测头。
  2) Patching（分块）：把输入窗口切成若干 patch，用每个 patch 的统计量
     (mean/std/min/max) + 原始点 作为特征，再接一个线性头（Ridge 回归）
     做多步直接预测（direct multi-step）。
  3) RevIN 风格实例归一化：对每个输入窗口做 (x-mean)/std，预测后再还原，
     缓解分布漂移。

这样既保留了 PatchTST 的建模直觉，又能在只装了 pandas/numpy/sklearn 的
机器上直接 `python` 跑起来。接口与 torch 版保持一致（fit / predict /
forecast_recursive），后续要换成真正的 PatchTST(torch) 只需替换本文件。
"""

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

SD_FLOOR = 0.25  # 局部标准差下限：Wu 的数据已全局 z-score，防止平坦窗口除以近零 std 而放大噪声


def _make_patches(window, patch_len, stride):
    """把一维窗口切成 patch，返回每个 patch 的统计特征拼接向量。"""
    feats = []
    i = 0
    n = len(window)
    while i + patch_len <= n:
        p = window[i:i + patch_len]
        feats.extend([p.mean(), p.std(), p.min(), p.max(), p[-1]])
        i += stride
    # 末尾不足一个 patch 的残余，用剩余点的统计补一个 patch
    if i < n:
        p = window[i:]
        feats.extend([p.mean(), p.std(), p.min(), p.max(), p[-1]])
    return np.asarray(feats, dtype=float)


class ChannelForecaster:
    """单通道（单指标）预测器：patching + RevIN + Ridge 多输出直接预测。"""

    def __init__(self, input_window, horizon, patch_len=12, stride=6, alpha=1.0,
                 instance_norm=False):
        self.L = input_window
        self.H = horizon
        self.patch_len = patch_len
        self.stride = stride
        # instance_norm=True 时启用 RevIN 风格逐窗归一化；
        # Wu 的输入已做全局 z-score，默认关闭，避免平坦窗口放大尖峰目标。
        self.instance_norm = instance_norm
        # 输入已全局 z-score（单位尺度），无需再 StandardScaler（否则平坦窗口里
        # 近零方差的 patch 统计特征会被放大导致预测发散）。直接用 Ridge 正则。
        self.alpha = alpha
        self.model = Ridge(alpha=alpha)
        self.resid_std = None  # 回测残差标准差，用于置信区间
        self.lo = None         # 递归预测的下界（防止发散）
        self.hi = None
        self.tr_mean = 0.0

    def _features(self, window):
        w = np.asarray(window, dtype=float)
        if self.instance_norm:
            mu, sd = w.mean(), max(w.std(), SD_FLOOR)
        else:
            mu, sd = 0.0, 1.0
        wn = (w - mu) / sd
        patch_feats = _make_patches(wn, self.patch_len, self.stride)
        # 特征 = 归一化原始点 + patch 统计特征
        return np.concatenate([wn, patch_feats]), mu, sd

    def _build_xy(self, series):
        X, Y = [], []
        n = len(series)
        for start in range(0, n - self.L - self.H + 1):
            win = series[start:start + self.L]
            tgt = series[start + self.L:start + self.L + self.H]
            feat, mu, sd = self._features(win)
            X.append(feat)
            Y.append((np.asarray(tgt, dtype=float) - mu) / sd)  # 归一化目标
        return np.asarray(X), np.asarray(Y)

    def fit(self, series):
        X, Y = self._build_xy(series)
        if len(X) == 0:
            raise ValueError("训练样本不足：序列长度 < input_window + horizon")
        self.model.fit(X, Y)
        # 记录训练分布，用于递归预测时钳制，避免长程递归发散
        s = np.asarray(series, dtype=float)
        rng = float(s.max() - s.min()) or 1.0
        self.lo = float(s.min()) - 0.5 * rng
        self.hi = float(s.max()) + 0.5 * rng
        self.tr_mean = float(s.mean())
        return self

    def predict_next(self, window):
        """给定一个长度 L 的窗口，预测未来 H 步（已还原到原尺度）。"""
        feat, mu, sd = self._features(window)
        yn = self.model.predict(feat.reshape(1, -1))[0]
        pred = yn * sd + mu
        # 非有限值兜底 + 钳制到训练分布附近，保证长程递归稳定
        pred = np.nan_to_num(pred, nan=self.tr_mean, posinf=self.hi, neginf=self.lo)
        if self.lo is not None:
            pred = np.clip(pred, self.lo, self.hi)
        return pred

    def forecast_recursive(self, last_window, n_steps):
        """递归多步预测：每次预测 H 步，取第一批向前滚动，直到凑够 n_steps。"""
        win = list(np.asarray(last_window, dtype=float))
        out = []
        while len(out) < n_steps:
            pred = self.predict_next(win[-self.L:])
            take = min(self.H, n_steps - len(out))
            out.extend(pred[:take].tolist())
            win.extend(pred[:take].tolist())
        return np.asarray(out[:n_steps])

    def backtest(self, series, n_folds=3):
        """walk-forward 回测，返回 (rmse, mae)，并记录残差标准差。"""
        X, Y = self._build_xy(series)
        if len(X) < n_folds + 1:
            # 样本太少，退化为留一部分做验证
            n_folds = max(1, len(X) // 2)
        fold = max(1, len(X) // (n_folds + 1))
        errs = []
        resid = []
        for k in range(1, n_folds + 1):
            split = fold * k
            if split >= len(X):
                break
            m = Ridge(alpha=self.alpha)
            m.fit(X[:split], Y[:split])
            pred = m.predict(X[split:split + fold])
            true = Y[split:split + fold]
            if len(true) == 0:
                continue
            e = pred - true
            resid.append(e.ravel())
            errs.append((np.sqrt((e ** 2).mean()), np.abs(e).mean()))
        if not errs:
            self.resid_std = float(np.std(Y)) if len(Y) else 1.0
            return float("nan"), float("nan")
        rmse = float(np.mean([e[0] for e in errs]))
        mae = float(np.mean([e[1] for e in errs]))
        self.resid_std = float(np.std(np.concatenate(resid)))
        return rmse, mae
