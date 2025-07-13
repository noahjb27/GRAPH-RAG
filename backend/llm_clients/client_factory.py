"""
Client factory for managing and creating LLM clients
"""

from typing import Dict, Optional
from .base_client import BaseLLMClient
from .mistral_client import MistralClient
from .openai_client import OpenAIClient
from .gemini_client import GeminiClient
from ..config import get_available_llm_providers

class LLMClientFactory:
    """Factory for creating and managing LLM clients"""
    
    _clients: Dict[str, BaseLLMClient] = {}
    
    @classmethod
    def create_client(cls, provider: str) -> Optional[BaseLLMClient]:
        """Create a client for the specified provider"""
        
        if provider in cls._clients:
            return cls._clients[provider]
        
        try:
            if provider == "mistral":
                client = MistralClient()
            elif provider == "openai":
                client = OpenAIClient()
            elif provider == "gemini":
                client = GeminiClient()
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            if client.is_available():
                cls._clients[provider] = client
                return client
            else:
                return None
                
        except Exception as e:
            print(f"Failed to create {provider} client: {e}")
            return None
    
    @classmethod
    def get_client(cls, provider: str) -> Optional[BaseLLMClient]:
        """Get existing client or create new one"""
        if provider in cls._clients:
            return cls._clients[provider]
        return cls.create_client(provider)
    
    @classmethod
    def get_available_clients(cls) -> Dict[str, BaseLLMClient]:
        """Get all available and configured clients"""
        available_providers = get_available_llm_providers()
        clients = {}
        
        for provider in available_providers:
            client = cls.get_client(provider)
            if client:
                clients[provider] = client
        
        return clients
    
    @classmethod
    def get_primary_client(cls) -> Optional[BaseLLMClient]:
        """Get the primary client (OpenAI preferred for stability)"""
        # Priority order: OpenAI (primary) -> Mistral (university) -> Gemini (backup)
        priority_order = ["openai", "mistral", "gemini"]
        
        for provider in priority_order:
            client = cls.get_client(provider)
            if client:
                return client
        
        return None
    
    @classmethod
    def reset_clients(cls):
        """Reset all clients (useful for testing)"""
        cls._clients.clear()
    
    @classmethod
    def get_client_stats(cls) -> Dict[str, Dict]:
        """Get usage statistics for all clients"""
        stats = {}
        for provider, client in cls._clients.items():
            stats[provider] = client.get_usage_stats()
        return stats

# Convenience functions
def create_llm_client(provider: str) -> Optional[BaseLLMClient]:
    """Create a single LLM client"""
    return LLMClientFactory.create_client(provider)

def get_all_clients() -> Dict[str, BaseLLMClient]:
    """Get all available LLM clients"""
    return LLMClientFactory.get_available_clients()

def get_primary_client() -> Optional[BaseLLMClient]:
    """Get the primary LLM client"""
    return LLMClientFactory.get_primary_client()

async def test_client_connectivity() -> Dict[str, bool]:
    """Test connectivity for all configured clients"""
    results = {}
    available_providers = get_available_llm_providers()
    
    for provider in available_providers:
        try:
            client = create_llm_client(provider)
            if client:
                # Simple connectivity test
                response = await client.generate(
                    prompt="Hello", 
                    max_tokens=5, 
                    temperature=0.1
                )
                results[provider] = len(response.text) > 0
            else:
                results[provider] = False
        except Exception as e:
            print(f"Connectivity test failed for {provider}: {e}")
            results[provider] = False
    
    return results 