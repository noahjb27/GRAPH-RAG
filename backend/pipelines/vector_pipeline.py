"""
Vector-based Pipeline - Graph-to-text conversion with vector similarity retrieval
Full implementation with ChromaDB and OpenAI embeddings
"""

import time
import re
from typing import List, Optional, Dict, Any
from .base_pipeline import BasePipeline, PipelineResult
from .vector_database import VectorDatabaseManager, VectorSearchResult, get_vector_database_manager
from .vector_indexing import VectorIndexingService, get_vector_indexing_service
from ..llm_clients.client_factory import create_llm_client
from ..database.neo4j_client import neo4j_client
from ..config import settings

class VectorPipeline(BasePipeline):
    """
    Vector-based RAG pipeline implementation
    
    Process:
    1. Convert user question to vector embedding
    2. Retrieve relevant text chunks from vector database
    3. Construct context from retrieved chunks
    4. Generate answer using LLM with retrieved context
    """
    
    def __init__(self):
        super().__init__(
            name="Vector-based RAG", 
            description="Graph-to-text conversion with vector similarity retrieval"
        )
        
        self.vector_db = get_vector_database_manager()
        self.indexing_service = None
        self._is_initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the vector pipeline"""
        
        if self._is_initialized:
            return True
            
        try:
            # Get the indexing service (this will also initialize vector DB)
            self.indexing_service = await get_vector_indexing_service(neo4j_client)
            
            # Initialize vector database
            success = await self.vector_db.initialize()
            if not success:
                print("Failed to initialize vector database for pipeline")
                return False
            
            # Check if vector database is populated
            stats = await self.indexing_service.get_indexing_status()
            if not stats.get("is_indexed", False):
                print("Vector database is not populated. Consider running indexing first.")
                # You can choose to auto-index here or require manual indexing
                # For now, we'll warn but continue
            
            self._is_initialized = True
            print("Vector pipeline initialized successfully")
            return True
            
        except Exception as e:
            print(f"Failed to initialize vector pipeline: {e}")
            return False
    
    async def process_query(
        self,
        question: str,
        llm_provider: str = "mistral",
        **kwargs
    ) -> PipelineResult:
        """Process a natural language question using Vector RAG approach"""
        
        start_time = time.time()
        
        try:
            # Ensure pipeline is initialized
            if not self._is_initialized:
                await self.initialize()
            
            # Step 1: Get LLM client
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
            
            # Step 2: Extract query context for filtering
            query_context = self._analyze_question_context(question)
            
            # Step 3: Retrieve relevant chunks from vector database
            retrieved_chunks = await self._retrieve_relevant_chunks(question, query_context)
            
            if not retrieved_chunks:
                return PipelineResult(
                    answer="I couldn't find relevant information in the database to answer your question.",
                    approach=self.name,
                    llm_provider=llm_provider,
                    execution_time_seconds=time.time() - start_time,
                    success=False,
                    error_message="No relevant chunks retrieved",
                    error_stage="vector_retrieval",
                    retrieved_context=[]
                )
            
            # Step 4: Construct context from retrieved chunks
            context = self._construct_context_from_chunks(retrieved_chunks)
            
            # Step 5: Generate answer using LLM with context
            answer_response = await self._generate_answer_with_context(
                question, context, llm_client
            )
            
            execution_time = time.time() - start_time
            
            # Extract just the content strings for the result
            retrieved_context = [chunk.content for chunk in retrieved_chunks]
            
            result = PipelineResult(
                answer=answer_response.text if answer_response and answer_response.text.strip() else "Unable to generate answer",
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=bool(answer_response and answer_response.text.strip()),
                retrieved_context=retrieved_context,
                llm_response=answer_response,
                metadata={
                    "chunks_retrieved": len(retrieved_chunks),
                    "avg_similarity_score": sum(chunk.similarity_score for chunk in retrieved_chunks) / len(retrieved_chunks),
                    "temporal_coverage": list(set(chunk.temporal_context for chunk in retrieved_chunks if chunk.temporal_context)),
                    "spatial_coverage": list(set(chunk.spatial_context for chunk in retrieved_chunks if chunk.spatial_context)),
                    "entity_types_covered": list(set(chunk.metadata.get("entity_type") for chunk in retrieved_chunks)),
                    "query_context": query_context
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
                error_stage="unknown"
            )
            self.update_stats(result)
            return result
    
    def _analyze_question_context(self, question: str) -> Dict[str, Any]:
        """Analyze the question to extract temporal, spatial, and entity contexts"""
        
        context = {
            "temporal": {},
            "spatial": {},
            "entities": {},
            "transport_types": []
        }
        
        question_lower = question.lower()
        
        # Extract years and temporal references
        year_pattern = r'\b(19[4-9]\d|196[0-9]|197[0-9]|198[0-9])\b'
        years = re.findall(year_pattern, question)
        if years:
            context["temporal"]["years"] = [int(year) for year in years]
        
        # Temporal keywords
        temporal_keywords = {
            "before": "before",
            "after": "after", 
            "during": "during",
            "between": "range",
            "wall": "berlin_wall_period",
            "unified": "unified_period",
            "divided": "divided_period"
        }
        
        for keyword, temporal_type in temporal_keywords.items():
            if keyword in question_lower:
                context["temporal"][temporal_type] = True
        
        # Extract spatial references
        spatial_keywords = {
            "west berlin": "west",
            "east berlin": "east", 
            "berlin": "berlin",
            "district": "district",
            "area": "area",
            "neighborhood": "neighborhood"
        }
        
        for keyword, spatial_type in spatial_keywords.items():
            if keyword in question_lower:
                context["spatial"][spatial_type] = True
        
        # Extract transport types
        transport_types = ["tram", "bus", "u-bahn", "s-bahn", "omnibus", "ferry", "autobus"]
        for transport_type in transport_types:
            if transport_type in question_lower:
                context["transport_types"].append(transport_type)
        
        # Extract entity references
        if "station" in question_lower:
            context["entities"]["station"] = True
        if "line" in question_lower:
            context["entities"]["line"] = True
        if "frequency" in question_lower:
            context["entities"]["frequency"] = True
        if "capacity" in question_lower:
            context["entities"]["capacity"] = True
        
        return context
    
    async def _retrieve_relevant_chunks(
        self, 
        question: str, 
        query_context: Dict[str, Any]
    ) -> List[VectorSearchResult]:
        """Retrieve relevant chunks using vector similarity and context filtering"""
        
        try:
            # Start with basic vector similarity search
            base_results = await self.vector_db.search_similar(
                question, 
                k=settings.vector_max_retrieved_chunks * 2  # Get more for filtering
            )
            
            # Apply temporal filtering if temporal context exists
            if query_context.get("temporal", {}).get("years"):
                years = query_context["temporal"]["years"]
                temporal_results = []
                
                for year in years:
                    year_results = await self.vector_db.search_with_temporal_filter(
                        question, year=year
                    )
                    temporal_results.extend(year_results)
                
                # Combine and deduplicate
                base_results.extend(temporal_results)
                base_results = self._deduplicate_results(base_results)
            
            # Apply spatial filtering if spatial context exists
            if query_context.get("spatial", {}).get("west") or query_context.get("spatial", {}).get("east"):
                political_side = "west" if query_context["spatial"].get("west") else "east"
                spatial_results = await self.vector_db.search_with_spatial_filter(
                    question, political_side=political_side
                )
                
                # Prefer spatially filtered results
                base_results = spatial_results + base_results
                base_results = self._deduplicate_results(base_results)
            
            # Filter by transport type if specified
            if query_context.get("transport_types"):
                filtered_results = []
                transport_types = query_context["transport_types"]
                
                for result in base_results:
                    result_transport_type = result.metadata.get("transport_type", "").lower()
                    if any(t_type in result_transport_type for t_type in transport_types):
                        filtered_results.append(result)
                
                # If we have transport-specific results, prefer them
                if filtered_results:
                    base_results = filtered_results + base_results
                    base_results = self._deduplicate_results(base_results)
            
            # Return top results respecting the configured limit
            return base_results[:settings.vector_max_retrieved_chunks]
            
        except Exception as e:
            print(f"Error retrieving chunks: {e}")
            return []
    
    def _deduplicate_results(self, results: List[VectorSearchResult]) -> List[VectorSearchResult]:
        """Remove duplicate results based on chunk ID"""
        
        seen_ids = set()
        deduplicated = []
        
        for result in results:
            if result.chunk_id not in seen_ids:
                seen_ids.add(result.chunk_id)
                deduplicated.append(result)
        
        return deduplicated
    
    def _construct_context_from_chunks(self, chunks: List[VectorSearchResult]) -> str:
        """Construct a coherent context string from retrieved chunks"""
        
        if not chunks:
            return ""
        
        # Sort chunks by similarity score (highest first)
        sorted_chunks = sorted(chunks, key=lambda x: x.similarity_score, reverse=True)
        
        context_parts = []
        context_parts.append("Based on the available information about Berlin's historical transport network:")
        context_parts.append("")
        
        # Group chunks by type for better organization
        entity_groups = {}
        for chunk in sorted_chunks:
            entity_type = chunk.metadata.get("entity_type", "general")
            if entity_type not in entity_groups:
                entity_groups[entity_type] = []
            entity_groups[entity_type].append(chunk)
        
        # Present information in logical order
        type_order = ["temporal_snapshot", "station", "line", "administrative_area", "relationship"]
        
        for entity_type in type_order:
            if entity_type in entity_groups:
                chunks_of_type = entity_groups[entity_type]
                
                # Add section header
                if entity_type == "temporal_snapshot":
                    context_parts.append("Network Overview:")
                elif entity_type == "station":
                    context_parts.append("Station Information:")
                elif entity_type == "line":
                    context_parts.append("Line Information:")
                elif entity_type == "administrative_area":
                    context_parts.append("Administrative Areas:")
                elif entity_type == "relationship":
                    context_parts.append("Connections:")
                
                # Add content
                for chunk in chunks_of_type[:3]:  # Limit per section
                    context_parts.append(f"- {chunk.content}")
                
                context_parts.append("")
        
        # Add any remaining chunks not in the main categories
        remaining_chunks = []
        for entity_type, chunks_of_type in entity_groups.items():
            if entity_type not in type_order:
                remaining_chunks.extend(chunks_of_type)
        
        if remaining_chunks:
            context_parts.append("Additional Information:")
            for chunk in remaining_chunks[:2]:
                context_parts.append(f"- {chunk.content}")
        
        return "\n".join(context_parts)
    
    async def _generate_answer_with_context(
        self,
        question: str,
        context: str,
        llm_client
    ):
        """Generate an answer using the LLM with retrieved context"""
        
        system_prompt = """You are an expert historian specializing in Berlin's public transportation system from 1946-1989. You have access to detailed historical data about stations, lines, administrative areas, and the evolution of the transport network.

Your task is to answer questions about Berlin's transport network using the provided context information. Be precise, factual, and cite specific details from the context when possible.

Guidelines:
- Use specific numbers, dates, and names from the context
- Acknowledge the historical period (1946-1989) and political context (East/West Berlin division after 1961)
- If the context doesn't contain enough information, say so clearly
- Be concise but informative
- Use past tense when describing historical facts"""
        
        user_prompt = f"""Please answer the following question about Berlin's historical transport network based on the provided context:

QUESTION: {question}

CONTEXT:
{context}

Please provide a clear, factual answer based on the information available in the context."""
        
        return await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,  # Low temperature for factual responses
            max_tokens=500
        )
    
    def get_required_capabilities(self) -> List[str]:
        """Return required capabilities"""
        return [
            "vector_retrieval", 
            "text_embedding", 
            "similarity_search",
            "graph_to_text_conversion",
            "temporal_filtering",
            "spatial_filtering"
        ]
    
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get status information about the vector pipeline"""
        
        if not self._is_initialized or not self.indexing_service:
            return {"status": "not_initialized"}
        
        try:
            # Get indexing status
            indexing_status = await self.indexing_service.get_indexing_status()
            
            # Get vector database stats
            db_stats = await self.vector_db.get_collection_stats()
            
            # Get pipeline stats
            pipeline_stats = self.get_stats()
            
            return {
                "status": "initialized" if self._is_initialized else "not_initialized",
                "indexing_status": indexing_status,
                "vector_db_stats": db_stats,
                "pipeline_stats": pipeline_stats,
                "configuration": {
                    "chunk_size": settings.vector_chunk_size,
                    "embedding_model": settings.vector_embedding_model,
                    "similarity_threshold": settings.vector_similarity_threshold,
                    "max_retrieved_chunks": settings.vector_max_retrieved_chunks,
                    "graph_to_text_strategy": settings.graph_to_text_strategy
                }
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)} 