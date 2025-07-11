"""
Vector Database Manager for Graph-RAG Pipeline

This module manages the ChromaDB vector database for storing and retrieving
embeddings of graph-derived text chunks.
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
import numpy as np
from .graph_to_text import GraphTextChunk
from ..config import settings

@dataclass
class VectorSearchResult:
    """Result from vector similarity search"""
    
    chunk_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    source_entities: List[str]
    temporal_context: Optional[str] = None
    spatial_context: Optional[str] = None

class VectorDatabaseManager:
    """Manages ChromaDB vector database for graph text chunks"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern to ensure only one instance"""
        if cls._instance is None:
            cls._instance = super(VectorDatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'client'):
            self.client = None
            self.collection = None
            self.embedding_function = None
            self._initialize_embedding_function()
        
    def _initialize_embedding_function(self):
        """Initialize the embedding function"""
        
        # Use OpenAI embeddings if available, otherwise sentence transformers
        if settings.openai_api_key:
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=settings.openai_api_key,
                model_name=settings.vector_embedding_model
            )
        else:
            # Fallback to sentence transformers
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
    
    async def initialize(self) -> bool:
        """Initialize the ChromaDB client and collection"""
        
        if VectorDatabaseManager._initialized:
            return True
        
        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(
                    name=settings.vector_db_collection_name,
                    embedding_function=self.embedding_function
                )
                print(f"Loaded existing collection: {settings.vector_db_collection_name}")
            except Exception as e:
                # Collection doesn't exist (NotFoundError) or other issue, create it
                print(f"Collection not found ({type(e).__name__}: {e}), creating new collection...")
                self.collection = self.client.create_collection(
                    name=settings.vector_db_collection_name,
                    embedding_function=self.embedding_function,
                    metadata={"description": "Berlin transport graph embeddings"}
                )
                print(f"Created new collection: {settings.vector_db_collection_name}")
            
            VectorDatabaseManager._initialized = True
            return True
            
        except Exception as e:
            print(f"Failed to initialize vector database: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector collection"""
        
        if not self.collection:
            return {"error": "Collection not initialized"}
        
        try:
            count = self.collection.count()
            
            # Get some sample metadata to understand content distribution
            if count > 0:
                sample_size = min(100, count)
                results = self.collection.get(
                    limit=sample_size,
                    include=["metadatas"]
                )
                
                # Analyze metadata
                entity_types = {}
                years = {}
                chunk_types = {}
                
                for metadata in results.get('metadatas', []):
                    if metadata:
                        entity_type = metadata.get('entity_type', 'unknown')
                        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
                        
                        year = metadata.get('year')
                        if year:
                            years[year] = years.get(year, 0) + 1
                        
                        chunk_type = metadata.get('chunk_type', 'unknown')
                        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
                
                return {
                    "total_chunks": count,
                    "entity_types": entity_types,
                    "years": years,
                    "chunk_types": chunk_types,
                    "sample_size": sample_size
                }
            else:
                return {"total_chunks": 0}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def add_chunks(self, chunks: List[GraphTextChunk], batch_size: int = 100) -> bool:
        """Add graph text chunks to the vector database"""
        
        if not self.collection:
            print("Collection not initialized")
            return False
        
        try:
            total_chunks = len(chunks)
            print(f"Adding {total_chunks} chunks to vector database...")
            
            # Process in batches to avoid memory issues
            for i in range(0, total_chunks, batch_size):
                batch = chunks[i:i + batch_size]
                
                # Prepare data for ChromaDB
                documents = [chunk.content for chunk in batch]
                metadatas = []
                ids = []
                
                for chunk in batch:
                    # Ensure unique IDs
                    chunk_id = chunk.id if chunk.id else str(uuid.uuid4())
                    ids.append(chunk_id)
                    
                    # Prepare metadata (ChromaDB requires simple types)
                    metadata = {
                        "entity_type": chunk.metadata.get("entity_type", "unknown"),
                        "chunk_type": chunk.chunk_type,
                        "source_entities": ",".join(chunk.source_entities) if chunk.source_entities else "",
                        "temporal_context": chunk.temporal_context or "",
                        "spatial_context": chunk.spatial_context or ""
                    }
                    
                    # Add specific metadata based on entity type
                    if chunk.metadata:
                        for key, value in chunk.metadata.items():
                            if value is not None and not isinstance(value, (list, dict)):
                                metadata[key] = str(value)
                    
                    metadatas.append(metadata)
                
                # Add to collection
                try:
                    self.collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    print(f"Added batch {i//batch_size + 1}/{(total_chunks + batch_size - 1)//batch_size}")
                except Exception as batch_error:
                    print(f"Error adding batch {i//batch_size + 1}: {batch_error}")
                    # Print sample data for debugging
                    if documents:
                        print(f"  Sample document: {documents[0][:100]}...")
                    if metadatas:
                        print(f"  Sample metadata: {metadatas[0]}")
                    raise batch_error
            
            print(f"Successfully added {total_chunks} chunks to vector database")
            return True
            
        except Exception as e:
            print(f"Error adding chunks to vector database: {e}")
            return False
    
    async def search_similar(
        self, 
        query: str, 
        k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search for similar chunks in the vector database"""
        
        if not self.collection:
            print("Collection not initialized")
            return []
        
        k = k or settings.vector_max_retrieved_chunks
        similarity_threshold = similarity_threshold or settings.vector_similarity_threshold
        
        try:
            # Prepare where clause for filtering
            where_clause = {}
            if filters:
                for key, value in filters.items():
                    if value is not None:
                        where_clause[key] = str(value)
            
            # Perform vector search
            search_kwargs = {
                "query_texts": [query],
                "n_results": k,
                "include": ["documents", "metadatas", "distances"]
            }
            
            if where_clause:
                search_kwargs["where"] = where_clause
            
            results = self.collection.query(**search_kwargs)
            
            # Process results
            search_results = []
            
            if results and results.get('documents') and results['documents'][0]:
                documents = results['documents'][0]
                metadatas = results.get('metadatas', [None])[0] or []
                distances = results.get('distances', [None])[0] or []
                ids = results.get('ids', [None])[0] or []
                
                for i, (doc, metadata, distance, chunk_id) in enumerate(zip(documents, metadatas, distances, ids)):
                    # Convert distance to similarity score (lower distance = higher similarity)
                    similarity_score = 1.0 - distance if distance is not None else 0.0
                    
                    # Filter by similarity threshold
                    if similarity_score >= similarity_threshold:
                        # Parse source entities
                        source_entities = []
                        if metadata and metadata.get('source_entities'):
                            source_entities = metadata['source_entities'].split(',')
                        
                        result = VectorSearchResult(
                            chunk_id=chunk_id or f"unknown_{i}",
                            content=doc,
                            similarity_score=similarity_score,
                            metadata=metadata or {},
                            source_entities=source_entities,
                            temporal_context=metadata.get('temporal_context') if metadata else None,
                            spatial_context=metadata.get('spatial_context') if metadata else None
                        )
                        
                        search_results.append(result)
            
            print(f"Found {len(search_results)} similar chunks for query")
            return search_results
            
        except Exception as e:
            print(f"Error searching vector database: {e}")
            return []
    
    async def search_with_temporal_filter(
        self, 
        query: str, 
        year: Optional[int] = None,
        year_range: Optional[Tuple[int, int]] = None
    ) -> List[VectorSearchResult]:
        """Search with temporal filtering"""
        
        filters = {}
        
        if year:
            filters["year"] = str(year)
        elif year_range:
            # Note: ChromaDB doesn't support range queries directly in where clause
            # We'll need to filter post-search or use multiple queries
            pass
        
        results = await self.search_similar(query, filters=filters)
        
        # Additional post-processing for year ranges if needed
        if year_range and not year:
            start_year, end_year = year_range
            filtered_results = []
            
            for result in results:
                result_year = result.metadata.get('year')
                if result_year:
                    try:
                        year_int = int(result_year)
                        if start_year <= year_int <= end_year:
                            filtered_results.append(result)
                    except (ValueError, TypeError):
                        pass
            
            results = filtered_results
        
        return results
    
    async def search_with_spatial_filter(
        self, 
        query: str, 
        area_name: Optional[str] = None,
        political_side: Optional[str] = None
    ) -> List[VectorSearchResult]:
        """Search with spatial/administrative filtering"""
        
        filters = {}
        
        if political_side:
            filters["political_side"] = political_side
        
        results = await self.search_similar(query, filters=filters)
        
        # Additional filtering for area names (substring match)
        if area_name:
            filtered_results = []
            area_name_lower = area_name.lower()
            
            for result in results:
                spatial_context = result.spatial_context or ""
                area_name_meta = result.metadata.get('area_name', "")
                
                if (area_name_lower in spatial_context.lower() or 
                    area_name_lower in area_name_meta.lower()):
                    filtered_results.append(result)
            
            results = filtered_results
        
        return results
    
    async def clear_collection(self) -> bool:
        """Clear all data from the vector collection"""
        
        if not self.collection or not self.client:
            return False
        
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(settings.vector_db_collection_name)
            self.collection = self.client.create_collection(
                name=settings.vector_db_collection_name,
                embedding_function=self.embedding_function,
                metadata={"description": "Berlin transport graph embeddings"}
            )
            print("Vector collection cleared and recreated")
            
            # Update all instances to use the new collection
            VectorDatabaseManager._instance.collection = self.collection
            
            return True
            
        except Exception as e:
            print(f"Error clearing vector collection: {e}")
            return False
    
    async def close(self):
        """Close the vector database connection"""
        # ChromaDB client doesn't need explicit closing
        self.client = None
        self.collection = None
        VectorDatabaseManager._initialized = False
        VectorDatabaseManager._instance = None

# Global instance accessor
def get_vector_database_manager() -> VectorDatabaseManager:
    """Get the singleton vector database manager instance"""
    return VectorDatabaseManager() 