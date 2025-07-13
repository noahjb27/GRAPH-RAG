"""
Graph Embedding Pipeline - Topological Similarity Retrieval
Uses Node2Vec embeddings and FAISS search for structural similarity
"""

import time
import re
from typing import List, Optional, Dict, Any, Tuple
from .base_pipeline import BasePipeline, PipelineResult
from .node_embedding_service import (
    NodeEmbeddingService, EmbeddingTrainingConfig, 
    get_node_embedding_service
)
from .graph_vector_index import (
    GraphVectorIndexService, SearchResult,
    get_graph_vector_index_service
)
from .graph_preprocessing import (
    GraphPreprocessingService, get_graph_preprocessing_service
)
from ..llm_clients.client_factory import create_llm_client
from ..database.neo4j_client import neo4j_client
from ..config import settings

class GraphEmbeddingPipeline(BasePipeline):
    """
    Graph Embedding Pipeline for topological similarity retrieval
    
    Process:
    1. Train/load node embeddings using Node2Vec
    2. Create FAISS index for fast similarity search
    3. Embed user query using sentence transformers
    4. Find structurally similar nodes via vector search
    5. Retrieve local neighborhoods around similar nodes
    6. Generate answer using LLM with retrieved context
    """
    
    def __init__(self):
        super().__init__(
            name="Graph Embedding",
            description="Topological similarity retrieval using Node2Vec embeddings"
        )
        
        self.embedding_service = get_node_embedding_service()
        self.index_service = get_graph_vector_index_service()
        self.graph_preprocessing = get_graph_preprocessing_service()
        
        # Initialize with default configuration
        self.embedding_config = EmbeddingTrainingConfig(
            dimensions=128,
            walk_length=80,
            num_walks=10,
            p=1.0,  # Balanced exploration
            q=1.0,  # Balanced exploration
            neighborhood_hops=2,
            max_neighbors=50
        )
        
        # Cache for embeddings and indices
        self._embeddings_cache = {}
        self._index_cache = {}
        self._graph_cache = {}
        
        # Common Berlin location patterns for anchor detection
        self.location_patterns = [
            r'\b([A-ZÄÖÜ][a-zäöü]+(?:\s+[A-ZÄÖÜ][a-zäöü]+)*(?:platz|straße|str\.|bahnhof|station|bf\.?))\b',
            r'\b([A-ZÄÖÜ][a-zäöü]+(?:\s+[A-ZÄÖÜ][a-zäöü]+)*(?:berg|burg|dorf|felde|hagen|hof|ow|stedt|thal|wald|werder))\b',
            r'\b(U\d+|S\d+|Bus\s+\d+|Linie\s+\d+)\b'
        ]
        
    async def process_query(
        self,
        question: str,
        llm_provider: str = "mistral",
        year_filter: Optional[int] = None,
        max_results: int = 10,
        re_rank: bool = True,
        semantic_weight: float = 0.6,
        structural_weight: float = 0.4,
        **kwargs
    ) -> PipelineResult:
        """Process a question using graph embedding similarity search"""
        
        start_time = time.time()
        
        try:
            # Step 1: Ensure embeddings and index are ready
            cache_key = f"year_{year_filter}"
            if cache_key not in self._embeddings_cache:
                await self._initialize_embeddings_and_index(year_filter, cache_key)
            
            embedding_result = self._embeddings_cache[cache_key]
            index_result = self._index_cache[cache_key]
            graph_result = self._graph_cache[cache_key]
            
            # Step 2: Embed the query
            target_dimensions = embedding_result.training_config.dimensions
            query_embedding = self.embedding_service.embed_query(question, target_dimensions)
            
            # Step 3: Detect anchor nodes in the question (for hybrid search)
            anchor_nodes = await self._detect_anchor_nodes(question, graph_result, year_filter)
            
            # Step 4: Perform similarity search
            if anchor_nodes and re_rank:
                # Hybrid search: combine semantic and structural similarity
                search_results = self.index_service.search_hybrid(
                    query_embedding,
                    anchor_nodes,
                    index_result,
                    graph_result,
                    semantic_weight=semantic_weight,
                    structural_weight=structural_weight,
                    top_k=max_results
                )
            else:
                # Pure semantic search
                search_results = self.index_service.search_similar_nodes(
                    query_embedding,
                    index_result,
                    graph_result,
                    top_k=max_results
                )
            
            # Step 5: Apply metadata filters if specified
            filters = self._extract_filters_from_question(question)
            if filters:
                search_results = self.index_service.filter_results_by_metadata(
                    search_results, filters
                )
            
            # Step 6: Retrieve local neighborhoods around similar nodes
            context = await self._build_context_from_results(
                search_results, graph_result, year_filter
            )
            
            # Step 7: Generate answer using LLM
            answer = await self._generate_answer(
                question, context, llm_provider, search_results, embedding_result
            )
            
            execution_time = time.time() - start_time
            
            return PipelineResult(
                answer=answer,
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=True,
                retrieved_context=[context],
                metadata={
                    "search_results_count": len(search_results),
                    "anchor_nodes": anchor_nodes,
                    "filters_applied": filters,
                    "embedding_dimensions": embedding_result.training_config.dimensions,
                    "semantic_weight": semantic_weight,
                    "structural_weight": structural_weight,
                    "year_filter": year_filter
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return PipelineResult(
                answer=f"I encountered an error while processing your question: {str(e)}",
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=False,
                error_message=str(e),
                error_stage="graph_embedding_processing"
            )
    
    async def _initialize_embeddings_and_index(self, year_filter: Optional[int], cache_key: str):
        """Initialize embeddings and index for given year filter"""
        
        print(f"Initializing embeddings and index for {cache_key}")
        
        # Extract graph
        graph_result = await self.graph_preprocessing.extract_transport_network(
            year_filter=year_filter,
            include_administrative=True,
            include_temporal=False
        )
        
        # Train embeddings
        embedding_result = await self.embedding_service.train_embeddings(
            self.embedding_config,
            year_filter=year_filter,
            include_administrative=True
        )
        
        # Create vector index
        index_result = self.index_service.create_index(
            embedding_result, graph_result, index_type="flat"
        )
        
        # Cache results
        self._embeddings_cache[cache_key] = embedding_result
        self._index_cache[cache_key] = index_result
        self._graph_cache[cache_key] = graph_result
        
        print(f"Initialized embeddings for {len(embedding_result.embeddings)} nodes")
    
    async def _detect_anchor_nodes(
        self,
        question: str,
        graph_result,
        year_filter: Optional[int]
    ) -> List[str]:
        """Detect anchor nodes mentioned in the question"""
        
        detected_entities = []
        
        # Use regex patterns to find potential entities
        for pattern in self.location_patterns:
            matches = re.finditer(pattern, question, re.IGNORECASE)
            for match in matches:
                detected_entities.append(match.group(1))
        
        # Find corresponding nodes in the graph
        anchor_nodes = []
        for entity in detected_entities:
            # Search in node attributes
            for node_id, attributes in graph_result.node_attributes.items():
                node_name = attributes.get("name", "").lower()
                if entity.lower() in node_name or node_name in entity.lower():
                    anchor_nodes.append(node_id)
                    break
        
        return anchor_nodes[:5]  # Limit to 5 anchors
    
    def _extract_filters_from_question(self, question: str) -> Dict[str, Any]:
        """Extract metadata filters from the question"""
        
        filters = {}
        question_lower = question.lower()
        
        # Transport type filters
        if "station" in question_lower:
            filters["is_station"] = True
        elif "line" in question_lower:
            filters["is_line"] = True
        
        # Political side filters
        if "west" in question_lower and "east" not in question_lower:
            filters["political_side"] = "west"
        elif "east" in question_lower and "west" not in question_lower:
            filters["political_side"] = "east"
        
        # Transport mode filters
        transport_types = ["u-bahn", "s-bahn", "tram", "bus", "omnibus"]
        for transport_type in transport_types:
            if transport_type in question_lower:
                filters["type"] = transport_type
                break
        
        return filters
    
    async def _build_context_from_results(
        self,
        search_results: List[SearchResult],
        graph_result,
        year_filter: Optional[int]
    ) -> str:
        """Build context from search results by retrieving neighborhoods"""
        
        if not search_results:
            return "No relevant nodes found in the graph."
        
        context_parts = []
        context_parts.append("=== STRUCTURALLY SIMILAR ENTITIES ===")
        
        for i, result in enumerate(search_results[:10], 1):
            # Get node attributes
            attrs = result.node_attributes or {}
            name = attrs.get("name", "Unknown")
            node_type = attrs.get("type", "Unknown")
            political_side = attrs.get("political_side", "")
            
            context_parts.append(f"\n{i}. {name} (similarity: {result.similarity_score:.3f})")
            context_parts.append(f"   Type: {node_type}")
            if political_side:
                context_parts.append(f"   Political side: {political_side}")
            
            # Add location info if available
            lat = attrs.get("latitude")
            lon = attrs.get("longitude")
            if lat and lon:
                context_parts.append(f"   Location: {lat:.4f}, {lon:.4f}")
            
            # Add operational info for lines
            if attrs.get("is_line"):
                frequency = attrs.get("frequency")
                capacity = attrs.get("capacity")
                if frequency:
                    context_parts.append(f"   Frequency: {frequency} minutes")
                if capacity:
                    context_parts.append(f"   Capacity: {capacity} passengers")
        
        # Add summary
        context_parts.append(f"\n=== SEARCH SUMMARY ===")
        context_parts.append(f"Found {len(search_results)} structurally similar entities")
        if year_filter:
            context_parts.append(f"Filtered to year: {year_filter}")
        
        # Add topological explanation
        context_parts.append("\n=== METHODOLOGY ===")
        context_parts.append("Results found using topological similarity search:")
        context_parts.append("- Nodes with similar structural roles in the transport network")
        context_parts.append("- Based on connection patterns and neighborhood structure")
        context_parts.append("- Ranked by vector similarity in embedding space")
        
        return "\n".join(context_parts)
    
    async def _generate_answer(
        self,
        question: str,
        context: str,
        llm_provider: str,
        search_results: List[SearchResult],
        embedding_result
    ) -> str:
        """Generate natural language answer using LLM"""
        
        prompt = f"""You are analyzing Berlin's historical transport network using graph embedding similarity search.

QUESTION: {question}

CONTEXT FROM TOPOLOGICAL SIMILARITY SEARCH:
{context}

Based on the structurally similar entities found through graph embeddings, provide a comprehensive answer to the question. 

Key points to consider:
1. The results show entities that have similar structural roles/patterns in the network
2. Topological similarity means these entities function similarly within the graph structure
3. Focus on the structural relationships and patterns revealed by the embeddings
4. Explain why these particular entities are structurally similar
5. Connect the findings back to the original question

Provide a clear, informative answer that explains both the findings and the reasoning behind the structural similarities."""

        try:
            llm_client = create_llm_client(llm_provider)
            if llm_client is None:
                return f"Failed to create LLM client for provider: {llm_provider}"
            response = await llm_client.generate(prompt)
            return response.text
        except Exception as e:
            return f"Failed to generate answer: {str(e)}"
    
    def get_required_capabilities(self) -> List[str]:
        """Return required capabilities"""
        return [
            "graph_embeddings",
            "node2vec_training",
            "vector_similarity_search",
            "faiss_indexing",
            "topological_analysis"
        ]
    
    async def warm_up(self, year_filter: Optional[int] = None):
        """Pre-compute embeddings and indices for faster query processing"""
        cache_key = f"year_{year_filter}"
        if cache_key not in self._embeddings_cache:
            await self._initialize_embeddings_and_index(year_filter, cache_key)
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about cached embeddings"""
        stats = {}
        for cache_key, embedding_result in self._embeddings_cache.items():
            stats[cache_key] = {
                "num_embeddings": len(embedding_result.embeddings),
                "dimensions": embedding_result.training_config.dimensions,
                "training_time": embedding_result.training_time_seconds,
                "graph_stats": embedding_result.graph_stats
            }
        return stats 