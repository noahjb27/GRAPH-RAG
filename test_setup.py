#!/usr/bin/env python3
"""
Test script for Graph-RAG Research System setup
Run this to verify your configuration before starting the full system
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_setup():
    """Test system setup and configuration"""
    
    print("🧪 Testing Graph-RAG Research System Setup")
    print("=" * 50)
    
    # Test 1: Environment Variables
    print("\n1. 📋 Environment Variables Check:")
    
    required_vars = [
        "NEO4J_AURA_URI",
        "NEO4J_AURA_USERNAME", 
        "NEO4J_AURA_PASSWORD"
    ]
    
    optional_vars = [
        "OPENAI_API_KEY",
        "MISTRAL_API_KEY", 
        "MISTRAL_BASE_URL",
        "GEMINI_API_KEY"
    ]
    
    all_good = True
    
    for var in required_vars:
        if os.getenv(var):
            print(f"   ✅ {var}: Set")
        else:
            print(f"   ❌ {var}: Missing (Required)")
            all_good = False
    
    llm_providers = []
    for var in optional_vars:
        if os.getenv(var):
            print(f"   ✅ {var}: Set")
            if "API_KEY" in var:
                provider = var.replace("_API_KEY", "").lower()
                llm_providers.append(provider)
        else:
            print(f"   ⚠️  {var}: Not set")
    
    print(f"\n   📊 Available LLM Providers: {llm_providers}")
    
    if not llm_providers:
        print("   ❌ No LLM providers configured!")
        all_good = False
    
    # Test 2: Neo4j Connection
    print("\n2. 🗄️  Neo4j Database Connection:")
    try:
        from backend.database.neo4j_client import neo4j_client
        
        connected = await neo4j_client.test_connection()
        if connected:
            print("   ✅ Neo4j connection successful")
            
            # Get database info
            db_info = await neo4j_client.get_database_info()
            print(f"   📈 Nodes: {db_info.get('node_count', 'Unknown')}")
            print(f"   📈 Relationships: {db_info.get('relationship_count', 'Unknown')}")
            print(f"   📅 Available years: {db_info.get('available_years', 'Unknown')}")
        else:
            print("   ❌ Neo4j connection failed")
            all_good = False
            
    except Exception as e:
        print(f"   ❌ Neo4j connection error: {e}")
        all_good = False
    
    # Test 3: LLM Providers
    print("\n3. 🤖 LLM Provider Connectivity:")
    try:
        from backend.llm_clients.client_factory import test_client_connectivity
        
        connectivity = await test_client_connectivity()
        
        for provider, status in connectivity.items():
            if status:
                print(f"   ✅ {provider.title()}: Connected")
            else:
                print(f"   ❌ {provider.title()}: Failed")
        
        connected_providers = [p for p, status in connectivity.items() if status]
        if not connected_providers:
            print("   ❌ No LLM providers are working!")
            all_good = False
            
    except Exception as e:
        print(f"   ❌ LLM provider test error: {e}")
        all_good = False
    
    # Test 4: Question Taxonomy
    print("\n4. 📚 Question Taxonomy:")
    try:
        from backend.evaluation.question_loader import QuestionLoader
        
        loader = QuestionLoader()
        questions = loader.get_all_questions()
        summary = loader.get_taxonomy_summary()
        
        print(f"   ✅ Total questions: {summary.get('total_questions', 0)}")
        print(f"   📊 Categories: {list(summary.get('categories', {}).keys())}")
        
        if summary.get('total_questions', 0) == 0:
            print("   ⚠️  No questions loaded - check question_taxonomy import")
        
    except Exception as e:
        print(f"   ❌ Question taxonomy error: {e}")
    
    # Final Result
    print("\n" + "=" * 50)
    if all_good:
        print("🎉 Setup Complete! Your system is ready to run.")
        print("\nNext steps:")
        print("1. Run: python -m backend.main")
        print("2. Open: http://localhost:8000/docs")
        print("3. Test: http://localhost:8000/status")
    else:
        print("⚠️  Setup Issues Found - Please fix the errors above")
        print("\nCommon fixes:")
        print("1. Check your .env file has all required variables")
        print("2. Verify your Neo4j credentials and connection")
        print("3. Ensure you have valid API keys for LLM providers")

if __name__ == "__main__":
    asyncio.run(test_setup()) 