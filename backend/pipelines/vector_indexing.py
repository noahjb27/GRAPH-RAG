"""
Data Indexing Service for Vector-based RAG Pipeline

This module orchestrates the process of extracting data from Neo4j,
converting it to text, and indexing it in the vector database.
"""

import asyncio
import time
import os
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from .graph_to_text import GraphToTextConverter, GraphTextChunk
from .vector_database import VectorDatabaseManager, VectorSearchResult, get_vector_database_manager
from ..database.neo4j_client import Neo4jClient
from ..config import settings

@dataclass
class IndexingStats:
    """Statistics from the indexing process"""
    
    total_chunks_created: int
    total_chunks_indexed: int
    indexing_time_seconds: float
    chunks_per_second: float
    entity_type_breakdown: Dict[str, int]
    temporal_coverage: List[int]
    spatial_coverage: List[str]
    errors: List[str]
    
    def __post_init__(self):
        if not self.entity_type_breakdown:
            self.entity_type_breakdown = {}
        if not self.temporal_coverage:
            self.temporal_coverage = []
        if not self.spatial_coverage:
            self.spatial_coverage = []
        if not self.errors:
            self.errors = []

class VectorIndexingService:
    """Service for indexing Neo4j graph data into vector database"""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j_client = neo4j_client
        self.graph_converter = GraphToTextConverter(neo4j_client)
        self.vector_db = get_vector_database_manager()
        self._is_initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the indexing service"""
        
        if self._is_initialized:
            return True
            
        try:
            # Initialize vector database
            success = await self.vector_db.initialize()
            if not success:
                print("Failed to initialize vector database")
                return False
            
            # Ensure Neo4j connection
            if not self.neo4j_client.driver:
                await self.neo4j_client.connect()
            
            self._is_initialized = True
            print("Vector indexing service initialized successfully")
            return True
            
        except Exception as e:
            print(f"Failed to initialize vector indexing service: {e}")
            return False
    
    async def get_indexing_status(self) -> Dict[str, Any]:
        """Get current status of the vector index"""
        
        if not self._is_initialized:
            return {"status": "not_initialized"}
        
        try:
            # Get vector database stats
            db_stats = await self.vector_db.get_collection_stats()
            
            # Get Neo4j data stats for comparison
            neo4j_stats = await self._get_neo4j_data_stats()
            
            return {
                "status": "initialized",
                "vector_db_stats": db_stats,
                "neo4j_stats": neo4j_stats,
                "is_indexed": db_stats.get("total_chunks", 0) > 0,
                "index_coverage": self._calculate_coverage(db_stats, neo4j_stats)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _get_neo4j_data_stats(self) -> Dict[str, Any]:
        """Get statistics about the Neo4j data"""
        
        queries = {
            "stations": "MATCH (s:Station) RETURN count(s) as count",
            "lines": "MATCH (l:Line) RETURN count(l) as count",  
            "years": "MATCH (y:Year) RETURN count(y) as count, collect(y.year) as years",
            "areas": "MATCH (a:HistoricalOrtsteil) RETURN count(a) as count"
        }
        
        stats = {}
        
        for key, query in queries.items():
            try:
                result = await self.neo4j_client.execute_read_query(query)
                if result.records:
                    stats[key] = result.records[0]
            except Exception as e:
                stats[key] = {"error": str(e)}
        
        return stats
    
    def _calculate_coverage(self, vector_stats: Dict, neo4j_stats: Dict) -> Dict[str, Any]:
        """Calculate how well the vector index covers the Neo4j data"""
        
        coverage = {}
        
        # Entity type coverage
        vector_entities = vector_stats.get("entity_types", {})
        
        for entity_type in ["station", "line", "administrative_area", "temporal_snapshot"]:
            vector_count = vector_entities.get(entity_type, 0)
            
            # Map to Neo4j equivalent
            neo4j_key = {
                "station": "stations",
                "line": "lines", 
                "administrative_area": "areas",
                "temporal_snapshot": "years"
            }.get(entity_type, entity_type)
            
            neo4j_count = neo4j_stats.get(neo4j_key, {}).get("count", 0)
            
            if neo4j_count > 0:
                coverage[entity_type] = {
                    "vector_count": vector_count,
                    "neo4j_count": neo4j_count,
                    "coverage_ratio": vector_count / neo4j_count
                }
        
        return coverage
    
    async def full_reindex(self, force: bool = False, export_chunks: bool = False) -> IndexingStats:
        """Perform a full reindex of the Neo4j data"""
        
        start_time = time.time()
        
        if not self._is_initialized:
            await self.initialize()
        
        print("Starting full reindex of graph data...")
        
        # Clear existing data if forced or if rebuilding
        if force or settings.rebuild_vector_db_on_startup:
            print("Clearing existing vector data...")
            await self.vector_db.clear_collection()
        
        # Convert graph data to text chunks
        print("Converting graph data to text chunks...")
        chunks = await self.graph_converter.convert_entire_graph()
        
        if not chunks:
            return IndexingStats(
                 total_chunks_created=0,
                 total_chunks_indexed=0,
                 indexing_time_seconds=time.time() - start_time,
                 chunks_per_second=0.0,
                 entity_type_breakdown={},
                 temporal_coverage=[],
                 spatial_coverage=[],
                 errors=["No chunks created from graph data"]
             )
        
        print(f"Created {len(chunks)} text chunks")
        
        # Export chunks as text files if requested
        if export_chunks:
            await self._export_chunks_to_files(chunks)
        
        # Calculate statistics
        entity_types = {}
        years = set()
        areas = set()
        
        for chunk in chunks:
            entity_type = chunk.metadata.get("entity_type", "unknown")
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            
            year = chunk.metadata.get("year")
            if year:
                years.add(year)
            
            spatial_context = chunk.spatial_context
            if spatial_context:
                areas.add(spatial_context)
        
        # Index chunks in vector database
        print("Indexing chunks in vector database...")
        success = await self.vector_db.add_chunks(chunks)
        
        indexing_time = time.time() - start_time
        chunks_per_second = len(chunks) / indexing_time if indexing_time > 0 else 0
        
        stats = IndexingStats(
            total_chunks_created=len(chunks),
            total_chunks_indexed=len(chunks) if success else 0,
            indexing_time_seconds=indexing_time,
            chunks_per_second=chunks_per_second,
            entity_type_breakdown=entity_types,
            temporal_coverage=sorted(list(years)),
            spatial_coverage=sorted(list(areas)),
            errors=[] if success else ["Failed to index chunks in vector database"]
        )
        
        print(f"Indexing complete. Processed {len(chunks)} chunks in {indexing_time:.2f} seconds")
        return stats
    
    async def _export_chunks_to_files(self, chunks: List[GraphTextChunk]):
        """Export chunks to text files organized by type for inspection"""
        
        # Create export directory
        export_dir = "chunk_exports"
        os.makedirs(export_dir, exist_ok=True)
        
        print(f"Exporting {len(chunks)} chunks to {export_dir}/...")
        
        # Group chunks by entity type
        chunks_by_type = {}
        for chunk in chunks:
            entity_type = chunk.metadata.get("entity_type", "unknown")
            if entity_type not in chunks_by_type:
                chunks_by_type[entity_type] = []
            chunks_by_type[entity_type].append(chunk)
        
        # Export each entity type to separate files
        for entity_type, type_chunks in chunks_by_type.items():
            filename = f"{export_dir}/{entity_type}_chunks.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# {entity_type.upper()} CHUNKS ({len(type_chunks)} total)\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
                
                for i, chunk in enumerate(type_chunks, 1):
                    f.write(f"## CHUNK {i}: {chunk.id}\n")
                    f.write(f"**Type:** {chunk.chunk_type}\n")
                    f.write(f"**Temporal Context:** {chunk.temporal_context or 'N/A'}\n") 
                    f.write(f"**Spatial Context:** {chunk.spatial_context or 'N/A'}\n")
                    f.write(f"**Source Entities:** {', '.join(chunk.source_entities)}\n")
                    f.write(f"**Metadata:** {json.dumps(chunk.metadata, indent=2)}\n")
                    f.write(f"**Content:**\n{chunk.content}\n")
                    f.write("-" * 80 + "\n\n")
        
        # Create summary file
        summary_file = f"{export_dir}/SUMMARY.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# CHUNK EXPORT SUMMARY\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Total chunks: {len(chunks)}\n\n")
            
            f.write("## Breakdown by Entity Type:\n")
            for entity_type, type_chunks in sorted(chunks_by_type.items()):
                f.write(f"- {entity_type}: {len(type_chunks)} chunks\n")
            
            f.write(f"\n## Files Created:\n")
            for entity_type in sorted(chunks_by_type.keys()):
                f.write(f"- {entity_type}_chunks.txt\n")
                
        print(f"Exported chunks to {len(chunks_by_type)} files in {export_dir}/")
        print(f"See {summary_file} for overview")
    
    async def incremental_update(self, entity_type: Optional[str] = None) -> IndexingStats:
        """Perform an incremental update of specific entity types"""
        
        start_time = time.time()
        
        if not self._is_initialized:
            await self.initialize()
        
        print(f"Starting incremental update for entity type: {entity_type or 'all'}")
        
        # For now, we'll implement this as a simplified version
        # In a production system, you'd track changes and only update modified entities
        chunks = []
        
        if entity_type == "station" or entity_type is None:
            station_chunks = await self.graph_converter._convert_stations_narrative()
            chunks.extend(station_chunks)
        
        if entity_type == "line" or entity_type is None:
            line_chunks = await self.graph_converter._convert_lines_narrative()  
            chunks.extend(line_chunks)
        
        if entity_type == "temporal" or entity_type is None:
            temporal_chunks = await self.graph_converter._convert_temporal_snapshots()
            chunks.extend(temporal_chunks)
        
        if entity_type == "administrative" or entity_type is None:
            area_chunks = await self.graph_converter._convert_administrative_areas()
            chunks.extend(area_chunks)
        
        if not chunks:
            return IndexingStats(
                 total_chunks_created=0,
                 total_chunks_indexed=0,
                 indexing_time_seconds=time.time() - start_time,
                 chunks_per_second=0.0,
                 entity_type_breakdown={},
                 temporal_coverage=[],
                 spatial_coverage=[],
                 errors=[f"No chunks created for entity type: {entity_type}"]
             )
        
        # Index new chunks
        success = await self.vector_db.add_chunks(chunks)
        
        indexing_time = time.time() - start_time
        chunks_per_second = len(chunks) / indexing_time if indexing_time > 0 else 0
        
        stats = IndexingStats(
             total_chunks_created=len(chunks),
             total_chunks_indexed=len(chunks) if success else 0,
             indexing_time_seconds=indexing_time,
             chunks_per_second=chunks_per_second,
             entity_type_breakdown={},
             temporal_coverage=[],
             spatial_coverage=[],
             errors=[] if success else ["Failed to index chunks in vector database"]
         )
        
        print(f"Incremental update complete. Processed {len(chunks)} chunks in {indexing_time:.2f} seconds")
        return stats
    
    async def test_retrieval(self, test_query: str = "Berlin transport stations") -> List[VectorSearchResult]:
        """Test the retrieval functionality with a sample query"""
        
        if not self._is_initialized:
            await self.initialize()
        
        print(f"Testing retrieval with query: '{test_query}'")
        
        try:
            results = await self.vector_db.search_similar(test_query, k=5)
            
            print(f"Retrieved {len(results)} results:")
            for i, result in enumerate(results[:3]):  # Show first 3
                print(f"  {i+1}. Score: {result.similarity_score:.3f}")
                print(f"     Content: {result.content[:100]}...")
                print(f"     Type: {result.metadata.get('entity_type', 'unknown')}")
                print()
            
            return results
            
        except Exception as e:
            print(f"Error testing retrieval: {e}")
            return []
    
    async def cleanup(self):
        """Clean up resources"""
        
        try:
            await self.vector_db.close()
            await self.neo4j_client.close()
            self._is_initialized = False
            print("Vector indexing service cleaned up")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")

# Global instance for use in FastAPI startup
vector_indexing_service: Optional[VectorIndexingService] = None

async def get_vector_indexing_service(neo4j_client: Neo4jClient) -> VectorIndexingService:
    """Get or create the global vector indexing service instance"""
    
    global vector_indexing_service
    
    if vector_indexing_service is None:
        vector_indexing_service = VectorIndexingService(neo4j_client)
        await vector_indexing_service.initialize()
    
    return vector_indexing_service 