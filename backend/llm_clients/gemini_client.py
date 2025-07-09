"""
Google Gemini LLM client implementation for comparison testing
"""

import time
from datetime import datetime
from typing import Optional, Dict, Any
import google.generativeai as genai
from .base_client import BaseLLMClient, LLMResponse
from ..config import settings, LLM_COSTS

class GeminiClient(BaseLLMClient):
    """Google Gemini LLM client for comparison testing"""
    
    def __init__(self):
        super().__init__("gemini", settings.gemini_model)
        
        if not settings.gemini_api_key:
            raise ValueError("Gemini API key must be configured")
        
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(self.model_name)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text response from Gemini"""
        
        start_time = time.time()
        
        # Prepare full prompt (Gemini doesn't have separate system prompt in same way)
        full_prompt = ""
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
        else:
            full_prompt = prompt
        
        # Configure generation parameters
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
        )
        
        if max_tokens:
            generation_config.max_output_tokens = max_tokens
        
        try:
            # Make API request
            response = await self.model.generate_content_async(
                full_prompt,
                generation_config=generation_config
            )
            
            # Parse response
            response_time = time.time() - start_time
            
            # Extract generated text
            generated_text = ""
            if response.text:
                generated_text = response.text
            
            # Estimate token usage (Gemini doesn't always provide exact counts)
            input_tokens = self.estimate_tokens(full_prompt)
            output_tokens = self.estimate_tokens(generated_text)
            total_tokens = input_tokens + output_tokens
            
            # Calculate cost
            cost_usd = self.calculate_cost(input_tokens, output_tokens)
            
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
                    "finish_reason": getattr(response, 'finish_reason', None),
                    "safety_ratings": getattr(response, 'safety_ratings', []),
                    "raw_response": str(response)
                }
            )
            
            self._update_usage_stats(llm_response)
            return llm_response
            
        except Exception as e:
            raise Exception(f"Gemini API error: {e}")
    
    async def generate_with_schema(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        **kwargs
    ) -> LLMResponse:
        """Generate structured response following a schema"""
        
        # For Gemini, we'll use prompt engineering for structured output
        enhanced_prompt = prompt
        
        if schema:
            import json
            schema_text = json.dumps(schema, indent=2)
            enhanced_prompt += f"\n\nPlease respond with a JSON object that follows this schema:\n{schema_text}"
            enhanced_prompt += "\n\nReturn only valid JSON, no additional text."
        
        return await self.generate(
            prompt=enhanced_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            **kwargs
        )
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for given text"""
        # Gemini tokenizer rough estimation: ~4 characters per token
        return len(text) // 4 + 1
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for Gemini usage"""
        costs = LLM_COSTS.get("gemini", {"input": 0.00125, "output": 0.00375})
        return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000
    
    def is_available(self) -> bool:
        """Check if Gemini client is properly configured"""
        return bool(settings.gemini_api_key) 