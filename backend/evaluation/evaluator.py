"""
Main evaluator for Graph-RAG pipeline assessment with multi-LLM support
"""

import time
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime

from ..pipelines.base_pipeline import BasePipeline
from ..pipelines.direct_cypher_pipeline import DirectCypherPipeline
from ..pipelines.multi_query_cypher_pipeline import MultiQueryCypherPipeline
from ..pipelines.no_rag_pipeline import NoRAGPipeline
from ..pipelines.vector_pipeline import VectorPipeline
from ..pipelines.hybrid_pipeline import HybridPipeline
from ..pipelines.path_traversal_pipeline import PathTraversalPipeline
from ..pipelines.graph_embedding_pipeline import GraphEmbeddingPipeline
from ..pipelines.graphrag_transport_pipeline import GraphRAGTransportPipeline
from ..pipelines.chatbot_pipeline import ChatbotPipeline
from ..config import get_available_llm_providers
from .question_loader import QuestionLoader

@dataclass
class EvaluationResult:
    """Result of evaluating a pipeline on a question"""
    
    question_id: str
    question_text: str
    pipeline_name: str
    llm_provider: str
    
    # Results
    answer: str
    success: bool
    execution_time_seconds: float
    
    # LLM metrics
    cost_usd: float
    total_tokens: int
    tokens_per_second: float
    
    # Pipeline-specific data
    generated_cypher: Optional[str] = None
    cypher_results: Optional[List[Dict[str, Any]]] = None
    
    # Evaluation metadata
    timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}

class Evaluator:
    """Main evaluator for Graph-RAG approaches with multi-LLM support"""
    
    def __init__(self):
        self.question_loader = QuestionLoader()
        self.pipelines = self._initialize_pipelines()
        self.evaluation_history = []
        
    def _initialize_pipelines(self) -> Dict[str, BasePipeline]:
        """Initialize all available pipelines"""
        return {
            "direct_cypher": DirectCypherPipeline(),
            "multi_query_cypher": MultiQueryCypherPipeline(),
            "no_rag": NoRAGPipeline(),
            "vector": VectorPipeline(),
            "hybrid": HybridPipeline(),
            "path_traversal": PathTraversalPipeline(),
            "graph_embedding": GraphEmbeddingPipeline(),
            "graphrag_transport": GraphRAGTransportPipeline(),
            "chatbot": ChatbotPipeline()
        }
    
    async def evaluate_single_question(
        self,
        question_id: str,
        pipeline_names: List[str],
        llm_providers: List[str]
    ) -> List[EvaluationResult]:
        """Evaluate a single question across multiple pipelines and LLM providers"""
        
        question = self.question_loader.get_question_by_id(question_id)
        if not question:
            raise ValueError(f"Question {question_id} not found")
        
        results = []
        
        # Test each pipeline with each LLM provider
        for pipeline_name in pipeline_names:
            if pipeline_name not in self.pipelines:
                print(f"Warning: Pipeline {pipeline_name} not available")
                continue
                
            pipeline = self.pipelines[pipeline_name]
            
            for llm_provider in llm_providers:
                try:
                    result = await self._evaluate_pipeline_question(
                        pipeline, question, llm_provider
                    )
                    results.append(result)
                    
                except Exception as e:
                    # Create error result
                    error_result = EvaluationResult(
                        question_id=question.question_id,
                        question_text=question.question_text,
                        pipeline_name=pipeline_name,
                        llm_provider=llm_provider,
                        answer="",
                        success=False,
                        execution_time_seconds=0.0,
                        cost_usd=0.0,
                        total_tokens=0,
                        tokens_per_second=0.0,
                        error_message=str(e)
                    )
                    results.append(error_result)
        
        return results
    
    async def evaluate_sample_questions(
        self,
        pipeline_names: List[str],
        llm_providers: List[str],
        question_count: int = 5,
        categories: Optional[List[str]] = None,
        max_difficulty: int = 3
    ) -> List[EvaluationResult]:
        """Evaluate sample questions for development testing"""
        
        questions = self.question_loader.get_sample_questions(
            count=question_count,
            categories=categories,
            max_difficulty=max_difficulty
        )
        
        results = []
        
        for question in questions:
            question_results = await self.evaluate_single_question(
                question.question_id,
                pipeline_names,
                llm_providers
            )
            results.extend(question_results)
        
        return results
    
    async def evaluate_full_taxonomy(
        self,
        pipeline_names: List[str],
        llm_providers: List[str],
        progress_callback: Optional[Callable] = None
    ) -> List[EvaluationResult]:
        """Evaluate all questions in the taxonomy (batch evaluation)"""
        
        questions = self.question_loader.get_all_questions()
        total_evaluations = len(questions) * len(pipeline_names) * len(llm_providers)
        
        results = []
        completed = 0
        
        for question in questions:
            question_results = await self.evaluate_single_question(
                question.question_id,
                pipeline_names, 
                llm_providers
            )
            results.extend(question_results)
            
            completed += len(question_results)
            
            # Report progress
            if progress_callback:
                progress_callback({
                    "completed": completed,
                    "total": total_evaluations,
                    "current_question": question.question_text,
                    "progress_percent": (completed / total_evaluations) * 100
                })
        
        return results
    
    async def _evaluate_pipeline_question(
        self,
        pipeline: BasePipeline,
        question: Any,  # EvaluationQuestion type
        llm_provider: str
    ) -> EvaluationResult:
        """Evaluate a single pipeline on a single question"""
        
        start_time = time.time()
        
        try:
            # Process the question with the pipeline
            pipeline_result = await pipeline.process_query(
                question.question_text,
                llm_provider=llm_provider
            )
            
            # Convert to evaluation result
            eval_result = EvaluationResult(
                question_id=question.question_id,
                question_text=question.question_text,
                pipeline_name=pipeline.name,
                llm_provider=llm_provider,
                answer=pipeline_result.answer,
                success=pipeline_result.success,
                execution_time_seconds=pipeline_result.execution_time_seconds,
                cost_usd=pipeline_result.cost_usd,
                total_tokens=pipeline_result.total_tokens,
                tokens_per_second=pipeline_result.tokens_per_second,
                generated_cypher=pipeline_result.generated_cypher,
                cypher_results=pipeline_result.cypher_results,
                error_message=pipeline_result.error_message,
                metadata={
                    "question_category": question.category,
                    "question_difficulty": question.difficulty,
                    "question_capabilities": question.required_capabilities,
                    "historical_context": question.historical_context,
                    **(pipeline_result.metadata or {})
                }
            )
            
            # Store in history
            self.evaluation_history.append(eval_result)
            
            return eval_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            error_result = EvaluationResult(
                question_id=question.question_id,
                question_text=question.question_text,
                pipeline_name=pipeline.name,
                llm_provider=llm_provider,
                answer="",
                success=False,
                execution_time_seconds=execution_time,
                cost_usd=0.0,
                total_tokens=0,
                tokens_per_second=0.0,
                error_message=str(e)
            )
            
            self.evaluation_history.append(error_result)
            return error_result
    
    def get_available_pipelines(self) -> List[str]:
        """Get list of available pipeline names"""
        return list(self.pipelines.keys())
    
    def get_available_llm_providers(self) -> List[str]:
        """Get list of available LLM providers"""
        return get_available_llm_providers()
    
    def get_evaluation_summary(
        self,
        results: List[EvaluationResult]
    ) -> Dict[str, Any]:
        """Generate summary statistics from evaluation results"""
        
        if not results:
            return {"total_evaluations": 0}
        
        # Basic statistics
        total_evaluations = len(results)
        successful_evaluations = sum(1 for r in results if r.success)
        
        # Group by pipeline and LLM provider
        by_pipeline = {}
        by_llm_provider = {}
        
        total_cost = 0.0
        total_tokens = 0
        total_execution_time = 0.0
        
        for result in results:
            # Pipeline statistics
            if result.pipeline_name not in by_pipeline:
                by_pipeline[result.pipeline_name] = {
                    "total": 0, "successful": 0, "cost": 0.0, "tokens": 0, "time": 0.0
                }
            
            pipeline_stats = by_pipeline[result.pipeline_name]
            pipeline_stats["total"] += 1
            if result.success:
                pipeline_stats["successful"] += 1
            pipeline_stats["cost"] += result.cost_usd
            pipeline_stats["tokens"] += result.total_tokens
            pipeline_stats["time"] += result.execution_time_seconds
            
            # LLM provider statistics
            if result.llm_provider not in by_llm_provider:
                by_llm_provider[result.llm_provider] = {
                    "total": 0, "successful": 0, "cost": 0.0, "tokens": 0, "time": 0.0
                }
            
            llm_stats = by_llm_provider[result.llm_provider]
            llm_stats["total"] += 1
            if result.success:
                llm_stats["successful"] += 1
            llm_stats["cost"] += result.cost_usd
            llm_stats["tokens"] += result.total_tokens
            llm_stats["time"] += result.execution_time_seconds
            
            # Overall totals
            total_cost += result.cost_usd
            total_tokens += result.total_tokens
            total_execution_time += result.execution_time_seconds
        
        # Calculate success rates
        for pipeline_name, stats in by_pipeline.items():
            stats["success_rate"] = stats["successful"] / stats["total"] if stats["total"] > 0 else 0.0
            stats["avg_time"] = stats["time"] / stats["total"] if stats["total"] > 0 else 0.0
        
        for provider_name, stats in by_llm_provider.items():
            stats["success_rate"] = stats["successful"] / stats["total"] if stats["total"] > 0 else 0.0
            stats["avg_time"] = stats["time"] / stats["total"] if stats["total"] > 0 else 0.0
        
        # Calculate average tokens per second
        total_tokens_with_time = sum(r.total_tokens for r in results if r.execution_time_seconds > 0)
        total_time_with_tokens = sum(r.execution_time_seconds for r in results if r.execution_time_seconds > 0)
        avg_tokens_per_second = total_tokens_with_time / total_time_with_tokens if total_time_with_tokens > 0 else 0.0
        
        failed_evaluations = total_evaluations - successful_evaluations
        
        return {
            "total_evaluations": total_evaluations,
            "successful_evaluations": successful_evaluations,
            "failed_evaluations": failed_evaluations,
            "success_rate": successful_evaluations / total_evaluations,
            "avg_execution_time": total_execution_time / total_evaluations,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "avg_tokens_per_second": avg_tokens_per_second,
            "by_pipeline": by_pipeline,
            "by_llm_provider": by_llm_provider
        }

    def export_results_to_json(
        self,
        results: List[EvaluationResult],
        file_path: str,
        include_summary: bool = True
    ) -> None:
        """Export evaluation results to JSON file"""
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "total_results": len(results),
            "results": []
        }
        
        # Convert results to dictionaries
        for result in results:
            result_dict = asdict(result)
            
            # Convert datetime to ISO string for JSON serialization
            if result_dict.get("timestamp") and result.timestamp:
                result_dict["timestamp"] = result.timestamp.isoformat()
            
            # Convert cypher_results to JSON string if present
            if result_dict.get("cypher_results"):
                result_dict["cypher_results"] = json.dumps(result_dict["cypher_results"])
            
            # Convert metadata to JSON string if present
            if result_dict.get("metadata"):
                result_dict["metadata"] = json.dumps(result_dict["metadata"])
            
            export_data["results"].append(result_dict)
        
        # Add summary if requested
        if include_summary:
            export_data["summary"] = self.get_evaluation_summary(results)
        
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        print(f"Exported {len(results)} results to {file_path}")

    def export_results_to_csv(
        self,
        results: List[EvaluationResult],
        file_path: str,
        flatten_metadata: bool = True
    ) -> None:
        """Export evaluation results to CSV file"""
        
        if not results:
            print("No results to export")
            return
        
        # Define CSV columns
        base_columns = [
            "question_id",
            "question_text", 
            "pipeline_name",
            "llm_provider",
            "answer",
            "success",
            "execution_time_seconds",
            "cost_usd",
            "total_tokens",
            "tokens_per_second",
            "generated_cypher",
            "cypher_results",
            "timestamp",
            "error_message"
        ]
        
        # If flattening metadata, get all unique metadata keys
        metadata_keys = set()
        if flatten_metadata:
            for result in results:
                if result.metadata:
                    metadata_keys.update(result.metadata.keys())
        
        # Final column list
        columns = base_columns + (["metadata"] if not flatten_metadata else [f"metadata_{key}" for key in sorted(metadata_keys)])
        
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write CSV
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            
            for result in results:
                row = {}
                
                # Basic fields
                row["question_id"] = result.question_id
                row["question_text"] = result.question_text
                row["pipeline_name"] = result.pipeline_name
                row["llm_provider"] = result.llm_provider
                row["answer"] = result.answer
                row["success"] = result.success
                row["execution_time_seconds"] = result.execution_time_seconds
                row["cost_usd"] = result.cost_usd
                row["total_tokens"] = result.total_tokens
                row["tokens_per_second"] = result.tokens_per_second
                row["generated_cypher"] = result.generated_cypher or ""
                row["cypher_results"] = json.dumps(result.cypher_results) if result.cypher_results else ""
                row["timestamp"] = result.timestamp.isoformat() if result.timestamp else ""
                row["error_message"] = result.error_message or ""
                
                # Handle metadata
                if flatten_metadata and result.metadata:
                    for key in metadata_keys:
                        row[f"metadata_{key}"] = result.metadata.get(key, "")
                elif not flatten_metadata:
                    row["metadata"] = json.dumps(result.metadata) if result.metadata else ""
                else:
                    # Fill empty metadata columns
                    for key in metadata_keys:
                        row[f"metadata_{key}"] = ""
                
                writer.writerow(row)
        
        print(f"Exported {len(results)} results to {file_path}")

    def export_results_with_timestamp(
        self,
        results: List[EvaluationResult],
        base_filename: str,
        formats: List[str] = ["json", "csv"],
        output_dir: str = "evaluation_exports"
    ) -> List[str]:
        """Export results with automatic timestamp in filename"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exported_files = []
        
        for format_type in formats:
            if format_type.lower() == "json":
                filename = f"{base_filename}_{timestamp}.json"
                file_path = f"{output_dir}/{filename}"
                self.export_results_to_json(results, file_path)
                exported_files.append(file_path)
            
            elif format_type.lower() == "csv":
                filename = f"{base_filename}_{timestamp}.csv"
                file_path = f"{output_dir}/{filename}"
                self.export_results_to_csv(results, file_path)
                exported_files.append(file_path)
            
            else:
                print(f"Warning: Unknown format '{format_type}', skipping")
        
        return exported_files 