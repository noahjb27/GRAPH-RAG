"""
Base pipeline class for all Graph-RAG approaches
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from ..llm_clients.base_client import LLMResponse

@dataclass
class PipelineResult:
    """Result from a Graph-RAG pipeline execution"""
    
    answer: str
    approach: str
    llm_provider: str
    execution_time_seconds: float
    success: bool
    
    # LLM-related metrics
    llm_response: Optional[LLMResponse] = None
    
    # Pipeline-specific data
    generated_cypher: Optional[str] = None
    cypher_results: Optional[List[Dict[str, Any]]] = None
    retrieved_context: Optional[List[str]] = None
    
    # Error information
    error_message: Optional[str] = None
    error_stage: Optional[str] = None  # Which stage failed
    
    # Metadata
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def cost_usd(self) -> float:
        """Get cost from LLM response"""
        return self.llm_response.cost_usd if self.llm_response else 0.0
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens from LLM response"""
        return self.llm_response.total_tokens if self.llm_response else 0
    
    @property
    def tokens_per_second(self) -> float:
        """Get tokens per second from LLM response"""
        return self.llm_response.tokens_per_second if self.llm_response else 0.0

class BasePipeline(ABC):
    """Abstract base class for all Graph-RAG pipelines"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.success_count = 0
        
    @abstractmethod
    async def process_query(
        self,
        question: str,
        llm_provider: str = "mistral",
        **kwargs
    ) -> PipelineResult:
        """Process a natural language question and return an answer"""
        pass
    
    @abstractmethod
    def get_required_capabilities(self) -> List[str]:
        """Return list of capabilities this pipeline requires"""
        pass
    
    def update_stats(self, result: PipelineResult):
        """Update pipeline statistics"""
        self.execution_count += 1
        self.total_execution_time += result.execution_time_seconds
        if result.success:
            self.success_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline performance statistics"""
        avg_time = (
            self.total_execution_time / self.execution_count 
            if self.execution_count > 0 else 0.0
        )
        success_rate = (
            self.success_count / self.execution_count 
            if self.execution_count > 0 else 0.0
        )
        
        return {
            "name": self.name,
            "description": self.description,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "success_rate": success_rate,
            "average_execution_time": avg_time,
            "total_execution_time": self.total_execution_time
        }
    
    def reset_stats(self):
        """Reset pipeline statistics"""
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.success_count = 0 