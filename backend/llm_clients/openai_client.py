"""
OpenAI LLM client implementation for comparison testing
"""

import time
from datetime import datetime
from typing import Optional, Dict, Any
import openai
from .base_client import BaseLLMClient, LLMResponse
from ..config import settings, LLM_COSTS

class OpenAIClient(BaseLLMClient):
    """OpenAI LLM client for comparison testing"""
    
    def __init__(self):
        super().__init__("openai", settings.openai_model)
        
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key must be configured")
        
        self.client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key
        )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text response from OpenAI"""
        
        start_time = time.time()
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request parameters
        request_params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            request_params["max_tokens"] = max_tokens
            
        # Add any additional parameters
        for key, value in kwargs.items():
            if key not in request_params:
                request_params[key] = value
        
        try:
            # Make API request
            response = await self.client.chat.completions.create(**request_params)
            
            # Parse response
            response_time = time.time() - start_time
            
            # Extract token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else input_tokens + output_tokens
            
            # Calculate cost
            cost_usd = self.calculate_cost(input_tokens, output_tokens)
            
            # Extract generated text
            generated_text = ""
            if response.choices:
                generated_text = response.choices[0].message.content or ""
            
            # Create response object
            llm_response = LLMResponse(
                text=generated_text,
                provider=self.provider_name,
                model=self.model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                response_time_seconds=response_time,
                timestamp=datetime.now(),
                metadata={
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "finish_reason": response.choices[0].finish_reason if response.choices else None,
                    "raw_response": response.model_dump() if hasattr(response, 'model_dump') else str(response)
                }
            )
            
            self._update_usage_stats(llm_response)
            return llm_response
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")
    
    async def generate_with_schema(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        **kwargs
    ) -> LLMResponse:
        """Generate structured response following a schema"""
        
        # Use OpenAI's function calling for structured output if schema provided
        if schema:
            function_def = {
                "name": "structured_response", 
                "description": "Generate a structured response",
                "parameters": schema
            }
            
            return await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                functions=[function_def],
                function_call={"name": "structured_response"},
                **kwargs
            )
        else:
            return await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                **kwargs
            )
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for given text"""
        # GPT tokenizer rough estimation: ~4 characters per token
        return len(text) // 4 + 1
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for OpenAI usage"""
        costs = LLM_COSTS.get("openai", {"input": 0.01, "output": 0.03})
        return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000
    
    def is_available(self) -> bool:
        """Check if OpenAI client is properly configured"""
        return bool(settings.openai_api_key) 