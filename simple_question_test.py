#!/usr/bin/env python3
"""
Simple Question Testing Script
Test one question at a time to see detailed pipeline results
"""

import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def test_single_question(question_id: str, pipeline_name: str):
    """Test a single question with a single pipeline"""
    
    request_data = {
        "question_id": question_id,
        "pipeline_names": [pipeline_name],
        "llm_providers": ["openai"]
    }
    
    print(f"\n🧪 Testing {question_id} with {pipeline_name}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(f"{BASE_URL}/evaluate/question", json=request_data)
            response.raise_for_status()
            result = response.json()
            
            print(f"✅ API call successful")
            print(f"📊 Response keys: {list(result.keys())}")
            
            # Print the full response in a readable format
            print(f"\n📋 Full Response:")
            print(json.dumps(result, indent=2))
            
            # Try to extract specific information
            if "evaluation_results" in result:
                for eval_result in result["evaluation_results"]:
                    pipeline = eval_result.get("pipeline", "Unknown")
                    success = eval_result.get("success", False)
                    
                    print(f"\n🔍 Pipeline: {pipeline}")
                    print(f"   Success: {success}")
                    
                    if success:
                        answer = eval_result.get("result", {}).get("answer", "No answer")
                        print(f"   Answer: {answer}")
                    else:
                        error = eval_result.get("error", "No error message")
                        print(f"   Error: {error}")
            
            return result
            
        except Exception as e:
            print(f"❌ Failed: {str(e)}")
            return None

async def main():
    """Test a simple factual question with each pipeline"""
    
    question_id = "fact_001"  # "What was the frequency of tram Line 1 in 1964?"
    pipelines = ["direct_cypher", "no_rag", "vector", "hybrid"]
    
    print(f"🚀 Testing question {question_id} across all pipelines")
    
    for pipeline in pipelines:
        result = await test_single_question(question_id, pipeline)
        if result:
            print(f"\n✅ {pipeline} completed")
        else:
            print(f"\n❌ {pipeline} failed")

if __name__ == "__main__":
    asyncio.run(main()) 