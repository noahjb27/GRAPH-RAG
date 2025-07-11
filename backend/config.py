"""
Configuration management for Graph-RAG Research System
Handles environment variables and settings for multi-LLM providers
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # FastAPI settings
    app_name: str = "Graph-RAG Research System"
    debug: bool = False
    backend_port: int = 8000
    host: str = "0.0.0.0"
    
    # Neo4j Database settings
    neo4j_uri: str = Field(alias="NEO4J_AURA_URI")
    neo4j_username: str = Field(alias="NEO4J_AURA_USERNAME")
    neo4j_password: str = Field(alias="NEO4J_AURA_PASSWORD")
    neo4j_database: str = "neo4j"
    
    # LLM Provider Settings
    # Mistral (University access - VPN required)
    mistral_api_key: Optional[str] = None
    mistral_base_url: Optional[str] = None  # OpenAI-compatible endpoint
    mistral_model: str = "llm1"  # University Mistral Large model
    
    # OpenAI (Primary)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"  # Latest GPT-4o model
    openai_embedding_model: str = "text-embedding-3-large"
    
    # Google Gemini (For comparison)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-pro-latest"
    
    # Vector Database (optional for vector-based approaches)
    chroma_persist_directory: str = "./chroma_db"
    
    # Evaluation settings
    max_concurrent_evaluations: int = 3
    evaluation_timeout_seconds: int = 300
    
    # Cost tracking
    cost_tracking_enabled: bool = True
    monthly_budget_usd: float = 500.0
    
    # Graph-RAG Pipeline Settings
    cypher_generation_temperature: float = 0.1
    vector_retrieval_k: int = 5
    hybrid_alpha: float = 0.7  # Weight for structured vs vector results
    
    # Query Execution Settings
    max_query_complexity: int = 6  # Maximum allowed query complexity (1-5 scale)
    default_query_limit: int = 1000  # Default LIMIT for queries without one
    
    # Vector Pipeline Specific Settings
    vector_chunk_size: int = 512  # Text chunk size for vectorization
    vector_chunk_overlap: int = 50  # Overlap between chunks
    vector_embedding_model: str = "text-embedding-3-large"  # OpenAI embedding model
    vector_similarity_threshold: float = 0.2  # Minimum similarity for retrieval
    vector_max_retrieved_chunks: int = 10  # Maximum chunks to retrieve
    
    # Graph-to-Text Conversion Settings
    graph_to_text_strategy: str = "narrative"  # "triple", "narrative", or "hybrid"
    include_temporal_context: bool = True
    include_spatial_context: bool = True
    include_relationships: bool = True
    max_hops_per_entity: int = 2  # Maximum relationship hops for context
    
    # Vector Database Initialization
    rebuild_vector_db_on_startup: bool = False  # Set to True to rebuild vector DB
    vector_db_collection_name: str = "berlin_transport_graph"
    
    # Historical context settings
    berlin_wall_construction_year: int = 1961
    german_reunification_year: int = 1989
    available_years: List[int] = [1946, 1951, 1956, 1960, 1961, 1964, 1965, 1967, 1971, 1980, 1982, 1984, 1985, 1989]
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }

# Global settings instance
settings = Settings()

# LLM Provider availability check
def get_available_llm_providers() -> List[str]:
    """Return list of available LLM providers based on API keys"""
    providers = []
    
    if settings.mistral_api_key and settings.mistral_base_url:
        providers.append("mistral")
    
    if settings.openai_api_key:
        providers.append("openai")
        
    if settings.gemini_api_key:
        providers.append("gemini")
    
    return providers

# Cost estimation per provider (USD per 1K tokens)
LLM_COSTS = {
    "mistral": {"input": 0.0, "output": 0.0},  # Free university access
    "openai": {"input": 0.01, "output": 0.03},  # GPT-4 Turbo pricing
    "gemini": {"input": 0.00125, "output": 0.00375}  # Gemini 1.5 Pro pricing
}

def estimate_cost(provider: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for a given provider and token usage"""
    if provider not in LLM_COSTS:
        return 0.0
    
    costs = LLM_COSTS[provider]
    return (input_tokens * costs["input"] + output_tokens * costs["output"]) / 1000 