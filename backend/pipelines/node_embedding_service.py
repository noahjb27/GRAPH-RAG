"""
Node embedding service for training and managing graph embeddings
Uses Node2Vec for structural similarity and topological embeddings
"""

import os
import pickle
import hashlib
import numpy as np
import networkx as nx
from node2vec import Node2Vec
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from sentence_transformers import SentenceTransformer
import asyncio
import time
from .graph_preprocessing import GraphPreprocessingService, GraphExtractionResult, get_graph_preprocessing_service
from ..config import settings

@dataclass
class EmbeddingTrainingConfig:
    """Configuration for embedding training"""
    dimensions: int = 128
    walk_length: int = 80
    num_walks: int = 10
    workers: int = 4
    window: int = 10
    min_count: int = 1
    batch_words: int = 4
    
    # Node2Vec specific parameters
    p: float = 1.0  # Return parameter
    q: float = 1.0  # In-out parameter
    
    # For creating neighborhood fingerprints
    neighborhood_hops: int = 2
    max_neighbors: int = 50

@dataclass
class NodeEmbeddingResult:
    """Result from node embedding training"""
    embeddings: Dict[str, np.ndarray]  # nx_node_id -> embedding vector
    model: Node2Vec
    training_config: EmbeddingTrainingConfig
    graph_stats: Dict[str, Any]
    training_time_seconds: float
    cache_key: str

class NodeEmbeddingService:
    """Service for training and managing node embeddings"""
    
    def __init__(self):
        self.graph_preprocessing = get_graph_preprocessing_service()
        self.cache_dir = os.path.join(os.getcwd(), "embeddings_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Query embedding model for semantic similarity
        self.query_encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.query_encoder_dim = self.query_encoder.get_sentence_embedding_dimension()
        
        # Projection layer to align query embeddings with Node2Vec dimensions
        self.projection_matrix = None
        
    async def train_embeddings(
        self,
        config: EmbeddingTrainingConfig,
        year_filter: Optional[int] = None,
        include_administrative: bool = True,
        force_retrain: bool = False
    ) -> NodeEmbeddingResult:
        """Train node embeddings using Node2Vec"""
        
        # Create cache key based on configuration and graph parameters
        cache_key = self._create_cache_key(config, year_filter, include_administrative)
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.pkl")
        
        # Check cache first
        if not force_retrain and os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    cached_result = pickle.load(f)
                    print(f"Loaded cached embeddings: {cache_key}")
                    return cached_result
            except Exception as e:
                print(f"Failed to load cached embeddings: {e}")
        
        print(f"Training new embeddings with cache key: {cache_key}")
        start_time = time.time()
        
        # Extract graph
        graph_result = await self.graph_preprocessing.extract_transport_network(
            year_filter=year_filter,
            include_administrative=include_administrative,
            include_temporal=False  # Don't include temporal for structural embeddings
        )
        
        print(f"Extracted graph: {graph_result.extraction_stats}")
        
        # Train Node2Vec embeddings
        embeddings, model = self._train_node2vec(graph_result.graph, config)
        
        training_time = time.time() - start_time
        
        # Create result
        result = NodeEmbeddingResult(
            embeddings=embeddings,
            model=model,
            training_config=config,
            graph_stats=graph_result.extraction_stats,
            training_time_seconds=training_time,
            cache_key=cache_key
        )
        
        # Cache result
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(result, f)
            print(f"Cached embeddings to: {cache_path}")
        except Exception as e:
            print(f"Failed to cache embeddings: {e}")
        
        return result
    
    def _train_node2vec(
        self,
        graph: nx.Graph,
        config: EmbeddingTrainingConfig
    ) -> Tuple[Dict[str, np.ndarray], Node2Vec]:
        """Train Node2Vec model"""
        
        print(f"Training Node2Vec on graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        
        # Initialize Node2Vec
        node2vec = Node2Vec(
            graph,
            dimensions=config.dimensions,
            walk_length=config.walk_length,
            num_walks=config.num_walks,
            workers=config.workers,
            p=config.p,
            q=config.q
        )
        
        # Train model
        model = node2vec.fit(
            window=config.window,
            min_count=config.min_count,
            batch_words=config.batch_words
        )
        
        # Extract embeddings
        embeddings = {}
        for node in graph.nodes():
            try:
                embeddings[node] = model.wv[node]
            except KeyError:
                # Handle nodes that might not be in the trained model
                print(f"Warning: Node {node} not found in trained model")
                embeddings[node] = np.zeros(config.dimensions)
        
        print(f"Successfully trained embeddings for {len(embeddings)} nodes")
        return embeddings, node2vec
    
    def create_neighborhood_fingerprints(
        self,
        graph: nx.Graph,
        embeddings: Dict[str, np.ndarray],
        config: EmbeddingTrainingConfig
    ) -> Dict[str, np.ndarray]:
        """Create neighborhood fingerprints by aggregating embeddings"""
        
        fingerprints = {}
        
        for node in graph.nodes():
            # Get k-hop neighborhood
            neighborhood = self._get_k_hop_neighborhood(
                graph, node, config.neighborhood_hops, config.max_neighbors
            )
            
            # Aggregate embeddings
            neighbor_embeddings = []
            for neighbor in neighborhood:
                if neighbor in embeddings:
                    neighbor_embeddings.append(embeddings[neighbor])
            
            if neighbor_embeddings:
                # Mean pooling of neighborhood embeddings
                fingerprint = np.mean(neighbor_embeddings, axis=0)
            else:
                # Fallback to node's own embedding
                fingerprint = embeddings.get(node, np.zeros(config.dimensions))
            
            fingerprints[node] = fingerprint
        
        return fingerprints
    
    def _get_k_hop_neighborhood(
        self,
        graph: nx.Graph,
        center_node: str,
        hops: int,
        max_neighbors: int
    ) -> List[str]:
        """Get k-hop neighborhood around a node"""
        
        if center_node not in graph:
            return [center_node]
        
        neighborhood = set([center_node])
        current_level = set([center_node])
        
        for _ in range(hops):
            next_level = set()
            for node in current_level:
                if node in graph:
                    neighbors = set(graph.neighbors(node))
                    next_level.update(neighbors)
            
            neighborhood.update(next_level)
            current_level = next_level
            
            # Limit neighborhood size
            if len(neighborhood) >= max_neighbors:
                break
        
        return list(neighborhood)[:max_neighbors]
    
    def embed_query(self, query: str, target_dimensions: int = 128) -> np.ndarray:
        """Embed a natural language query using sentence transformer"""
        embedding = self.query_encoder.encode(query)
        embedding = np.array(embedding)
        
        # Project to target dimensions if needed
        if embedding.shape[0] != target_dimensions:
            embedding = self._project_embedding(embedding, target_dimensions)
        
        return embedding
    
    def _project_embedding(self, embedding: np.ndarray, target_dimensions: int) -> np.ndarray:
        """Project embedding to target dimensions using learned or random projection"""
        
        current_dim = embedding.shape[0]
        
        # Create or reuse projection matrix
        if self.projection_matrix is None or self.projection_matrix.shape != (target_dimensions, current_dim):
            # Initialize with random projection (Xavier initialization)
            self.projection_matrix = np.random.normal(
                0, np.sqrt(2.0 / (current_dim + target_dimensions)), 
                (target_dimensions, current_dim)
            ).astype(np.float32)
        
        # Apply projection
        projected = np.dot(self.projection_matrix, embedding)
        
        # Normalize to maintain vector magnitude properties
        projected = projected / np.linalg.norm(projected) * np.linalg.norm(embedding)
        
        return projected
    
    def find_similar_nodes(
        self,
        query_embedding: np.ndarray,
        node_embeddings: Dict[str, np.ndarray],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Find most similar nodes to query using cosine similarity"""
        
        similarities = []
        
        for node_id, node_embedding in node_embeddings.items():
            # Cosine similarity
            similarity = self._cosine_similarity(query_embedding, node_embedding)
            similarities.append((node_id, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def find_structurally_similar_nodes(
        self,
        anchor_node: str,
        node_embeddings: Dict[str, np.ndarray],
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """Find nodes structurally similar to an anchor node"""
        
        if anchor_node not in node_embeddings:
            return []
        
        anchor_embedding = node_embeddings[anchor_node]
        similarities = []
        
        for node_id, node_embedding in node_embeddings.items():
            if node_id == anchor_node:
                continue
                
            similarity = self._cosine_similarity(anchor_embedding, node_embedding)
            similarities.append((node_id, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        
        # Handle zero vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return np.dot(vec1, vec2) / (norm1 * norm2)
    
    def _create_cache_key(
        self,
        config: EmbeddingTrainingConfig,
        year_filter: Optional[int],
        include_administrative: bool
    ) -> str:
        """Create cache key for embedding configuration"""
        
        config_str = (
            f"dim{config.dimensions}_walk{config.walk_length}_"
            f"num{config.num_walks}_p{config.p}_q{config.q}_"
            f"year{year_filter}_admin{include_administrative}"
        )
        
        return hashlib.md5(config_str.encode()).hexdigest()[:16]
    
    def get_embedding_stats(self, embeddings: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Get statistics about the embeddings"""
        
        if not embeddings:
            return {}
        
        vectors = list(embeddings.values())
        stacked = np.stack(vectors)
        
        return {
            "num_embeddings": len(embeddings),
            "dimensions": stacked.shape[1],
            "mean_norm": float(np.mean(np.linalg.norm(stacked, axis=1))),
            "std_norm": float(np.std(np.linalg.norm(stacked, axis=1))),
            "mean_values": stacked.mean(axis=0).tolist(),
            "std_values": stacked.std(axis=0).tolist()
        }

# Singleton instance
_node_embedding_service = None

def get_node_embedding_service() -> NodeEmbeddingService:
    """Get singleton node embedding service"""
    global _node_embedding_service
    if _node_embedding_service is None:
        _node_embedding_service = NodeEmbeddingService()
    return _node_embedding_service 