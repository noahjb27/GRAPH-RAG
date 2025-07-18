#!/usr/bin/env python3
"""
GraphRAG Production Deployment Script
Comprehensive setup and pre-computation for production deployment
"""

import asyncio
import sys
import time
import argparse
from pathlib import Path
from typing import List, Optional

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.pipelines.graphrag_transport_pipeline import (
    TransportCommunityDetector,
    TransportCommunitySummarizer,
    GraphRAGTransportPipeline
)
from backend.pipelines.graphrag_cache import graphrag_cache
from backend.database.neo4j_client import neo4j_client
from backend.config import settings

class GraphRAGProductionDeployer:
    """
    Handles complete GraphRAG production deployment setup
    """
    
    def __init__(self):
        self.detector = TransportCommunityDetector(neo4j_client)
        self.cache = graphrag_cache
        self.pipeline = GraphRAGTransportPipeline()
    
    async def deploy_for_production(self, full_deployment: bool = True):
        """
        Complete production deployment with pre-computation
        """
        print("🚀 Starting GraphRAG Production Deployment")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            # Step 1: Validate system requirements
            await self._validate_system()
            
            # Step 2: Initialize cache structure
            await self._initialize_cache_structure()
            
            # Step 3: Pre-compute communities for all common scenarios
            if full_deployment:
                await self._precompute_full_communities()
            else:
                await self._precompute_essential_communities()
            
            # Step 4: Generate summaries for all LLM providers
            await self._precompute_summaries()
            
            # Step 5: Validate deployment
            await self._validate_deployment()
            
            # Step 6: Performance benchmarking
            await self._run_performance_benchmarks()
            
            total_time = time.time() - start_time
            print(f"\n🎉 GraphRAG Production Deployment Complete!")
            print(f"   ⏱️  Total deployment time: {total_time:.2f} seconds")
            
            # Generate deployment report
            await self._generate_deployment_report()
            
        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    async def _validate_system(self):
        """
        Validate system requirements for GraphRAG
        """
        print("\n🔍 Validating system requirements...")
        
        # Check Neo4j connection
        try:
            # Simple test query
            result = await neo4j_client.execute_read_query("MATCH (n) RETURN count(n) as total LIMIT 1")
            if result.success:
                total_nodes = result.records[0]['total']
                print(f"   ✅ Neo4j connected: {total_nodes} nodes available")
            else:
                raise Exception("Neo4j query failed")
        except Exception as e:
            raise Exception(f"Neo4j connection failed: {e}")
        
        # Check temporal data availability
        try:
            result = await neo4j_client.execute_read_query(
                "MATCH (cs:CoreStation) WHERE cs.activity_period IS NOT NULL RETURN count(cs) as total"
            )
            if result.success and result.records[0]['total'] > 0:
                temporal_stations = result.records[0]['total']
                print(f"   ✅ Temporal data available: {temporal_stations} CoreStations with activity periods")
            else:
                raise Exception("No temporal data found")
        except Exception as e:
            raise Exception(f"Temporal data validation failed: {e}")
        
        # Check LLM provider availability (optional)
        try:
            from backend.llm_clients.client_factory import create_llm_client
            llm_client = create_llm_client("openai")
            if llm_client:
                print(f"   ✅ LLM provider available: OpenAI")
            else:
                print(f"   ⚠️  No LLM provider available (fallback summaries will be used)")
        except Exception as e:
            print(f"   ⚠️  LLM validation warning: {e}")
        
        print("   ✅ System validation complete")
    
    async def _initialize_cache_structure(self):
        """
        Initialize cache directory structure
        """
        print("\n📁 Initializing cache structure...")
        
        # Cache is initialized automatically by GraphRAGCache
        stats = await self.cache.get_cache_stats()
        print(f"   ✅ Cache directory created: {self.cache.cache_dir}")
        print(f"   📊 Current cache state:")
        print(f"      - Community caches: {stats['community_caches']}")
        print(f"      - Summary caches: {stats['summary_caches']}")
        print(f"      - Total size: {stats['cache_dir_size_mb']:.2f} MB")
    
    async def _precompute_essential_communities(self):
        """
        Pre-compute communities for essential scenarios only
        """
        print("\n🧠 Pre-computing essential communities...")
        
        essential_scenarios = [
            (None, None),  # All communities, all years
            (1961, None),  # Berlin Wall construction year
            (1989, None),  # Reunification year
        ]
        
        for year_filter, community_types in essential_scenarios:
            year_str = str(year_filter) if year_filter else "all years"
            types_str = str(community_types) if community_types else "all types"
            print(f"   🔄 Computing communities for {year_str}, {types_str}...")
            
            communities = await self.detector.detect_all_communities(year_filter, use_cache=True)
            total_communities = sum(len(cl) for cl in communities.values())
            print(f"      ✅ {total_communities} communities detected and cached")
    
    async def _precompute_full_communities(self):
        """
        Pre-compute communities for all production scenarios
        """
        print("\n🧠 Pre-computing communities for all scenarios...")
        
        # All year filters that might be used in production
        year_filters = [None] + settings.available_years
        
        # Community type combinations
        community_type_combinations = [
            None,  # All types
            ["geographic"],
            ["temporal"],
            ["operational"],
            ["service_type"],
            ["geographic", "temporal"],
            ["geographic", "operational"]
        ]
        
        total_scenarios = len(year_filters) * len(community_type_combinations)
        current_scenario = 0
        
        for year_filter in year_filters:
            for community_types in community_type_combinations:
                current_scenario += 1
                year_str = str(year_filter) if year_filter else "all years"
                types_str = str(community_types) if community_types else "all types"
                
                print(f"   🔄 [{current_scenario}/{total_scenarios}] Computing communities for {year_str}, {types_str}...")
                
                try:
                    communities = await self.detector.detect_all_communities(year_filter, use_cache=True)
                    total_communities = sum(len(cl) for cl in communities.values())
                    print(f"      ✅ {total_communities} communities detected and cached")
                except Exception as e:
                    print(f"      ❌ Error: {e}")
    
    async def _precompute_summaries(self):
        """
        Pre-compute summaries for all communities and LLM providers
        """
        print("\n📝 Pre-computing community summaries...")
        
        # Get all cached communities
        all_communities = await self.cache.load_communities()
        if not all_communities:
            print("   ⚠️  No cached communities found, skipping summary generation")
            return
        
        # LLM providers to support
        llm_providers = settings.graphrag_cache_warm_llm_providers
        
        total_communities = sum(len(cl) for cl in all_communities.values())
        total_summaries_needed = total_communities * len(llm_providers)
        current_summary = 0
        
        print(f"   📊 Generating summaries for {total_communities} communities x {len(llm_providers)} LLM providers = {total_summaries_needed} total summaries")
        
        for provider in llm_providers:
            print(f"   🧠 Generating summaries with {provider}...")
            summarizer = TransportCommunitySummarizer(provider)
            
            for community_type, community_list in all_communities.items():
                for community in community_list:
                    current_summary += 1
                    progress = (current_summary / total_summaries_needed) * 100
                    
                    try:
                        summary = await summarizer.summarize_community(community, use_cache=True)
                        if current_summary % 10 == 0:  # Progress every 10 summaries
                            print(f"      📈 Progress: {progress:.1f}% ({current_summary}/{total_summaries_needed})")
                    except Exception as e:
                        print(f"      ❌ Error generating summary for {community.name}: {e}")
        
        print(f"   ✅ Summary generation complete")
    
    async def _validate_deployment(self):
        """
        Validate that the deployment is working correctly
        """
        print("\n✅ Validating deployment...")
        
        # Test community loading
        communities = await self.cache.load_communities()
        if not communities:
            raise Exception("No communities found in cache")
        
        total_communities = sum(len(cl) for cl in communities.values())
        print(f"   ✅ Community loading: {total_communities} communities available")
        
        # Test summary loading
        test_community = next(iter(next(iter(communities.values()))))
        summary = await self.cache.load_summary(test_community.id, "openai")
        if summary:
            print(f"   ✅ Summary loading: Successfully loaded test summary")
        else:
            print(f"   ⚠️  Summary loading: No cached summary found (may use fallback)")
        
        # Test full pipeline
        test_question = "What were the main transport characteristics in 1971?"
        try:
            result = await self.pipeline.process_query(
                question=test_question,
                llm_provider="openai",
                year_filter=1971
            )
            if result.success:
                print(f"   ✅ Pipeline test: Query completed in {result.execution_time_seconds:.2f}s")
            else:
                raise Exception(f"Pipeline test failed: {result.error_message}")
        except Exception as e:
            raise Exception(f"Pipeline validation failed: {e}")
    
    async def _run_performance_benchmarks(self):
        """
        Run performance benchmarks
        """
        print("\n⚡ Running performance benchmarks...")
        
        benchmark_questions = [
            ("Global question", "How did Berlin's transport network change during political division?", None),
            ("Temporal question", "What transport developments occurred in 1961?", 1961),
            ("Geographic question", "What transport coverage existed in different districts?", None),
        ]
        
        total_time = 0
        for name, question, year_filter in benchmark_questions:
            start_time = time.time()
            
            try:
                result = await self.pipeline.process_query(
                    question=question,
                    llm_provider="openai",
                    year_filter=year_filter
                )
                
                execution_time = time.time() - start_time
                total_time += execution_time
                
                if result.success:
                    communities_count = result.metadata.get('communities_analyzed', 0) if result.metadata else 0
                    print(f"   ⚡ {name}: {execution_time:.2f}s ({communities_count} communities)")
                else:
                    print(f"   ❌ {name}: Failed")
            
            except Exception as e:
                print(f"   ❌ {name}: Error - {e}")
        
        avg_time = total_time / len(benchmark_questions)
        print(f"   📊 Average query time: {avg_time:.2f}s")
    
    async def _generate_deployment_report(self):
        """
        Generate a comprehensive deployment report
        """
        print("\n📋 Generating deployment report...")
        
        stats = await self.cache.get_cache_stats()
        
        report = {
            "deployment_timestamp": time.time(),
            "cache_statistics": stats,
            "configuration": {
                "cache_enabled": settings.graphrag_cache_enabled,
                "cache_directory": settings.graphrag_cache_dir,
                "summary_max_tokens": settings.graphrag_summary_max_tokens,
                "warm_llm_providers": settings.graphrag_cache_warm_llm_providers,
                "supported_years": settings.available_years,
            },
            "system_status": "deployed"
        }
        
        report_file = "graphrag_deployment_report.json"
        import json
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"   📄 Deployment report saved: {report_file}")
        print(f"   📊 Final statistics:")
        print(f"      - Cached communities: {stats['total_cached_communities']}")
        print(f"      - Cached summaries: {stats['summary_caches']}")
        print(f"      - Total cache size: {stats['cache_dir_size_mb']:.2f} MB")

async def main():
    parser = argparse.ArgumentParser(description="GraphRAG Production Deployment")
    parser.add_argument("--quick", action="store_true", 
                       help="Quick deployment (essential scenarios only)")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only run validation without pre-computation")
    
    args = parser.parse_args()
    
    deployer = GraphRAGProductionDeployer()
    
    try:
        if args.validate_only:
            await deployer._validate_system()
            await deployer._validate_deployment()
        else:
            full_deployment = not args.quick
            await deployer.deploy_for_production(full_deployment)
    
    except Exception as e:
        print(f"❌ Deployment error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 