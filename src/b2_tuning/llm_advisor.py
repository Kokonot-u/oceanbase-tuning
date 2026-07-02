"""
大模型调优建议生成器

利用大语言模型生成OceanBase参数调优的自然语言建议。
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from loguru import logger

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available")

try:
    from langchain.llms import OpenAI, HuggingFacePipeline
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain not available")


@dataclass
class TuningRecommendation:
    """调优建议"""
    parameter: str
    current_value: Any
    recommended_value: Any
    reason: str
    expected_impact: str
    risk_level: str  # "low", "medium", "high"
    priority: str  # "low", "medium", "high", "critical"


class LLMAdvisor:
    """
    基于大模型的OceanBase调优建议生成器
    """

    SYSTEM_PROMPT = """你是一个OceanBase数据库性能调优专家。
基于提供的性能数据和参数配置，生成调优建议。

请考虑以下方面：
1. 识别性能瓶颈
2. 建议参数调整
3. 评估风险和预期影响
4. 提供调整优先级

输出格式使用JSON:
```json
{
  "analysis": "性能分析总结",
  "recommendations": [
    {
      "parameter": "参数名",
      "current_value": "当前值",
      "recommended_value": "建议值",
      "reason": "调整原因",
      "expected_impact": "预期影响",
      "risk_level": "risk_level",
      "priority": "priority"
    }
  ]
}
```
"""

    def __init__(self,
                 model_name: str = "Qwen/Qwen-7B-Chat",
                 use_api: bool = False,
                 api_key: Optional[str] = None):
        """
        初始化LLM Advisor

        Args:
            model_name: 模型名称
            use_api: 是否使用API（如OpenAI）
            api_key: API密钥
        """
        self.model_name = model_name
        self.use_api = use_api
        self.api_key = api_key
        self.llm = None
        self.chain = None

        if use_api and api_key:
            self._init_api_model()
        else:
            self._init_local_model()

    def _init_api_model(self) -> None:
        """初始化API模型（如OpenAI）"""
        if not LANGCHAIN_AVAILABLE:
            logger.error("LangChain not available for API models")
            return

        try:
            self.llm = OpenAI(
                temperature=0.7,
                api_key=self.api_key,
                model_name=self.model_name
            )
            self._init_chain()
            logger.info(f"Initialized API model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize API model: {e}")

    def _init_local_model(self) -> None:
        """初始化本地模型"""
        if not TRANSFORMERS_AVAILABLE or not LANGCHAIN_AVAILABLE:
            logger.error("Transformers/LangChain not available for local models")
            return

        try:
            # 加载tokenizer和模型
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )

            # 创建pipeline
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=2048,
                temperature=0.7,
                top_p=0.8,
            )

            self.llm = HuggingFacePipeline(pipeline=pipe)
            self._init_chain()
            logger.info(f"Initialized local model: {self.model_name}")

        except Exception as e:
            logger.error(f"Failed to initialize local model: {e}")

    def _init_chain(self) -> None:
        """初始化LangChain链"""
        if self.llm is None:
            return

        template = """{system_prompt}

性能数据：
{performance_data}

参数配置：
{parameter_config}

请生成调优建议："""

        prompt = PromptTemplate(
            input_variables=["system_prompt", "performance_data", "parameter_config"],
            template=template
        )

        self.chain = LLMChain(llm=self.llm, prompt=prompt)

    def generate_advice(self,
                       performance_data: Dict[str, Any],
                       parameter_config: Dict[str, Any]) -> List[TuningRecommendation]:
        """
        生成调优建议

        Args:
            performance_data: 性能数据
            parameter_config: 参数配置

        Returns:
            调优建议列表
        """
        if self.chain is None:
            # 回退到基于规则的简单建议
            return self._generate_rule_based_advice(performance_data, parameter_config)

        try:
            # 调用LLM
            response = self.chain.run(
                system_prompt=self.SYSTEM_PROMPT,
                performance_data=self._format_performance_data(performance_data),
                parameter_config=self._format_parameter_config(parameter_config)
            )

            # 解析响应
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._generate_rule_based_advice(performance_data, parameter_config)

    def _format_performance_data(self, data: Dict[str, Any]) -> str:
        """格式化性能数据"""
        lines = [
            f"TPMC: {data.get('tpmc', 'N/A')}",
            f"平均延迟: {data.get('latency', 'N/A')}ms",
            f"CPU使用率: {data.get('cpu_usage', 0):.1%}",
            f"内存使用率: {data.get('memory_usage', 0):.1%}",
            f"IO使用率: {data.get('io_usage', 0):.1%}",
            f"慢查询数: {data.get('slow_queries', 'N/A')}",
        ]

        return "\n".join(lines)

    def _format_parameter_config(self, config: Dict[str, Any]) -> str:
        """格式化参数配置"""
        lines = []
        for name, value in config.items():
            lines.append(f"{name}: {value}")
        return "\n".join(lines)

    def _parse_response(self, response: str) -> List[TuningRecommendation]:
        """解析LLM响应"""
        try:
            import json
            import re

            # 提取JSON部分
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response

            data = json.loads(json_str)
            recommendations = []

            for rec in data.get('recommendations', []):
                recommendations.append(TuningRecommendation(
                    parameter=rec.get('parameter', ''),
                    current_value=rec.get('current_value'),
                    recommended_value=rec.get('recommended_value'),
                    reason=rec.get('reason', ''),
                    expected_impact=rec.get('expected_impact', ''),
                    risk_level=rec.get('risk_level', 'medium'),
                    priority=rec.get('priority', 'medium')
                ))

            return recommendations

        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return []

    def _generate_rule_based_advice(self,
                                    performance_data: Dict[str, Any],
                                    parameter_config: Dict[str, Any]) -> List[TuningRecommendation]:
        """
        基于规则生成调优建议（后备方案）

        Args:
            performance_data: 性能数据
            parameter_config: 参数配置

        Returns:
            调优建议列表
        """
        recommendations = []

        # CPU使用率过高
        cpu_usage = performance_data.get('cpu_usage', 0)
        if cpu_usage > 0.8:
            current_threads = parameter_config.get('net_thread_count', 4)
            if current_threads > 2:
                recommendations.append(TuningRecommendation(
                    parameter='net_thread_count',
                    current_value=current_threads,
                    recommended_value=max(2, current_threads - 2),
                    reason=f"CPU使用率过高({cpu_usage:.1%})，建议减少网络线程数",
                    expected_impact="降低CPU使用率约10-20%",
                    risk_level="low",
                    priority="high"
                ))

        # 内存使用率过高
        memory_usage = performance_data.get('memory_usage', 0)
        if memory_usage > 0.85:
            current_memstore = parameter_config.get('memstore_limit_percentage', 50)
            if current_memstore > 30:
                recommendations.append(TuningRecommendation(
                    parameter='memstore_limit_percentage',
                    current_value=current_memstore,
                    recommended_value=max(30, current_memstore - 10),
                    reason=f"内存使用率过高({memory_usage:.1%})，建议降低memstore占比",
                    expected_impact="降低内存使用率约5-10%",
                    risk_level="medium",
                    priority="high"
                ))

        # 缓存命中率低
        latency = performance_data.get('latency', 1)
        if latency > 10:
            current_cache = parameter_config.get('block_cache_size', 2147483648)
            recommendations.append(TuningRecommendation(
                parameter='block_cache_size',
                current_value=current_cache,
                recommended_value=min(8589934592, current_cache * 2),
                reason=f"延迟较高({latency:.2f}ms)，建议增加block cache大小",
                expected_impact="降低延迟约20-30%",
                risk_level="medium",
                priority="medium"
            ))

        # 并发度不足
        tpmc = performance_data.get('tpmc', 0)
        if tpmc > 1000 and tpmc < 5000:
            current_parallel = parameter_config.get('parallel_max_servers', 100)
            if current_parallel < 200:
                recommendations.append(TuningRecommendation(
                    parameter='parallel_max_servers',
                    current_value=current_parallel,
                    recommended_value=min(500, current_parallel + 100),
                    reason=f"TPMC潜力未充分发挥，建议增加并行服务器数",
                    expected_impact="提升吞吐量约20-40%",
                    risk_level="low",
                    priority="medium"
                ))

        return recommendations

    def explain_recommendation(self, recommendation: TuningRecommendation) -> str:
        """
        解释推荐建议

        Args:
            recommendation: 调优建议

        Returns:
            自然语言解释
        """
        explanation = f"""
## 建议调整参数: {recommendation.parameter}

**当前值**: {recommendation.current_value}
**建议值**: {recommendation.recommended_value}

**调整原因**:
{recommendation.reason}

**预期影响**:
{recommendation.expected_impact}

**风险评估**: {recommendation.risk_level.upper()}
**优先级**: {recommendation.priority.upper()}
"""
        return explanation

    def generate_report(self,
                       performance_data: Dict[str, Any],
                       parameter_config: Dict[str, Any],
                       recommendations: Optional[List[TuningRecommendation]] = None) -> str:
        """
        生成完整的调优报告

        Args:
            performance_data: 性能数据
            parameter_config: 参数配置
            recommendations: 调优建议列表（可选，会自动生成）

        Returns:
            调优报告
        """
        if recommendations is None:
            recommendations = self.generate_advice(performance_data, parameter_config)

        report = f"""
# OceanBase性能调优报告

## 性能概况
- TPMC: {performance_data.get('tpmc', 'N/A')}
- 平均延迟: {performance_data.get('latency', 'N/A')}ms
- CPU使用率: {performance_data.get('cpu_usage', 0):.1%}
- 内存使用率: {performance_data.get('memory_usage', 0):.1%}
- IO使用率: {performance_data.get('io_usage', 0):.1%}

## 调优建议

共生成 {len(recommendations)} 条建议：

"""

        # 按优先级排序
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations_sorted = sorted(
            recommendations,
            key=lambda x: priority_order.get(x.priority, 99)
        )

        for i, rec in enumerate(recommendations_sorted, 1):
            report += f"\n### {i}. {rec.parameter} (优先级: {rec.priority})\n\n"
            report += self.explain_recommendation(rec)

        return report

    def save_report(self, report: str, output_path: str) -> None:
        """
        保存报告到文件

        Args:
            report: 报告内容
            output_path: 输出路径
        """
        from pathlib import Path

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Report saved to {output_path}")

    def interactive_chat(self) -> None:
        """
        交互式聊天模式

        允许用户提问关于调优的问题
        """
        if self.chain is None:
            logger.error("LLM not initialized, interactive mode not available")
            return

        print("=== OceanBase调优助手 ===")
        print("输入问题，或输入 'quit' 退出\n")

        while True:
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                break

            if not user_input:
                continue

            try:
                response = self.llm.predict(user_input)
                print(f"Assistant: {response}\n")
            except Exception as e:
                print(f"Error: {e}\n")


class PromptTemplateManager:
    """提示词模板管理器"""

    DEFAULT_TEMPLATES = {
        "performance_analysis": """
分析以下OceanBase性能指标，识别潜在问题和优化方向：

指标：{metrics}

请提供：
1. 性能瓶颈分析
2. 潜在风险点
3. 优化建议方向
""",
        "parameter_tuning": """
当前OceanBase参数配置：
{parameters}

当前性能表现：
{performance}

请建议哪些参数需要调整，以及如何调整。
""",
        "diagnosis": """
症状：{symptoms}
相关参数：{parameters}
相关指标：{metrics}

请诊断可能的原因并提供解决方案。
""",
    }

    def __init__(self):
        self.templates = self.DEFAULT_TEMPLATES.copy()

    def get_template(self, name: str) -> str:
        """获取模板"""
        return self.templates.get(name, "")

    def add_template(self, name: str, template: str) -> None:
        """添加模板"""
        self.templates[name] = template

    def format_template(self, name: str, **kwargs) -> str:
        """格式化模板"""
        template = self.get_template(name)
        return template.format(**kwargs)