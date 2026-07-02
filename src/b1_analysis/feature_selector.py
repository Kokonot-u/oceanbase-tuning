"""
特征选择器

使用Scikit-learn和XGBoost进行特征选择，用于OceanBase性能分析。
"""

from typing import List, Tuple, Optional, Dict, Any
import numpy as np
import pandas as pd
from sklearn.feature_selection import (
    SelectKBest, f_regression, f_classif,
    mutual_info_regression, mutual_info_classif,
    RFE, VarianceThreshold
)
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from loguru import logger


class FeatureSelector:
    """特征选择器"""

    def __init__(self, task_type: str = "regression", random_state: int = 42):
        """
        初始化特征选择器

        Args:
            task_type: 任务类型，"regression" 或 "classification"
            random_state: 随机种子
        """
        self.task_type = task_type
        self.random_state = random_state
        self.selected_features: Optional[List[str]] = None
        self.feature_importance: Optional[pd.DataFrame] = None
        self.scores: Optional[Dict[str, float]] = None

    def select_by_importance(self, X: pd.DataFrame, y: pd.Series,
                           n_features: int, method: str = "xgboost") -> List[str]:
        """
        基于特征重要性选择特征

        Args:
            X: 特征矩阵
            y: 目标变量
            n_features: 选择特征数量
            method: 模型类型 ("xgboost", "rf", "lgb")

        Returns:
            选择的特征名称列表
        """
        logger.info(f"Selecting {n_features} features by importance using {method}")

        if method == "xgboost":
            return self._select_by_xgboost(X, y, n_features)
        elif method == "rf":
            return self._select_by_random_forest(X, y, n_features)
        elif method == "lgb":
            return self._select_by_lightgbm(X, y, n_features)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _select_by_xgboost(self, X: pd.DataFrame, y: pd.Series,
                          n_features: int) -> List[str]:
        """使用XGBoost进行特征选择"""
        if self.task_type == "regression":
            model = xgb.XGBRegressor(
                n_estimators=100,
                random_state=self.random_state,
                eval_metric='rmse'
            )
        else:
            model = xgb.XGBClassifier(
                n_estimators=100,
                random_state=self.random_state,
                eval_metric='logloss'
            )

        model.fit(X, y)
        importance = model.feature_importances_

        self.feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': importance
        }).sort_values('importance', ascending=False)

        self.selected_features = self.feature_importance['feature'].head(n_features).tolist()
        return self.selected_features

    def _select_by_random_forest(self, X: pd.DataFrame, y: pd.Series,
                                 n_features: int) -> List[str]:
        """使用随机森林进行特征选择"""
        if self.task_type == "regression":
            model = RandomForestRegressor(
                n_estimators=100,
                random_state=self.random_state
            )
        else:
            model = RandomForestClassifier(
                n_estimators=100,
                random_state=self.random_state
            )

        model.fit(X, y)
        importance = model.feature_importances_

        self.feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': importance
        }).sort_values('importance', ascending=False)

        self.selected_features = self.feature_importance['feature'].head(n_features).tolist()
        return self.selected_features

    def _select_by_lightgbm(self, X: pd.DataFrame, y: pd.Series,
                           n_features: int) -> List[str]:
        """使用LightGBM进行特征选择"""
        try:
            import lightgbm as lgb

            if self.task_type == "regression":
                model = lgb.LGBMRegressor(
                    n_estimators=100,
                    random_state=self.random_state,
                    verbose=-1
                )
            else:
                model = lgb.LGBMClassifier(
                    n_estimators=100,
                    random_state=self.random_state,
                    verbose=-1
                )

            model.fit(X, y)
            importance = model.feature_importances_

            self.feature_importance = pd.DataFrame({
                'feature': X.columns,
                'importance': importance
            }).sort_values('importance', ascending=False)

            self.selected_features = self.feature_importance['feature'].head(n_features).tolist()
            return self.selected_features

        except ImportError:
            logger.warning("LightGBM not available, falling back to XGBoost")
            return self._select_by_xgboost(X, y, n_features)

    def select_by_statistical(self, X: pd.DataFrame, y: pd.Series,
                              n_features: int, method: str = "f_score") -> List[str]:
        """
        基于统计测试选择特征

        Args:
            X: 特征矩阵
            y: 目标变量
            n_features: 选择特征数量
            method: 统计方法 ("f_score", "mutual_info")

        Returns:
            选择的特征名称列表
        """
        logger.info(f"Selecting {n_features} features by {method}")

        if method == "f_score":
            if self.task_type == "regression":
                score_func = f_regression
            else:
                score_func = f_classif
        elif method == "mutual_info":
            if self.task_type == "regression":
                score_func = mutual_info_regression
            else:
                score_func = mutual_info_classif
        else:
            raise ValueError(f"Unknown method: {method}")

        selector = SelectKBest(score_func=score_func, k=n_features)
        selector.fit(X, y)

        self.scores = dict(zip(X.columns, selector.scores_))
        scores_df = pd.DataFrame({
            'feature': X.columns,
            'score': selector.scores_
        }).sort_values('score', ascending=False)

        self.selected_features = scores_df['feature'].head(n_features).tolist()
        return self.selected_features

    def select_by_rfe(self, X: pd.DataFrame, y: pd.Series,
                     n_features: int, estimator: Optional[Any] = None) -> List[str]:
        """
        使用递归特征消除（RFE）选择特征

        Args:
            X: 特征矩阵
            y: 目标变量
            n_features: 选择特征数量
            estimator: 基础估计器，默认使用随机森林

        Returns:
            选择的特征名称列表
        """
        logger.info(f"Selecting {n_features} features using RFE")

        if estimator is None:
            if self.task_type == "regression":
                estimator = RandomForestRegressor(n_estimators=50, random_state=self.random_state)
            else:
                estimator = RandomForestClassifier(n_estimators=50, random_state=self.random_state)

        selector = RFE(estimator=estimator, n_features_to_select=n_features)
        selector.fit(X, y)

        self.selected_features = X.columns[selector.support_].tolist()
        return self.selected_features

    def remove_low_variance(self, X: pd.DataFrame, threshold: float = 0.0) -> Tuple[pd.DataFrame, List[str]]:
        """
        移除低方差特征

        Args:
            X: 特征矩阵
            threshold: 方差阈值

        Returns:
            过滤后的特征矩阵和保留的特征名
        """
        selector = VarianceThreshold(threshold=threshold)
        selector.fit(X)

        retained_features = X.columns[selector.get_support()].tolist()
        filtered_X = X[retained_features]

        logger.info(f"Removed {len(X.columns) - len(retained_features)} low variance features")
        return filtered_X, retained_features

    def remove_correlated(self, X: pd.DataFrame, threshold: float = 0.95) -> Tuple[pd.DataFrame, List[str]]:
        """
        移除高度相关的特征

        Args:
            X: 特征矩阵
            threshold: 相关系数阈值

        Returns:
            过滤后的特征矩阵和保留的特征名
        """
        corr_matrix = X.corr().abs()
        upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

        to_drop = [col for col in upper_tri.columns if any(upper_tri[col] > threshold)]
        retained_features = [col for col in X.columns if col not in to_drop]
        filtered_X = X[retained_features]

        logger.info(f"Removed {len(to_drop)} highly correlated features")
        return filtered_X, retained_features

    def comprehensive_selection(self, X: pd.DataFrame, y: pd.Series,
                               n_features: int = 50) -> List[str]:
        """
        综合特征选择流程：
        1. 移除低方差特征
        2. 移除高度相关特征
        3. 使用XGBoost重要性选择

        Args:
            X: 特征矩阵
            y: 目标变量
            n_features: 最终选择的特征数量

        Returns:
            选择的特征名称列表
        """
        logger.info("Starting comprehensive feature selection")

        # 1. 移除低方差
        X_filtered, _ = self.remove_low_variance(X, threshold=0.01)

        # 2. 移除高度相关特征
        X_filtered, _ = self.remove_correlated(X_filtered, threshold=0.95)

        # 3. 基于重要性选择
        selected = self.select_by_importance(
            X_filtered, y,
            min(n_features, len(X_filtered.columns)),
            method="xgboost"
        )

        logger.info(f"Selected {len(selected)} features out of {len(X.columns)}")
        return selected

    def shap_analysis(self, X: pd.DataFrame, model: Any,
                     max_features: int = 20) -> pd.DataFrame:
        """
        使用SHAP分析特征重要性

        Args:
            X: 特征矩阵
            model: 已训练的模型
            max_features: 显示的最大特征数

        Returns:
            SHAP值DataFrame
        """
        try:
            import shap

            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)

            # 计算平均绝对SHAP值
            mean_shap = np.abs(shap_values).mean(axis=0)

            shap_df = pd.DataFrame({
                'feature': X.columns,
                'shap_value': mean_shap
            }).sort_values('shap_value', ascending=False)

            logger.info(f"SHAP analysis completed, top feature: {shap_df.iloc[0]['feature']}")
            return shap_df.head(max_features)

        except ImportError:
            logger.warning("SHAP not available")
            return pd.DataFrame()

    def get_top_features(self, n: int = 10) -> List[str]:
        """
        获取最重要的特征

        Args:
            n: 返回特征数量

        Returns:
            特征名称列表
        """
        if self.feature_importance is not None:
            return self.feature_importance['feature'].head(n).tolist()
        elif self.scores is not None:
            return sorted(self.scores, key=self.scores.get, reverse=True)[:n]
        else:
            return []

    def plot_importance(self, save_path: Optional[str] = None) -> None:
        """
        绘制特征重要性图

        Args:
            save_path: 保存路径
        """
        import matplotlib.pyplot as plt
        import seaborn as sns

        if self.feature_importance is None:
            logger.warning("No feature importance data available")
            return

        plt.figure(figsize=(10, 6))
        top_features = self.feature_importance.head(20)

        sns.barplot(data=top_features, x='importance', y='feature', palette='viridis')
        plt.title('Feature Importance')
        plt.xlabel('Importance')
        plt.ylabel('Feature')
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Saved importance plot to {save_path}")
        else:
            plt.show()

        plt.close()