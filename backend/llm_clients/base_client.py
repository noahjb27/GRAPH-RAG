"""
Base LLM client interface for unified multi-provider support
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import time

@dataclass
class LLMResponse:
    """Standardized response from any LLM provider"""
    
    text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    response_time_seconds: float
    timestamp: datetime
    metadata: Dict[str, Any]
    
    @property
    def total_cost(self) -> float:
        """Total cost in USD"""
        return self.cost_usd
    
    @property
    def tokens_per_second(self) -> float:
        """Tokens generated per second"""
        if self.response_time_seconds == 0:
            return 0.0
        return self.output_tokens / self.response_time_seconds

class BaseLLMClient(ABC):
    """Abstract base class for all LLM clients"""
    
    def __init__(self, provider_name: str, model_name: str):
        self.provider_name = provider_name
        self.model_name = model_name
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.request_count = 0
        
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text response from the LLM"""
        pass
    
    @abstractmethod
    async def generate_with_schema(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        **kwargs
    ) -> LLMResponse:
        """Generate structured response following a schema"""
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for given text"""
        pass
    
    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for given token usage"""
        pass
    
    def _update_usage_stats(self, response: LLMResponse):
        """Update internal usage statistics"""
        self.total_tokens_used += response.total_tokens
        self.total_cost_usd += response.cost_usd
        self.request_count += 1
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "total_tokens_used": self.total_tokens_used,
            "total_cost_usd": self.total_cost_usd,
            "request_count": self.request_count,
            "avg_cost_per_request": (
                self.total_cost_usd / self.request_count 
                if self.request_count > 0 else 0.0
            ),
            "avg_tokens_per_request": (
                self.total_tokens_used / self.request_count 
                if self.request_count > 0 else 0.0
            )
        }
    
    def reset_usage_stats(self):
        """Reset usage statistics"""
        self.total_tokens_used = 0
        self.total_cost_usd = 0.0
        self.request_count = 0 