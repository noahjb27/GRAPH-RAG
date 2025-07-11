"""
Test script for the Vector-based RAG Pipeline
Demonstrates indexing and querying functionality
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.database.neo4j_client import neo4j_client
from backend.pipelines.vector_indexing import VectorIndexingService
from backend.pipelines.vector_pipeline import VectorPipeline
from backend.config import settings

async def test_vector_pipeline():
    """Test the complete vector pipeline functionality"""
    
    print("🚀 Testing Vector-based RAG Pipeline")
    print("=" * 50)
    
    # Step 1: Initialize services
    print("\n1. Initializing services...")
    
    try:
        # Connect to Neo4j
        await neo4j_client.connect()
        print("✓ Neo4j connected")
        
        # Initialize vector indexing service
        indexing_service = VectorIndexingService(neo4j_client)
        await indexing_service.initialize()
        print("✓ Vector indexing service initialized")
        
        # Initialize vector pipeline
        vector_pipeline = VectorPipeline()
        await vector_pipeline.initialize()
        print("✓ Vector pipeline initialized")
        
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        return
    
    # Step 2: Check current indexing status
    print("\n2. Checking indexing status...")
    
    try:
        status = await indexing_service.get_indexing_status()
        print(f"Vector DB Status: {status.get('status', 'unknown')}")
        
        db_stats = status.get("vector_db_stats", {})
        total_chunks = db_stats.get("total_chunks", 0)
        print(f"Current chunks: {total_chunks}")
        
        if total_chunks == 0:
            print("⚠ Vector database is empty. Starting indexing...")
            
            # Step 3: Index the graph data
            print("\n3. Indexing graph data...")
            indexing_stats = await indexing_service.full_reindex(force=True)
            
            print(f"✓ Indexing completed:")
            print(f"  - Chunks created: {indexing_stats.total_chunks_created}")
            print(f"  - Chunks indexed: {indexing_stats.total_chunks_indexed}")
            print(f"  - Time taken: {indexing_stats.indexing_time_seconds:.2f} seconds")
            print(f"  - Chunks/second: {indexing_stats.chunks_per_second:.2f}")
            
            if indexing_stats.entity_type_breakdown:
                print("  - Entity breakdown:")
                for entity_type, count in indexing_stats.entity_type_breakdown.items():
                    print(f"    {entity_type}: {count}")
        else:
            print("✓ Vector database already populated")
            
    except Exception as e:
        print(f"✗ Indexing failed: {e}")
        return
    
    # Step 4: Test retrieval
    print("\n4. Testing vector retrieval...")
    
    test_queries = [
        "What tram lines operated in 1964?",
        "How many stations were in West Berlin?", 
        "Which areas had the most transport coverage?",
        "What was the frequency of Line 1?",
        "Tell me about transport in East Berlin after 1961"
    ]
    
    try:
        for i, query in enumerate(test_queries, 1):
            print(f"\n  Query {i}: {query}")
            
            # Test raw retrieval
            results = await indexing_service.test_retrieval(query)
            print(f"  Retrieved {len(results)} chunks (similarity scores: {[f'{r.similarity_score:.3f}' for r in results[:3]]})")
            
            # Test full pipeline
            if i <= 2:  # Only test full pipeline for first 2 queries to save time
                pipeline_result = await vector_pipeline.process_query(
                    question=query,
                    llm_provider="openai"  # Use OpenAI if available
                )
                
                print(f"  Pipeline Success: {pipeline_result.success}")
                if pipeline_result.success:
                    print(f"  Answer: {pipeline_result.answer[:150]}...")
                    print(f"  Execution time: {pipeline_result.execution_time_seconds:.2f}s")
                else:
                    print(f"  Error: {pipeline_result.error_message}")
                    
    except Exception as e:
        print(f"✗ Retrieval test failed: {e}")
    
    # Step 5: Show pipeline statistics
    print("\n5. Pipeline Statistics:")
    
    try:
        pipeline_stats = vector_pipeline.get_stats()
        print(f"  - Executions: {pipeline_stats['execution_count']}")
        print(f"  - Success rate: {pipeline_stats['success_rate']:.1%}")
        print(f"  - Avg execution time: {pipeline_stats['average_execution_time']:.2f}s")
        
        # Get detailed status
        detailed_status = await vector_pipeline.get_pipeline_status()
        config = detailed_status.get("configuration", {})
        print(f"  - Configuration:")
        print(f"    Max chunks: {config.get('max_retrieved_chunks', 'unknown')}")
        print(f"    Similarity threshold: {config.get('similarity_threshold', 'unknown')}")
        print(f"    Embedding model: {config.get('embedding_model', 'unknown')}")
        
    except Exception as e:
        print(f"⚠ Could not get pipeline statistics: {e}")
    
    # Step 6: Cleanup
    print("\n6. Cleaning up...")
    
    try:
        await indexing_service.cleanup()
        await neo4j_client.close()
        print("✓ Cleanup completed")
        
    except Exception as e:
        print(f"⚠ Cleanup error: {e}")
    
    print("\n🎉 Vector pipeline test completed!")

async def quick_test():
    """Quick test to verify basic functionality"""
    
    print("🔍 Quick Vector Pipeline Test")
    print("=" * 30)
    
    try:
        # Just test basic connectivity and status
        await neo4j_client.connect()
        
        indexing_service = VectorIndexingService(neo4j_client)
        await indexing_service.initialize()
        
        status = await indexing_service.get_indexing_status()
        print(f"Vector DB Status: {status.get('status', 'unknown')}")
        
        db_stats = status.get('vector_db_stats', {})
        print(f"Total chunks: {db_stats.get('total_chunks', 0)}")
        
        if db_stats.get('total_chunks', 0) > 0:
            # Quick retrieval test
            results = await indexing_service.test_retrieval("Berlin transport")
            print(f"Sample retrieval: {len(results)} chunks found")
            
            if results:
                print(f"Top result: {results[0].content[:100]}...")
        
        await indexing_service.cleanup()
        await neo4j_client.close()
        
        print("✓ Quick test completed successfully")
        
    except Exception as e:
        print(f"✗ Quick test failed: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Vector Pipeline")
    parser.add_argument("--quick", action="store_true", help="Run quick test only")
    parser.add_argument("--index-only", action="store_true", help="Only run indexing")
    
    args = parser.parse_args()
    
    if args.quick:
        asyncio.run(quick_test())
    else:
        asyncio.run(test_vector_pipeline()) 