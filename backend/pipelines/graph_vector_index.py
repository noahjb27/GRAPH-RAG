"""
Graph vector index service for fast similarity search using FAISS
Manages embedding indexing and retrieval for graph nodes
"""

import os
import pickle
import numpy as np
import faiss
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from .node_embedding_service import NodeEmbeddingResult, get_node_embedding_service
from .graph_preprocessing import GraphExtractionResult, get_graph_preprocessing_service

@dataclass
class IndexResult:
    """Result from vector indexing"""
    index: faiss.Index
    node_id_mapping: Dict[int, str]  # index_id -> nx_node_id
    reverse_mapping: Dict[str, int]  # nx_node_id -> index_id
    neo4j_mapping: Dict[str, str]  # nx_node_id -> neo4j_id
    dimension: int
    index_size: int

@dataclass
class SearchResult:
    """Result from similarity search"""
    node_id: str
    neo4j_id: str
    similarity_score: float
    node_attributes: Optional[Dict[str, Any]] = None

class GraphVectorIndexService:
    """Service for indexing and searching graph node embeddings"""
    
    def __init__(self):
        self.embedding_service = get_node_embedding_service()
        self.graph_preprocessing = get_graph_preprocessing_service()
        self.cache_dir = os.path.join(os.getcwd(), "vector_index_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def create_index(
        self,
        embedding_result: NodeEmbeddingResult,
        graph_result: GraphExtractionResult,
        index_type: str = "flat"  # "flat", "ivf", "hnsw"
    ) -> IndexResult:
        """Create FAISS index from node embeddings"""
        
        embeddings = embedding_result.embeddings
        dimension = embedding_result.training_config.dimensions
        
        # Prepare data for indexing
        node_ids = list(embeddings.keys())
        vectors = np.array([embeddings[node_id] for node_id in node_ids]).astype('float32')
        
        # Create FAISS index
        if index_type == "flat":
            index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity with normalized vectors)
        elif index_type == "ivf":
            nlist = min(100, len(node_ids) // 10)  # Number of clusters
            quantizer = faiss.IndexFlatIP(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
            index.train(vectors)
        elif index_type == "hnsw":
            M = 16  # Number of bi-directional links for each node
            index = faiss.IndexHNSWFlat(dimension, M)
        else:
            raise ValueError(f"Unsupported index type: {index_type}")
        
        # Normalize vectors for cosine similarity
        faiss.normalize_L2(vectors)
        
        # Add vectors to index
        index.add(vectors)
        
        # Create mappings
        node_id_mapping = {i: node_ids[i] for i in range(len(node_ids))}
        reverse_mapping = {node_ids[i]: i for i in range(len(node_ids))}
        
        # Create neo4j mapping
        neo4j_mapping = {}
        for nx_node_id in node_ids:
            if nx_node_id in graph_result.reverse_mapping:
                neo4j_mapping[nx_node_id] = graph_result.reverse_mapping[nx_node_id]
        
        return IndexResult(
            index=index,
            node_id_mapping=node_id_mapping,
            reverse_mapping=reverse_mapping,
            neo4j_mapping=neo4j_mapping,
            dimension=dimension,
            index_size=len(node_ids)
        )
    
    def search_similar_nodes(
        self,
        query_vector: np.ndarray,
        index_result: IndexResult,
        graph_result: GraphExtractionResult,
        top_k: int = 10,
        include_attributes: bool = True
    ) -> List[SearchResult]:
        """Search for nodes similar to query vector"""
        
        # Normalize query vector for cosine similarity
        query_vector = query_vector.astype('float32').reshape(1, -1)
        faiss.normalize_L2(query_vector)
        
        # Search index
        similarities, indices = index_result.index.search(query_vector, top_k)
        
        # Convert results
        results = []
        for i, (similarity, idx) in enumerate(zip(similarities[0], indices[0])):
            if idx == -1:  # FAISS uses -1 for empty results
                continue
                
            nx_node_id = index_result.node_id_mapping[idx]
            neo4j_id = index_result.neo4j_mapping.get(nx_node_id, "unknown")
            
            # Get node attributes if requested
            node_attributes = None
            if include_attributes and nx_node_id in graph_result.node_attributes:
                node_attributes = graph_result.node_attributes[nx_node_id]
            
            results.append(SearchResult(
                node_id=nx_node_id,
                neo4j_id=neo4j_id,
                similarity_score=float(similarity),
                node_attributes=node_attributes
            ))
        
        return results
    
    def search_by_node_similarity(
        self,
        anchor_node_id: str,
        index_result: IndexResult,
        graph_result: GraphExtractionResult,
        top_k: int = 10,
        include_attributes: bool = True
    ) -> List[SearchResult]:
        """Find nodes structurally similar to an anchor node"""
        
        if anchor_node_id not in index_result.reverse_mapping:
            return []
        
        # Get anchor node's index
        anchor_idx = index_result.reverse_mapping[anchor_node_id]
        
        # Get anchor vector from index
        anchor_vector = index_result.index.reconstruct(anchor_idx).reshape(1, -1)
        
        # Search for similar nodes
        return self.search_similar_nodes(
            anchor_vector.flatten(),
            index_result,
            graph_result,
            top_k + 1,  # +1 to exclude anchor itself
            include_attributes
        )[1:]  # Skip anchor node (first result)
    
    def search_hybrid(
        self,
        query_vector: np.ndarray,
        anchor_nodes: List[str],
        index_result: IndexResult,
        graph_result: GraphExtractionResult,
        semantic_weight: float = 0.6,
        structural_weight: float = 0.4,
        top_k: int = 10
    ) -> List[SearchResult]:
        """Hybrid search combining semantic and structural similarity"""
        
        # Get semantic similarity scores
        semantic_results = self.search_similar_nodes(
            query_vector, index_result, graph_result, top_k * 2, False
        )
        semantic_scores = {result.node_id: result.similarity_score for result in semantic_results}
        
        # Get structural similarity scores for each anchor
        structural_scores = {}
        for anchor in anchor_nodes:
            if anchor in index_result.reverse_mapping:
                struct_results = self.search_by_node_similarity(
                    anchor, index_result, graph_result, top_k * 2, False
                )
                for result in struct_results:
                    current_score = structural_scores.get(result.node_id, 0.0)
                    structural_scores[result.node_id] = max(current_score, result.similarity_score)
        
        # Combine scores
        all_nodes = set(semantic_scores.keys()) | set(structural_scores.keys())
        combined_results = []
        
        for node_id in all_nodes:
            semantic_score = semantic_scores.get(node_id, 0.0)
            structural_score = structural_scores.get(node_id, 0.0)
            
            combined_score = (
                semantic_weight * semantic_score + 
                structural_weight * structural_score
            )
            
            neo4j_id = index_result.neo4j_mapping.get(node_id, "unknown")
            node_attributes = graph_result.node_attributes.get(node_id)
            
            combined_results.append(SearchResult(
                node_id=node_id,
                neo4j_id=neo4j_id,
                similarity_score=combined_score,
                node_attributes=node_attributes
            ))
        
        # Sort by combined score and return top_k
        combined_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return combined_results[:top_k]
    
    def filter_results_by_metadata(
        self,
        results: List[SearchResult],
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Filter search results by node metadata"""
        
        filtered_results = []
        
        for result in results:
            if not result.node_attributes:
                continue
                
            # Apply filters
            passes_filters = True
            for filter_key, filter_value in filters.items():
                node_value = result.node_attributes.get(filter_key)
                
                if filter_key == "type" and node_value != filter_value:
                    passes_filters = False
                    break
                elif filter_key == "political_side" and node_value != filter_value:
                    passes_filters = False
                    break
                elif filter_key == "is_station" and bool(node_value) != bool(filter_value):
                    passes_filters = False
                    break
                elif filter_key == "is_line" and bool(node_value) != bool(filter_value):
                    passes_filters = False
                    break
                elif filter_key == "is_administrative" and bool(node_value) != bool(filter_value):
                    passes_filters = False
                    break
            
            if passes_filters:
                filtered_results.append(result)
        
        return filtered_results
    
    def save_index(self, index_result: IndexResult, cache_key: str):
        """Save index to disk"""
        
        index_path = os.path.join(self.cache_dir, f"{cache_key}_index.bin")
        metadata_path = os.path.join(self.cache_dir, f"{cache_key}_metadata.pkl")
        
        # Save FAISS index
        faiss.write_index(index_result.index, index_path)
        
        # Save metadata
        metadata = {
            "node_id_mapping": index_result.node_id_mapping,
            "reverse_mapping": index_result.reverse_mapping,
            "neo4j_mapping": index_result.neo4j_mapping,
            "dimension": index_result.dimension,
            "index_size": index_result.index_size
        }
        
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
    
    def load_index(self, cache_key: str) -> Optional[IndexResult]:
        """Load index from disk"""
        
        index_path = os.path.join(self.cache_dir, f"{cache_key}_index.bin")
        metadata_path = os.path.join(self.cache_dir, f"{cache_key}_metadata.pkl")
        
        if not (os.path.exists(index_path) and os.path.exists(metadata_path)):
            return None
        
        try:
            # Load FAISS index
            index = faiss.read_index(index_path)
            
            # Load metadata
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            return IndexResult(
                index=index,
                node_id_mapping=metadata["node_id_mapping"],
                reverse_mapping=metadata["reverse_mapping"],
                neo4j_mapping=metadata["neo4j_mapping"],
                dimension=metadata["dimension"],
                index_size=metadata["index_size"]
            )
        
        except Exception as e:
            print(f"Failed to load index: {e}")
            return None
    
    def get_index_stats(self, index_result: IndexResult) -> Dict[str, Any]:
        """Get statistics about the vector index"""
        
        return {
            "index_size": index_result.index_size,
            "dimension": index_result.dimension,
            "index_type": type(index_result.index).__name__,
            "total_nodes": len(index_result.node_id_mapping),
            "neo4j_mapped_nodes": len(index_result.neo4j_mapping)
        }

# Singleton instance
_graph_vector_index_service = None

def get_graph_vector_index_service() -> GraphVectorIndexService:
    """Get singleton graph vector index service"""
    global _graph_vector_index_service
    if _graph_vector_index_service is None:
        _graph_vector_index_service = GraphVectorIndexService()
    return _graph_vector_index_service 