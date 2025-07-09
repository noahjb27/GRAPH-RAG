"""
No-RAG Baseline Pipeline - Direct LLM querying without graph data
Priority 2 implementation for comparison baseline
"""

import time
from typing import List
from .base_pipeline import BasePipeline, PipelineResult
from ..llm_clients.client_factory import create_llm_client

class NoRAGPipeline(BasePipeline):
    """
    No-RAG baseline pipeline for comparison
    
    Process:
    1. Direct LLM query without any graph data
    2. Pure knowledge-based response
    """
    
    def __init__(self):
        super().__init__(
            name="No-RAG Baseline",
            description="Direct LLM querying without any graph data"
        )
    
    async def process_query(
        self,
        question: str,
        llm_provider: str = "mistral",
        **kwargs
    ) -> PipelineResult:
        """Process a natural language question without any RAG"""
        
        start_time = time.time()
        
        try:
            # Get LLM client
            llm_client = create_llm_client(llm_provider)
            if not llm_client:
                return PipelineResult(
                    answer="",
                    approach=self.name,
                    llm_provider=llm_provider,
                    execution_time_seconds=time.time() - start_time,
                    success=False,
                    error_message=f"LLM provider {llm_provider} not available",
                    error_stage="llm_client_init"
                )
            
            # Generate response using only LLM knowledge
            system_prompt = self._get_system_prompt()
            
            llm_response = await llm_client.generate(
                prompt=question,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=300
            )
            
            execution_time = time.time() - start_time
            
            result = PipelineResult(
                answer=llm_response.text if llm_response else "No response generated",
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=bool(llm_response and llm_response.text),
                llm_response=llm_response,
                metadata={
                    "approach": "direct_llm",
                    "used_external_data": False
                }
            )
            
            self.update_stats(result)
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            result = PipelineResult(
                answer="",
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=False,
                error_message=str(e),
                error_stage="llm_generation"
            )
            self.update_stats(result)
            return result
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for No-RAG baseline"""
        
        return """You are an expert on historical Berlin transport networks (1946-1989).

Answer questions about Berlin's public transportation history using only your training knowledge. Focus on:

- Historical accuracy about Berlin transport systems
- The impact of political division (1961+ East/West split)
- Transport modes: tram, U-Bahn, S-Bahn, bus, ferry systems
- Key stations, lines, and network changes over time
- Administrative geography and neighborhoods

Be honest about limitations in your knowledge and avoid speculation. If you don't have specific information, say so clearly.

Provide concise, factual responses with relevant historical context."""
    
    def get_required_capabilities(self) -> List[str]:
        """Return required capabilities for this pipeline"""
        return [
            "llm_generation",
            "historical_knowledge"
        ] 