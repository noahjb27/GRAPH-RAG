#!/usr/bin/env python3
"""
GraphRAG Cache Manager
Script for pre-computing and managing GraphRAG communities and summaries for production deployment
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

# Add backend to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from backend.pipelines.graphrag_transport_pipeline import (
    TransportCommunityDetector,
    TransportCommunitySummarizer
)
from backend.pipelines.graphrag_cache import graphrag_cache
from backend.database.neo4j_client import neo4j_client
from backend.config import settings

class GraphRAGCacheManager:
    """
    Manages GraphRAG cache operations for production deployment
    """
    
    def __init__(self):
        self.detector = TransportCommunityDetector(neo4j_client)
        self.cache = graphrag_cache
    
    async def warm_cache_for_production(self):
        """
        Pre-warm cache with all common query patterns for production use
        """
        print("🚀 Warming GraphRAG cache for production deployment...")
        
        # Common year filters that users might query
        year_filters = [None, 1946, 1950, 1961, 1970, 1975, 1980, 1989]
        
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
        
        # LLM providers to support
        llm_providers = ["openai", "gemini", "mistral"]
        
        # Initialize summarizers for each provider
        summarizers = {
            provider: TransportCommunitySummarizer(provider) 
            for provider in llm_providers
        }
        
        total_operations = len(year_filters) * len(community_type_combinations) * len(llm_providers)
        current_operation = 0
        
        for year_filter in year_filters:
            print(f"\n📅 Processing year filter: {year_filter}")
            
            for community_types in community_type_combinations:
                current_operation += 1
                types_str = str(community_types) if community_types else "all"
                print(f"  🏷️  Community types: {types_str} ({current_operation}/{total_operations})")
                
                # Get/generate communities
                communities = await self.detector.detect_all_communities(year_filter, use_cache=True)
                
                # Filter communities if specified
                if community_types:
                    filtered_communities = []
                    for community_type in community_types:
                        if community_type in communities:
                            filtered_communities.extend(communities[community_type])
                else:
                    filtered_communities = []
                    for community_list in communities.values():
                        filtered_communities.extend(community_list)
                
                # Generate summaries for each LLM provider
                for provider in llm_providers:
                    print(f"    🧠 Generating summaries with {provider}...")
                    summarizer = summarizers[provider]
                    
                    summary_count = 0
                    for community in filtered_communities:
                        try:
                            await summarizer.summarize_community(community, use_cache=True)
                            summary_count += 1
                        except Exception as e:
                            print(f"      ❌ Error with {community.name}: {e}")
                    
                    print(f"      ✅ Generated {summary_count} summaries")
        
        # Display final stats
        stats = await self.cache.get_cache_stats()
        print(f"\n🎉 Cache warming complete!")
        print(f"   📊 {stats['community_caches']} community cache files")
        print(f"   📝 {stats['summary_caches']} summary cache files")
        print(f"   🗂️  {stats['total_cached_communities']} total communities")
        print(f"   💾 {stats['cache_dir_size_mb']:.2f} MB cache size")
    
    async def validate_cache(self):
        """
        Validate cached data integrity and completeness
        """
        print("🔍 Validating GraphRAG cache...")
        
        stats = await self.cache.get_cache_stats()
        
        print(f"📊 Cache Statistics:")
        print(f"   Community caches: {stats['community_caches']}")
        print(f"   Summary caches: {stats['summary_caches']}")
        print(f"   Total communities: {stats['total_cached_communities']}")
        print(f"   Cache size: {stats['cache_dir_size_mb']:.2f} MB")
        
        # Test loading a few random communities
        print(f"\n🧪 Testing cache loading...")
        
        try:
            # Test basic community loading
            communities = await self.cache.load_communities()
            if communities:
                total_communities = sum(len(cl) for cl in communities.values())
                print(f"   ✅ Successfully loaded {total_communities} communities")
                
                # Test summary loading for first few communities
                test_count = 0
                for community_type, community_list in communities.items():
                    for community in community_list[:2]:  # Test first 2 of each type
                        summary = await self.cache.load_summary(community.id, "openai")
                        if summary:
                            test_count += 1
                
                print(f"   ✅ Successfully loaded {test_count} cached summaries")
            else:
                print(f"   ⚠️  No cached communities found")
        
        except Exception as e:
            print(f"   ❌ Cache validation error: {e}")
        
        print(f"✅ Cache validation complete")
    
    async def clear_cache(self, cache_type: str = "all"):
        """
        Clear cache data
        """
        print(f"🗑️  Clearing {cache_type} cache...")
        await self.cache.clear_cache(cache_type)
        print(f"✅ Cache cleared")
    
    async def export_cache_metadata(self, output_file: str = "graphrag_cache_metadata.json"):
        """
        Export cache metadata for monitoring and debugging
        """
        print(f"📤 Exporting cache metadata to {output_file}...")
        
        stats = await self.cache.get_cache_stats()
        
        # Add detailed information
        metadata = {
            "cache_stats": stats,
            "timestamp": time.time(),
            "cache_structure": {
                "communities_dir": str(self.cache.communities_dir),
                "summaries_dir": str(self.cache.summaries_dir),
                "metadata_dir": str(self.cache.metadata_dir)
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Metadata exported to {output_file}")

async def main():
    parser = argparse.ArgumentParser(description="GraphRAG Cache Manager")
    parser.add_argument("command", choices=["warm", "validate", "clear", "export", "stats"], 
                       help="Command to execute")
    parser.add_argument("--cache-type", choices=["all", "communities", "summaries"], 
                       default="all", help="Cache type for clear command")
    parser.add_argument("--output", default="graphrag_cache_metadata.json",
                       help="Output file for export command")
    
    args = parser.parse_args()
    
    manager = GraphRAGCacheManager()
    
    try:
        if args.command == "warm":
            await manager.warm_cache_for_production()
        elif args.command == "validate":
            await manager.validate_cache()
        elif args.command == "clear":
            await manager.clear_cache(args.cache_type)
        elif args.command == "export":
            await manager.export_cache_metadata(args.output)
        elif args.command == "stats":
            stats = await manager.cache.get_cache_stats()
            print("📊 GraphRAG Cache Statistics:")
            print(json.dumps(stats, indent=2))
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import time
    asyncio.run(main()) 