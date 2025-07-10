#!/usr/bin/env python3
"""
Test script for the new Multi-Query Cypher Pipeline
Demonstrates the enhanced pipeline with complex questions
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.pipelines.multi_query_cypher_pipeline import MultiQueryCypherPipeline
from backend.pipelines.direct_cypher_pipeline import DirectCypherPipeline

async def test_multi_query_pipeline():
    """Test the multi-query pipeline with complex questions"""
    
    print("=== Multi-Query Cypher Pipeline Test ===\n")
    
    # Initialize both pipelines for comparison
    multi_pipeline = MultiQueryCypherPipeline()
    direct_pipeline = DirectCypherPipeline()
    
    # Test questions that should trigger multi-query approach
    test_questions = [
        # Complex temporal comparison
        "How did the number of U-Bahn stations change between 1960 and 1971, and what was the impact on different districts?",
        
        # Multi-entity analysis
        "Compare the transport development in East and West Berlin between 1961 and 1971, focusing on both U-Bahn and S-Bahn expansion.",
        
        # Cross-domain correlation
        "What was the relationship between administrative changes and transport development in Kreuzberg between 1946 and 1971?",
        
        # Simple question (should use single query)
        "How many U-Bahn stations were there in 1971?",
        
        # Multi-step analysis
        "Which transport lines crossed the Berlin Wall area, and what happened to stations on those lines after 1961?"
    ]
    
    llm_provider = "openai"  # Change to your preferred provider
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {question}")
        print(f"{'='*60}")
        
        try:
            # Test with multi-query pipeline
            print(f"\n🔄 Testing with Multi-Query Pipeline...")
            multi_result = await multi_pipeline.process_query(question, llm_provider)
            
            print(f"✅ Multi-Query Result:")
            print(f"   Success: {multi_result.success}")
            print(f"   Execution Time: {multi_result.execution_time_seconds:.2f}s")
            print(f"   Answer: {multi_result.answer[:200]}...")
            
            # Show metadata about query planning
            if multi_result.metadata:
                intended = multi_result.metadata.get('intended_approach', 'unknown')
                actually_multi = multi_result.metadata.get('actually_used_multi_query', False)
                fallback_reason = multi_result.metadata.get('fallback_reason')
                
                print(f"   Intended Approach: {intended}")
                print(f"   Actually Used Multi-Query: {actually_multi}")
                if fallback_reason:
                    print(f"   Fallback Reason: {fallback_reason}")
                
                if actually_multi:
                    query_plan = multi_result.metadata.get('query_plan', {})
                    print(f"   Query Plan:")
                    print(f"     - Num Queries: {query_plan.get('num_queries', 'N/A')}")
                    print(f"     - Integration: {query_plan.get('integration_strategy', 'N/A')}")
                    print(f"     - Reasoning: {query_plan.get('reasoning', 'N/A')}")
                    
                    individual_queries = multi_result.metadata.get('individual_queries', [])
                    print(f"   Individual Query Results:")
                    for j, qr in enumerate(individual_queries):
                        status = "✅" if qr.get('success') else "❌"
                        query_preview = qr.get('query', '')[:50] + '...' if len(qr.get('query', '')) > 50 else qr.get('query', '')
                        print(f"     - Query {j+1}: {status} {qr.get('records_count', 0)} records ({qr.get('execution_time', 0):.2f}s)")
                        print(f"       {query_preview}")
                        if qr.get('error'):
                            print(f"       Error: {qr.get('error')}")
                    
                    print(f"   Total Records: {multi_result.metadata.get('total_records', 0)}")
                    
            # Show generated cypher if multi-query was used
            if multi_result.generated_cypher and multi_result.metadata and multi_result.metadata.get('actually_used_multi_query'):
                print(f"   Generated Cypher Queries:")
                print(f"   {multi_result.generated_cypher}")
                print(f"   ---")
            
            # Test with direct pipeline for comparison
            print(f"\n🔄 Testing with Direct Pipeline (comparison)...")
            direct_result = await direct_pipeline.process_query(question, llm_provider)
            
            print(f"✅ Direct Result:")
            print(f"   Success: {direct_result.success}")
            print(f"   Execution Time: {direct_result.execution_time_seconds:.2f}s")
            print(f"   Answer: {direct_result.answer[:200]}...")
            
            # Compare results
            print(f"\n📊 Comparison:")
            print(f"   Multi-Query Time: {multi_result.execution_time_seconds:.2f}s")
            print(f"   Direct Time: {direct_result.execution_time_seconds:.2f}s")
            print(f"   Time Difference: {(multi_result.execution_time_seconds - direct_result.execution_time_seconds):.2f}s")
            
        except Exception as e:
            print(f"❌ Error testing question {i}: {e}")
    
    print(f"\n{'='*60}")
    print("Test completed!")
    print(f"{'='*60}")

async def test_complexity_analysis():
    """Test the complexity analysis function"""
    
    print("\n=== Testing Question Complexity Analysis ===\n")
    
    pipeline = MultiQueryCypherPipeline()
    
    test_cases = [
        # Should trigger multi-query
        ("How did transport change between 1960 and 1971?", True),
        ("Compare U-Bahn and S-Bahn development in East and West Berlin", True),
        ("What is the relationship between districts and transport lines?", True),
        
        # Should use single query
        ("How many U-Bahn stations were there in 1971?", False),
        ("What is the name of the central station?", False),
        ("List all transport lines in Berlin", False),
    ]
    
    for question, expected_multi in test_cases:
        needs_multi = await pipeline._analyze_question_complexity(question)
        status = "✅" if needs_multi == expected_multi else "❌"
        approach = "Multi-Query" if needs_multi else "Single Query"
        print(f"{status} \"{question}\" → {approach}")

if __name__ == "__main__":
    print("Starting Multi-Query Pipeline Tests...")
    print("Make sure you have configured your LLM provider in the .env file!")
    
    # Run complexity analysis test
    asyncio.run(test_complexity_analysis())
    
    # Run full pipeline test
    try:
        asyncio.run(test_multi_query_pipeline())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nTest failed with error: {e}")
        import traceback
        traceback.print_exc() 