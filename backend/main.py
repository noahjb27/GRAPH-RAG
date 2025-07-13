"""
FastAPI main application for Graph-RAG Research System
Multi-LLM support with comprehensive evaluation framework
"""

import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
import json

from .config import settings, get_available_llm_providers
from .database.neo4j_client import neo4j_client
from .llm_clients.client_factory import test_client_connectivity, get_all_clients
from .evaluation.evaluator import Evaluator
from .evaluation.question_loader import QuestionLoader
from .evaluation.metrics import MetricsCalculator
from .pipelines.vector_indexing import get_vector_indexing_service
from .pipelines.chatbot_pipeline import ChatbotPipeline
from .pipelines.graphrag_transport_pipeline import GraphRAGTransportPipeline
from .pipelines.graphrag_cache import graphrag_cache

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Graph-RAG Research System for Berlin transport networks",
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
vector_indexing_service = None
chatbot_pipeline = ChatbotPipeline()

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
    vector_pipeline_status: Optional[str] = None

class VectorIndexingRequest(BaseModel):
    force_rebuild: bool = False
    entity_type: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"
    llm_provider: Optional[str] = "openai"
    stream: Optional[bool] = False

class ChatMessage(BaseModel):
    message: str
    is_streaming: bool = False
    query_type: str = "unknown"
    used_database: bool = False
    suggested_questions: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class GraphRAGRequest(BaseModel):
    question: str
    llm_provider: Optional[str] = "openai"
    year_filter: Optional[int] = None
    community_types: Optional[List[str]] = None

class GraphRAGCacheRequest(BaseModel):
    action: str  # "warm", "clear", "stats", "validate"
    cache_type: Optional[str] = "all"  # "all", "communities", "summaries"

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
    
    # Get vector pipeline status
    vector_status = "not_initialized"
    if vector_indexing_service:
        try:
            status_info = await vector_indexing_service.get_indexing_status()
            vector_status = status_info.get("status", "unknown")
        except Exception:
            vector_status = "error"
    
    return SystemStatus(
        neo4j_connected=neo4j_connected,
        available_llm_providers=available_providers,
        available_pipelines=available_pipelines,
        total_questions=taxonomy_summary.get("total_questions", 0),
        vector_pipeline_status=vector_status
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

    # GraphRAG Transport Pipeline Endpoints

@app.post("/graphrag/query")
async def graphrag_query(request: GraphRAGRequest):
    """Process a question using GraphRAG transport pipeline"""
    try:
        pipeline = GraphRAGTransportPipeline()
        
        result = await pipeline.process_query(
            question=request.question,
            llm_provider=request.llm_provider or "openai",
            year_filter=request.year_filter,
            community_types=request.community_types
        )
        
        return {
            "success": result.success,
            "answer": result.answer,
            "approach": result.approach,
            "execution_time_seconds": result.execution_time_seconds,
            "communities_analyzed": result.metadata.get("communities_analyzed", 0) if result.metadata else 0,
            "question_type": result.metadata.get("question_type", "unknown") if result.metadata else "unknown",
            "year_filter": request.year_filter,
            "community_types": request.community_types,
            "context_summaries_count": len(result.retrieved_context) if result.retrieved_context else 0,
            "metadata": result.metadata
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GraphRAG query failed: {str(e)}")

@app.get("/graphrag/cache/stats")
async def get_graphrag_cache_stats():
    """Get GraphRAG cache statistics"""
    try:
        stats = await graphrag_cache.get_cache_stats()
        return {
            "success": True,
            "cache_stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@app.post("/graphrag/cache/manage")
async def manage_graphrag_cache(request: GraphRAGCacheRequest, background_tasks: BackgroundTasks):
    """Manage GraphRAG cache (warm, clear, validate)"""
    try:
        if request.action == "stats":
            stats = await graphrag_cache.get_cache_stats()
            return {"success": True, "action": "stats", "result": stats}
        
        elif request.action == "clear":
            await graphrag_cache.clear_cache(request.cache_type or "all")
            return {"success": True, "action": "clear", "cache_type": request.cache_type}
        
        elif request.action == "validate":
            # Run validation in background to avoid timeout
            background_tasks.add_task(validate_cache_background)
            return {"success": True, "action": "validate", "message": "Cache validation started in background"}
        
        elif request.action == "warm":
            # Run cache warming in background to avoid timeout
            background_tasks.add_task(warm_cache_background)
            return {"success": True, "action": "warm", "message": "Cache warming started in background"}
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache management failed: {str(e)}")

async def warm_cache_background():
    """Background task for cache warming"""
    try:
        from .pipelines.graphrag_transport_pipeline import (
            TransportCommunityDetector, 
            TransportCommunitySummarizer
        )
        
        detector = TransportCommunityDetector(neo4j_client)
        summarizer = TransportCommunitySummarizer("openai")
        
        # Warm cache with common queries
        year_filters = [None, 1961, 1970, 1989]
        community_type_combinations = [None, ["geographic"], ["temporal"]]
        llm_providers = ["openai"]
        
        await graphrag_cache.warm_cache(
            detector, summarizer, year_filters, community_type_combinations, llm_providers
        )
        print("✅ GraphRAG cache warming completed in background")
    
    except Exception as e:
        print(f"❌ GraphRAG cache warming failed: {e}")

async def validate_cache_background():
    """Background task for cache validation"""
    try:
        stats = await graphrag_cache.get_cache_stats()
        print(f"✅ GraphRAG cache validation completed: {stats}")
    except Exception as e:
        print(f"❌ GraphRAG cache validation failed: {e}")

    # Vector Pipeline Management Endpoints

@app.get("/vector-pipeline/status")
async def get_vector_pipeline_status():
    """Get detailed status of the vector pipeline"""
    
    if not vector_indexing_service:
        return {"status": "not_initialized", "error": "Vector indexing service not initialized"}
    
    try:
        status = await vector_indexing_service.get_indexing_status()
        return status
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/vector-pipeline/index")
async def trigger_vector_indexing(request: VectorIndexingRequest, background_tasks: BackgroundTasks):
    """Trigger vector database indexing"""
    
    if not vector_indexing_service:
        raise HTTPException(status_code=503, detail="Vector indexing service not initialized")
    
    try:
        if request.entity_type:
            # Incremental update
            background_tasks.add_task(
                vector_indexing_service.incremental_update, 
                request.entity_type
            )
            return {
                "message": f"Started incremental indexing for entity type: {request.entity_type}",
                "type": "incremental"
            }
        else:
            # Full reindex
            background_tasks.add_task(
                vector_indexing_service.full_reindex,
                request.force_rebuild
            )
            return {
                "message": "Started full vector database indexing",
                "type": "full",
                "force_rebuild": request.force_rebuild
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vector-pipeline/test")
async def test_vector_retrieval(query: str = "Berlin transport stations"):
    """Test vector retrieval with a sample query"""
    
    if not vector_indexing_service:
        raise HTTPException(status_code=503, detail="Vector indexing service not initialized")
    
    try:
        results = await vector_indexing_service.test_retrieval(query)
        
        # Format results for API response
        formatted_results = []
        for result in results:
            formatted_results.append({
                "chunk_id": result.chunk_id,
                "content": result.content[:200] + "..." if len(result.content) > 200 else result.content,
                "similarity_score": result.similarity_score,
                "entity_type": result.metadata.get("entity_type", "unknown"),
                "temporal_context": result.temporal_context,
                "spatial_context": result.spatial_context
            })
        
        return {
            "query": query,
            "results": formatted_results,
            "total_results": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vector-pipeline/debug-index")
async def debug_vector_indexing(request: VectorIndexingRequest):
    """Debug indexing - runs synchronously to show errors"""
    
    if not vector_indexing_service:
        raise HTTPException(status_code=503, detail="Vector indexing service not initialized")
    
    try:
        print("Starting debug indexing...")
        
        if request.entity_type:
            # Incremental update
            stats = await vector_indexing_service.incremental_update(request.entity_type)
        else:
            # Full reindex
            stats = await vector_indexing_service.full_reindex(request.force_rebuild)
        
        return {
            "success": True,
            "stats": {
                "total_chunks_created": stats.total_chunks_created,
                "total_chunks_indexed": stats.total_chunks_indexed,
                "indexing_time_seconds": stats.indexing_time_seconds,
                "chunks_per_second": stats.chunks_per_second,
                "entity_type_breakdown": stats.entity_type_breakdown,
                "temporal_coverage": stats.temporal_coverage,
                "spatial_coverage": stats.spatial_coverage,
                "errors": stats.errors
            }
        }
    except Exception as e:
        print(f"Debug indexing error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vector/debug-comprehensive-index")
async def debug_comprehensive_index():
    """Debug endpoint: Comprehensive reindex with text file export"""
    
    try:
        indexing_service = await get_vector_indexing_service(neo4j_client)
        
        # Perform comprehensive reindex with chunk export
        stats = await indexing_service.full_reindex(force=True, export_chunks=True)
        
        return {
            "success": True,
            "message": "Comprehensive indexing completed with text file export",
            "stats": {
                "total_chunks_created": stats.total_chunks_created,
                "total_chunks_indexed": stats.total_chunks_indexed,
                "indexing_time_seconds": stats.indexing_time_seconds,
                "chunks_per_second": stats.chunks_per_second,
                "entity_type_breakdown": stats.entity_type_breakdown,
                "temporal_coverage": stats.temporal_coverage[:10],  # First 10 years
                "spatial_coverage": stats.spatial_coverage[:10],   # First 10 areas
                "errors": stats.errors
            },
            "export_info": {
                "export_directory": "chunk_exports",
                "check_files": [
                    "chunk_exports/SUMMARY.txt",
                    "chunk_exports/station_property_chunks.txt",
                    "chunk_exports/line_property_chunks.txt",
                    "chunk_exports/relationship_chunks.txt",
                    "chunk_exports/triple_chunks.txt"
                ]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to perform comprehensive indexing"
        }

@app.post("/api/vector/complete-indexing")
async def complete_indexing():
    """Complete indexing of remaining chunks without clearing existing data"""
    
    try:
        indexing_service = await get_vector_indexing_service(neo4j_client)
        
        # Get current status
        current_status = await indexing_service.get_indexing_status()
        current_chunks = current_status.get("vector_db_stats", {}).get("total_chunks", 0)
        
        # Perform indexing without clearing existing data (force=False)
        stats = await indexing_service.full_reindex(force=False, export_chunks=False)
        
        return {
            "success": True,
            "message": "Completed indexing of remaining chunks",
            "before_indexing": current_chunks,
            "stats": {
                "total_chunks_created": stats.total_chunks_created,
                "total_chunks_indexed": stats.total_chunks_indexed,
                "indexing_time_seconds": stats.indexing_time_seconds,
                "chunks_per_second": stats.chunks_per_second,
                "entity_type_breakdown": stats.entity_type_breakdown,
                "errors": stats.errors
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to complete indexing"
        }

# Chat endpoints
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Non-streaming chat endpoint"""
    
    try:
        # Get single response from chatbot
        response_generator = chatbot_pipeline.chat_response(
            message=request.message,
            session_id=request.session_id or "default",
            llm_provider=request.llm_provider or "openai",
            stream=False
        )
        
        # Get the final response
        final_response = None
        async for response in response_generator:
            final_response = response
        
        if final_response is None:
            raise HTTPException(status_code=500, detail="No response generated")
        
        return ChatMessage(
            message=final_response.message,
            is_streaming=False,
            query_type=final_response.query_type,
            used_database=final_response.used_database,
            suggested_questions=final_response.suggested_questions,
            metadata=final_response.metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """Streaming chat endpoint using Server-Sent Events"""
    
    async def generate_stream():
        """Generate streaming response"""
        try:
            response_generator = chatbot_pipeline.chat_response(
                message=request.message,
                session_id=request.session_id or "default",
                llm_provider=request.llm_provider or "openai",
                stream=True
            )
            
            async for response in response_generator:
                # Format as Server-Sent Event
                chat_data = {
                    "message": response.message,
                    "is_streaming": response.is_streaming,
                    "query_type": response.query_type,
                    "used_database": response.used_database,
                    "suggested_questions": response.suggested_questions,
                    "metadata": response.metadata
                }
                
                # Send as SSE format
                yield f"data: {json.dumps(chat_data)}\n\n"
            
            # Send end marker
            yield f"data: {json.dumps({'type': 'end'})}\n\n"
            
        except Exception as e:
            # Send error
            error_data = {
                "type": "error",
                "message": f"Error: {str(e)}",
                "query_type": "error",
                "used_database": False
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.get("/chat/sessions/{session_id}")
async def get_chat_session(session_id: str):
    """Get conversation history for a session"""
    
    context = chatbot_pipeline.get_conversation_context(session_id)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "message_count": len(context.history),
        "history": context.history[-10:],  # Last 10 messages
        "last_query_type": context.last_query_type,
        "last_entities": context.last_entities
    }

@app.delete("/chat/sessions/{session_id}")
async def clear_chat_session(session_id: str):
    """Clear conversation history for a session"""
    
    chatbot_pipeline.clear_conversation_context(session_id)
    return {"message": f"Session {session_id} cleared"}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    global vector_indexing_service
    
    print(f"Starting {settings.app_name}")
    
    # Connect to Neo4j
    try:
        await neo4j_client.connect()
        print("✓ Neo4j connection established")
    except Exception as e:
        print(f"✗ Neo4j connection failed: {e}")
    
    # Initialize Vector Indexing Service
    try:
        vector_indexing_service = await get_vector_indexing_service(neo4j_client)
        print("✓ Vector indexing service initialized")
        
        # Check if vector database needs initial indexing
        status = await vector_indexing_service.get_indexing_status()
        if not status.get("is_indexed", False):
            print("⚠ Vector database is empty. Run /vector-pipeline/index to populate it.")
        else:
            db_stats = status.get("vector_db_stats", {})
            total_chunks = db_stats.get("total_chunks", 0)
            print(f"✓ Vector database loaded with {total_chunks} chunks")
            
    except Exception as e:
        print(f"✗ Vector indexing service initialization failed: {e}")
        vector_indexing_service = None
    
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
    
    # Cleanup vector indexing service
    if vector_indexing_service:
        try:
            await vector_indexing_service.cleanup()
            print("✓ Vector indexing service cleaned up")
        except Exception as e:
            print(f"✗ Error cleaning up vector service: {e}")
    
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