"""
Metrics calculator for evaluation results
"""

from typing import List, Dict, Any
from .evaluator import EvaluationResult

class MetricsCalculator:
    """Calculate metrics from evaluation results"""
    
    @staticmethod
    def calculate_success_rate(results: List[EvaluationResult]) -> float:
        """Calculate overall success rate"""
        if not results:
            return 0.0
        
        successful = sum(1 for r in results if r.success)
        return successful / len(results)
    
    @staticmethod
    def calculate_average_cost(results: List[EvaluationResult]) -> float:
        """Calculate average cost per query"""
        if not results:
            return 0.0
        
        total_cost = sum(r.cost_usd for r in results)
        return total_cost / len(results)
    
    @staticmethod
    def calculate_average_execution_time(results: List[EvaluationResult]) -> float:
        """Calculate average execution time"""
        if not results:
            return 0.0
        
        total_time = sum(r.execution_time_seconds for r in results)
        return total_time / len(results)
    
    @staticmethod
    def calculate_tokens_per_dollar(results: List[EvaluationResult]) -> float:
        """Calculate tokens generated per dollar spent"""
        total_tokens = sum(r.total_tokens for r in results)
        total_cost = sum(r.cost_usd for r in results)
        
        if total_cost == 0:
            return 0.0
        
        return total_tokens / total_cost
    
    @staticmethod
    def compare_pipelines(results: List[EvaluationResult]) -> List[Dict[str, Any]]:
        """Compare performance across pipelines"""
        
        pipeline_results = {}
        
        for result in results:
            pipeline = result.pipeline_name
            if pipeline not in pipeline_results:
                pipeline_results[pipeline] = []
            pipeline_results[pipeline].append(result)
        
        comparison = []
        
        for pipeline, pipeline_results_list in pipeline_results.items():
            comparison.append({
                "pipeline_name": pipeline,
                "success_rate": MetricsCalculator.calculate_success_rate(pipeline_results_list),
                "avg_cost": MetricsCalculator.calculate_average_cost(pipeline_results_list),
                "avg_execution_time": MetricsCalculator.calculate_average_execution_time(pipeline_results_list),
                "total_evaluations": len(pipeline_results_list)
            })
        
        return comparison
    
    @staticmethod
    def compare_llm_providers(results: List[EvaluationResult]) -> List[Dict[str, Any]]:
        """Compare performance across LLM providers"""
        
        provider_results = {}
        
        for result in results:
            provider = result.llm_provider
            if provider not in provider_results:
                provider_results[provider] = []
            provider_results[provider].append(result)
        
        comparison = []
        
        for provider, provider_results_list in provider_results.items():
            # Calculate average tokens per second for this provider
            total_tokens = sum(r.total_tokens for r in provider_results_list if r.execution_time_seconds > 0)
            total_time = sum(r.execution_time_seconds for r in provider_results_list if r.execution_time_seconds > 0)
            avg_tokens_per_second = total_tokens / total_time if total_time > 0 else 0.0
            
            comparison.append({
                "llm_provider": provider,
                "success_rate": MetricsCalculator.calculate_success_rate(provider_results_list),
                "avg_cost": MetricsCalculator.calculate_average_cost(provider_results_list),
                "avg_execution_time": MetricsCalculator.calculate_average_execution_time(provider_results_list),
                "avg_tokens_per_second": avg_tokens_per_second,
                "total_evaluations": len(provider_results_list)
            })
        
        return comparison 