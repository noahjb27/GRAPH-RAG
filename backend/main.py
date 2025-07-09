"""
FastAPI main application for Graph-RAG Research System
Multi-LLM support with comprehensive evaluation framework
"""

import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .config import settings, get_available_llm_providers
from .database.neo4j_client import neo4j_client
from .llm_clients.client_factory import test_client_connectivity, get_all_clients
from .evaluation.evaluator import Evaluator
from .evaluation.question_loader import QuestionLoader
from .evaluation.metrics import MetricsCalculator

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Graph-RAG Research System for Berlin Transport Networks",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
evaluator = Evaluator()
question_loader = QuestionLoader()

# Pydantic models for API requests/responses
class QueryRequest(BaseModel):
    question: str
    pipeline_names: List[str]
    llm_providers: List[str]

class SingleQuestionRequest(BaseModel):
    question_id: str
    pipeline_names: List[str]
    llm_providers: List[str]

class BatchEvaluationRequest(BaseModel):
    pipeline_names: List[str]
    llm_providers: List[str]
    question_count: Optional[int] = 5
    categories: Optional[List[str]] = None
    max_difficulty: Optional[int] = 3

class SystemStatus(BaseModel):
    neo4j_connected: bool
    available_llm_providers: List[str]
    available_pipelines: List[str]
    total_questions: int

# API Routes

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Graph-RAG Research System",
        "description": "Multi-LLM evaluation for Berlin transport networks",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/status", response_model=SystemStatus)
async def system_status():
    """Get system status and availability"""
    
    # Test Neo4j connection
    neo4j_connected = await neo4j_client.test_connection()
    
    # Get available providers and pipelines
    available_providers = get_available_llm_providers()
    available_pipelines = evaluator.get_available_pipelines()
    
    # Get question count
    taxonomy_summary = question_loader.get_taxonomy_summary()
    
    return SystemStatus(
        neo4j_connected=neo4j_connected,
        available_llm_providers=available_providers,
        available_pipelines=available_pipelines,
        total_questions=taxonomy_summary.get("total_questions", 0)
    )

@app.get("/llm-providers")
async def get_llm_providers():
    """Get available LLM providers with connectivity status"""
    
    providers = get_available_llm_providers()
    connectivity = await test_client_connectivity()
    
    provider_info = []
    for provider in providers:
        info = {
            "name": provider,
            "available": provider in connectivity,
            "connected": connectivity.get(provider, False)
        }
        provider_info.append(info)
    
    return {
        "providers": provider_info,
        "total_available": len([p for p in provider_info if p["available"]])
    }

@app.get("/pipelines")
async def get_pipelines():
    """Get available Graph-RAG pipelines"""
    
    pipelines = []
    for pipeline_name, pipeline in evaluator.pipelines.items():
        pipeline_info = {
            "name": pipeline_name,
            "display_name": pipeline.name,
            "description": pipeline.description,
            "required_capabilities": pipeline.get_required_capabilities(),
            "stats": pipeline.get_stats()
        }
        pipelines.append(pipeline_info)
    
    return {"pipelines": pipelines}

@app.get("/questions")
async def get_questions(
    category: Optional[str] = None,
    difficulty: Optional[int] = None,
    limit: Optional[int] = None
):
    """Get evaluation questions with optional filtering"""
    
    if category:
        questions = question_loader.get_questions_by_category(category)
    elif difficulty:
        questions = question_loader.get_questions_by_difficulty(difficulty)
    else:
        questions = question_loader.get_all_questions()
    
    # Apply limit if specified
    if limit and limit > 0:
        questions = questions[:limit]
    
    # Convert to API response format
    question_data = []
    for q in questions:
        question_info = {
            "question_id": q.question_id,
            "question_text": q.question_text,
            "category": q.category,
            "sub_category": q.sub_category,
            "difficulty": q.difficulty,
            "required_capabilities": q.required_capabilities,
            "historical_context": q.historical_context,
            "evaluation_method": q.evaluation_method
        }
        question_data.append(question_info)
    
    return {
        "questions": question_data,
        "total": len(question_data),
        "taxonomy_summary": question_loader.get_taxonomy_summary()
    }

@app.get("/questions/{question_id}")
async def get_question_details(question_id: str):
    """Get detailed information for a specific question"""
    
    question = question_loader.get_question_by_id(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return {
        "question_id": question.question_id,
        "question_text": question.question_text,
        "category": question.category,
        "sub_category": question.sub_category,
        "difficulty": question.difficulty,
        "required_capabilities": question.required_capabilities,
        "ground_truth": question.ground_truth,
        "ground_truth_type": question.ground_truth_type,
        "cypher_query": question.cypher_query,
        "historical_context": question.historical_context,
        "evaluation_method": question.evaluation_method,
        "notes": question.notes
    }

@app.post("/evaluate/question")
async def evaluate_single_question(request: SingleQuestionRequest):
    """Evaluate a single question across selected pipelines and LLM providers"""
    
    try:
        results = await evaluator.evaluate_single_question(
            request.question_id,
            request.pipeline_names,
            request.llm_providers
        )
        
        # Convert results to API response format
        response_data = []
        for result in results:
            result_data = {
                "question_id": result.question_id,
                "question_text": result.question_text,
                "pipeline_name": result.pipeline_name,
                "llm_provider": result.llm_provider,
                "answer": result.answer,
                "success": result.success,
                "execution_time_seconds": result.execution_time_seconds,
                "cost_usd": result.cost_usd,
                "total_tokens": result.total_tokens,
                "tokens_per_second": result.tokens_per_second,
                "generated_cypher": result.generated_cypher,
                "error_message": result.error_message,
                "timestamp": result.timestamp.isoformat() if result.timestamp else None,
                "metadata": result.metadata
            }
            response_data.append(result_data)
        
        # Generate summary
        summary = evaluator.get_evaluation_summary(results)
        
        return {
            "results": response_data,
            "summary": summary,
            "total_evaluations": len(response_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate/sample")
async def evaluate_sample_questions(request: BatchEvaluationRequest):
    """Evaluate sample questions for development testing"""
    
    try:
        results = await evaluator.evaluate_sample_questions(
            request.pipeline_names,
            request.llm_providers,
            request.question_count or 5,
            request.categories,
            request.max_difficulty or 3
        )
        
        # Convert results to API response format
        response_data = []
        for result in results:
            result_data = {
                "question_id": result.question_id,
                "question_text": result.question_text,
                "pipeline_name": result.pipeline_name,
                "llm_provider": result.llm_provider,
                "answer": result.answer,
                "success": result.success,
                "execution_time_seconds": result.execution_time_seconds,
                "cost_usd": result.cost_usd,
                "total_tokens": result.total_tokens,
                "generated_cypher": result.generated_cypher,
                "error_message": result.error_message,
                "metadata": result.metadata
            }
            response_data.append(result_data)
        
        # Generate summary and comparisons
        summary = evaluator.get_evaluation_summary(results)
        pipeline_comparison = MetricsCalculator.compare_pipelines(results)
        llm_comparison = MetricsCalculator.compare_llm_providers(results)
        
        return {
            "results": response_data,
            "summary": summary,
            "pipeline_comparison": pipeline_comparison,
            "llm_comparison": llm_comparison,
            "total_evaluations": len(response_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/database/info")
async def get_database_info():
    """Get Neo4j database information"""
    
    try:
        db_info = await neo4j_client.get_database_info()
        return {
            "database_info": db_info,
            "connection_status": "connected"
        }
    except Exception as e:
        return {
            "database_info": {},
            "connection_status": "error",
            "error": str(e)
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    health_status = {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "components": {}
    }
    
    # Check Neo4j
    try:
        neo4j_connected = await neo4j_client.test_connection()
        health_status["components"]["neo4j"] = "healthy" if neo4j_connected else "unhealthy"
    except Exception as e:
        health_status["components"]["neo4j"] = f"error: {e}"
    
    # Check LLM providers
    try:
        connectivity = await test_client_connectivity()
        health_status["components"]["llm_providers"] = connectivity
    except Exception as e:
        health_status["components"]["llm_providers"] = f"error: {e}"
    
    return health_status

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    print(f"Starting {settings.app_name}")
    
    # Connect to Neo4j
    try:
        await neo4j_client.connect()
        print("✓ Neo4j connection established")
    except Exception as e:
        print(f"✗ Neo4j connection failed: {e}")
    
    # Test LLM providers
    try:
        connectivity = await test_client_connectivity()
        available_providers = [p for p, status in connectivity.items() if status]
        print(f"✓ Available LLM providers: {available_providers}")
    except Exception as e:
        print(f"✗ LLM provider test failed: {e}")
    
    print(f"✓ Server ready on {settings.host}:{settings.backend_port}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("Shutting down...")
    
    try:
        await neo4j_client.close()
        print("✓ Neo4j connection closed")
    except Exception as e:
        print(f"✗ Error closing Neo4j: {e}")

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.backend_port,
        reload=settings.debug,
        log_level="info"
    ) 