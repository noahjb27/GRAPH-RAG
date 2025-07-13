"""
GraphRAG Cache Management System
Handles persistent storage and retrieval of community detection results and LLM summaries
"""

import json
import os
import time
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import asdict
import asyncio

from .graphrag_types import TransportCommunity

class GraphRAGCache:
    """
    Manages persistent caching for GraphRAG communities and summaries
    """
    
    def __init__(self, cache_dir: str = "graphrag_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        self.communities_dir = self.cache_dir / "communities"
        self.summaries_dir = self.cache_dir / "summaries"
        self.metadata_dir = self.cache_dir / "metadata"
        
        for dir_path in [self.communities_dir, self.summaries_dir, self.metadata_dir]:
            dir_path.mkdir(exist_ok=True)
    
    def _generate_cache_key(self, year_filter: Optional[int] = None, 
                          community_types: Optional[List[str]] = None,
                          **kwargs) -> str:
        """Generate a unique cache key for the given parameters"""
        
        # Create a deterministic key from parameters
        params = {
            'year_filter': year_filter,
            'community_types': sorted(community_types) if community_types else None,
            'extra': sorted(kwargs.items()) if kwargs else None
        }
        
        key_string = json.dumps(params, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _community_to_dict(self, community: TransportCommunity) -> Dict[str, Any]:
        """Convert community to serializable dictionary"""
        return {
            'id': community.id,
            'type': community.type,
            'level': community.level,
            'name': community.name,
            'stations': community.stations,
            'lines': community.lines,
            'administrative_areas': community.administrative_areas,
            'temporal_span': community.temporal_span,
            'geographic_bounds': community.geographic_bounds,
            'operational_metrics': community.operational_metrics,
            'political_context': community.political_context,
            'parent_community': community.parent_community,
            'child_communities': community.child_communities,
            'summary': community.summary
        }
    
    def _dict_to_community(self, data: Dict[str, Any]) -> TransportCommunity:
        """Convert dictionary back to TransportCommunity"""
        return TransportCommunity(**data)
    
    async def save_communities(self, communities: Dict[str, List[TransportCommunity]], 
                              year_filter: Optional[int] = None,
                              community_types: Optional[List[str]] = None,
                              **kwargs) -> str:
        """Save community detection results to cache"""
        
        cache_key = self._generate_cache_key(year_filter, community_types, **kwargs)
        cache_file = self.communities_dir / f"{cache_key}.json"
        
        # Convert communities to serializable format
        serializable_communities = {}
        for community_type, community_list in communities.items():
            serializable_communities[community_type] = [
                self._community_to_dict(community) for community in community_list
            ]
        
        # Add metadata
        cache_data = {
            'timestamp': time.time(),
            'year_filter': year_filter,
            'community_types': community_types,
            'total_communities': sum(len(community_list) for community_list in communities.values()),
            'communities': serializable_communities
        }
        
        # Save to file
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {cache_data['total_communities']} communities to cache: {cache_key}")
        return cache_key
    
    async def load_communities(self, year_filter: Optional[int] = None,
                              community_types: Optional[List[str]] = None,
                              **kwargs) -> Optional[Dict[str, List[TransportCommunity]]]:
        """Load community detection results from cache"""
        
        cache_key = self._generate_cache_key(year_filter, community_types, **kwargs)
        cache_file = self.communities_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Convert back to TransportCommunity objects
            communities = {}
            for community_type, community_list in cache_data['communities'].items():
                communities[community_type] = [
                    self._dict_to_community(community_data) 
                    for community_data in community_list
                ]
            
            print(f"Loaded {cache_data['total_communities']} communities from cache: {cache_key}")
            return communities
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading communities cache {cache_key}: {e}")
            return None
    
    async def save_summary(self, community_id: str, summary: str, 
                          llm_provider: str = "openai") -> None:
        """Save a community summary to cache"""
        
        summary_key = f"{community_id}_{llm_provider}"
        summary_file = self.summaries_dir / f"{summary_key}.json"
        
        summary_data = {
            'community_id': community_id,
            'llm_provider': llm_provider,
            'timestamp': time.time(),
            'summary': summary
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    async def load_summary(self, community_id: str, 
                          llm_provider: str = "openai") -> Optional[str]:
        """Load a community summary from cache"""
        
        summary_key = f"{community_id}_{llm_provider}"
        summary_file = self.summaries_dir / f"{summary_key}.json"
        
        if not summary_file.exists():
            return None
        
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
            return summary_data['summary']
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading summary cache {summary_key}: {e}")
            return None
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached data"""
        
        community_files = list(self.communities_dir.glob("*.json"))
        summary_files = list(self.summaries_dir.glob("*.json"))
        
        # Analyze community caches
        total_communities = 0
        community_cache_info = []
        
        for cache_file in community_files:
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                total_communities += data.get('total_communities', 0)
                community_cache_info.append({
                    'cache_key': cache_file.stem,
                    'timestamp': data.get('timestamp', 0),
                    'year_filter': data.get('year_filter'),
                    'total_communities': data.get('total_communities', 0)
                })
            except:
                continue
        
        return {
            'community_caches': len(community_files),
            'summary_caches': len(summary_files),
            'total_cached_communities': total_communities,
            'cache_dir_size_mb': sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file()) / (1024 * 1024),
            'community_cache_details': community_cache_info
        }
    
    async def clear_cache(self, cache_type: str = "all") -> None:
        """Clear cache data"""
        
        if cache_type in ["all", "communities"]:
            for file in self.communities_dir.glob("*.json"):
                file.unlink()
        
        if cache_type in ["all", "summaries"]:
            for file in self.summaries_dir.glob("*.json"):
                file.unlink()
        
        print(f"Cleared {cache_type} cache")
    
    async def warm_cache(self, detector, summarizer, 
                        year_filters: List[Optional[int]] = [None],
                        community_type_combinations: List[Optional[List[str]]] = [None],
                        llm_providers: List[str] = ["openai"]) -> None:
        """
        Pre-warm the cache with common queries
        This is useful for production deployment
        """
        
        print("🔥 Warming GraphRAG cache...")
        
        for year_filter in year_filters:
            for community_types in community_type_combinations:
                print(f"  Detecting communities for year={year_filter}, types={community_types}")
                
                # Check if already cached
                cached_communities = await self.load_communities(year_filter, community_types)
                if cached_communities is None:
                    # Generate and cache communities
                    communities = await detector.detect_all_communities(year_filter)
                    await self.save_communities(communities, year_filter, community_types)
                    cached_communities = communities
                
                # Generate summaries for all communities
                for community_type, community_list in cached_communities.items():
                    for community in community_list:
                        for llm_provider in llm_providers:
                            # Check if summary already cached
                            cached_summary = await self.load_summary(community.id, llm_provider)
                            if cached_summary is None:
                                print(f"    Generating summary for {community.name}")
                                try:
                                    summary = await summarizer.summarize_community(community)
                                    await self.save_summary(community.id, summary, llm_provider)
                                except Exception as e:
                                    print(f"      Error generating summary: {e}")
        
        stats = await self.get_cache_stats()
        print(f"✅ Cache warming complete! {stats['total_cached_communities']} communities, {stats['summary_caches']} summaries")


# Global cache instance
graphrag_cache = GraphRAGCache() 