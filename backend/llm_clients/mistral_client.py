"""
Mistral LLM client implementation using OpenAI-compatible API
Primary provider for development (free university access)
"""

import httpx
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from .base_client import BaseLLMClient, LLMResponse
from ..config import settings

class MistralClient(BaseLLMClient):
    """Mistral LLM client using OpenAI-compatible endpoint"""
    
    def __init__(self):
        super().__init__("mistral", settings.mistral_model)
        self.api_key = settings.mistral_api_key
        self.base_url = settings.mistral_base_url
        self.timeout = 300.0  # 5 minutes for complex queries
        
        if not self.api_key or not self.base_url:
            raise ValueError("Mistral API key and base URL must be configured")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate text response from Mistral"""
        
        start_time = time.time()
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request payload
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        # Add any additional parameters
        for key, value in kwargs.items():
            if key not in payload:
                payload[key] = value
        
        # Make API request
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                response_data = response.json()
                
            except httpx.HTTPError as e:
                raise Exception(f"Mistral API error: {e}")
        
        # Parse response
        response_time = time.time() - start_time
        
        # Extract token usage (if available)
        usage = response_data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0) 
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
        
        # Calculate cost (free for university access)
        cost_usd = self.calculate_cost(input_tokens, output_tokens)
        
        # Extract generated text
        generated_text = ""
        if "choices" in response_data and response_data["choices"]:
            message = response_data["choices"][0].get("message", {})
            generated_text = message.get("content", "")
        
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
                "raw_response": response_data
            }
        )
        
        self._update_usage_stats(llm_response)
        return llm_response
    
    async def generate_with_schema(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        **kwargs
    ) -> LLMResponse:
        """Generate structured response following a schema"""
        
        # For Mistral, we'll use function calling or prompt engineering for structured output
        enhanced_system_prompt = system_prompt or ""
        
        if schema:
            schema_text = json.dumps(schema, indent=2)
            enhanced_system_prompt += f"\n\nPlease respond with a JSON object that follows this schema:\n{schema_text}"
            enhanced_system_prompt += "\n\nReturn only valid JSON, no additional text."
        
        return await self.generate(
            prompt=prompt,
            system_prompt=enhanced_system_prompt,
            temperature=temperature,
            **kwargs
        )
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for given text (rough approximation)"""
        # Rough estimation: ~4 characters per token for most languages
        return len(text) // 4 + 1
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost (free for university access)"""
        return 0.0
    
    def is_available(self) -> bool:
        """Check if Mistral client is properly configured"""
        return bool(self.api_key and self.base_url) 