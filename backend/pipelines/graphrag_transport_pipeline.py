"""
GraphRAG-inspired Transport Pipeline - Hierarchical community detection and analysis for transport networks
Adapted from Microsoft's GraphRAG approach for structured transport network data
"""

import json
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict

import networkx as nx
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np

# Try to import Leiden from graspologic, fallback to Louvain if not available
try:
    from graspologic.partition import leiden
    LEIDEN_AVAILABLE = True
except ImportError:
    print("Warning: graspologic not available, falling back to Louvain community detection")
    from networkx.algorithms.community import louvain_communities
    LEIDEN_AVAILABLE = False

from .base_pipeline import BasePipeline, PipelineResult
from ..llm_clients.client_factory import create_llm_client
from ..database.neo4j_client import neo4j_client
from ..config import settings
from .graphrag_cache import graphrag_cache
from .graphrag_types import TransportCommunity



class TransportCommunityDetector:
    """
    Detects hierarchical communities in transport network using multiple strategies
    """
    
    def __init__(self, neo4j_client):
        self.neo4j_client = neo4j_client
        
    async def detect_all_communities(self, year_filter: Optional[int] = None, use_cache: bool = True) -> Dict[str, List[TransportCommunity]]:
        """
        Detect communities across all dimensions with caching support
        """
        
        # Try to load from cache first
        if use_cache:
            cached_communities = await graphrag_cache.load_communities(year_filter)
            if cached_communities is not None:
                return cached_communities
        
        print(f"Detecting communities for year_filter={year_filter}...")
        
        communities = {}
        
        # Get base network data
        network_data = await self._get_network_data(year_filter)
        
        # Detect different types of communities
        communities['geographic'] = await self._detect_geographic_communities(network_data)
        communities['operational'] = await self._detect_operational_communities(network_data)
        communities['temporal'] = await self._detect_temporal_communities(network_data)
        communities['service_type'] = await self._detect_service_type_communities(network_data)
        
        # Create hierarchical structure
        hierarchical_communities = self._create_hierarchy(communities)
        
        # Save to cache
        if use_cache:
            await graphrag_cache.save_communities(hierarchical_communities, year_filter)
        
        return hierarchical_communities
    
    async def _get_network_data(self, year_filter: Optional[int] = None) -> Dict[str, Any]:
        """
        Get comprehensive network data for community detection
        """
        
        # Base query for stations and lines
        station_query = """
        MATCH (s:Station)-[:SERVES]-(l:Line)
        """
        if year_filter:
            station_query += f"""
            MATCH (s)-[:IN_YEAR]->(y:Year {{year: {year_filter}}})
            """
        
        station_query += """
        OPTIONAL MATCH (s)-[:LOCATED_IN]->(o:HistoricalOrtsteil)-[:PART_OF]->(b:HistoricalBezirk)
        RETURN s.name as station_name, s.type as station_type, s.east_west as station_east_west,
               s.latitude as latitude, s.longitude as longitude,
               l.name as line_name, l.type as line_type, l.east_west as line_east_west,
               l.capacity as capacity, l.frequency as frequency, l.length_km as length_km,
               o.name as ortsteil_name, o.snapshot_year as ortsteil_year,
               b.name as bezirk_name, b.east_west as bezirk_east_west
        """
        
        result = await self.neo4j_client.execute_read_query(station_query)
        
        if not result.success:
            return {}
        
        # Process results into structured format
        stations = {}
        lines = {}
        
        for record in result.records:
            station_key = f"{record['station_name']}_{record['station_type']}"
            line_key = f"{record['line_name']}_{record['line_type']}"
            
            if station_key not in stations:
                stations[station_key] = {
                    'name': record['station_name'],
                    'type': record['station_type'],
                    'east_west': record['station_east_west'],
                    'latitude': record['latitude'],
                    'longitude': record['longitude'],
                    'ortsteil': record['ortsteil_name'],
                    'bezirk': record['bezirk_name'],
                    'bezirk_east_west': record['bezirk_east_west'],
                    'connected_lines': set()
                }
            
            if line_key not in lines:
                lines[line_key] = {
                    'name': record['line_name'],
                    'type': record['line_type'],
                    'east_west': record['line_east_west'],
                    'capacity': record['capacity'],
                    'frequency': record['frequency'],
                    'length_km': record['length_km'],
                    'connected_stations': set()
                }
            
            stations[station_key]['connected_lines'].add(line_key)
            lines[line_key]['connected_stations'].add(station_key)
        
        # Convert sets to lists for JSON serialization
        for station in stations.values():
            station['connected_lines'] = list(station['connected_lines'])
        for line in lines.values():
            line['connected_stations'] = list(line['connected_stations'])
        
        return {
            'stations': stations,
            'lines': lines,
            'year_filter': year_filter
        }
    
    async def _detect_geographic_communities(self, network_data: Dict[str, Any]) -> List[TransportCommunity]:
        """
        Detect geographic communities based on Bezirk/Ortsteil and spatial clustering
        """
        communities = []
        stations = network_data['stations']
        lines = network_data['lines']
        
        # Level 0: By Bezirk (highest level)
        bezirk_groups = defaultdict(list)
        for station_key, station in stations.items():
            if station['bezirk']:
                bezirk_groups[station['bezirk']].append(station_key)
        
        for bezirk_name, station_keys in bezirk_groups.items():
            if len(station_keys) < 2:  # Skip very small communities
                continue
            
            community_stations = [stations[key] for key in station_keys]
            
            # Get all lines serving these stations
            all_lines = set()
            for station in community_stations:
                all_lines.update(station['connected_lines'])
            
            community_lines = [lines[line_key] for line_key in all_lines if line_key in lines]
            
            # Calculate geographic bounds
            lats = [s['latitude'] for s in community_stations if s['latitude']]
            lons = [s['longitude'] for s in community_stations if s['longitude']]
            
            geo_bounds = {
                'min_lat': min(lats) if lats else None,
                'max_lat': max(lats) if lats else None,
                'min_lon': min(lons) if lons else None,
                'max_lon': max(lons) if lons else None
            }
            
            # Operational metrics
            operational_metrics = self._calculate_operational_metrics(community_lines)
            
            # Political context
            political_context = community_stations[0]['bezirk_east_west'] if community_stations else 'unknown'
            
            community = TransportCommunity(
                id=f"geo_bezirk_{bezirk_name.lower().replace(' ', '_')}",
                type="geographic",
                level=0,
                name=f"Bezirk {bezirk_name}",
                stations=community_stations,
                lines=community_lines,
                administrative_areas=[{'name': bezirk_name, 'type': 'bezirk'}],
                temporal_span={'year_filter': network_data['year_filter']},
                geographic_bounds=geo_bounds,
                operational_metrics=operational_metrics,
                political_context=political_context
            )
            
            communities.append(community)
        
        # Level 1: By Ortsteil (more granular)
        ortsteil_groups = defaultdict(list)
        for station_key, station in stations.items():
            if station['ortsteil']:
                ortsteil_groups[station['ortsteil']].append(station_key)
        
        for ortsteil_name, station_keys in ortsteil_groups.items():
            if len(station_keys) < 2:
                continue
            
            community_stations = [stations[key] for key in station_keys]
            
            # Get all lines serving these stations
            all_lines = set()
            for station in community_stations:
                all_lines.update(station['connected_lines'])
            
            community_lines = [lines[line_key] for line_key in all_lines if line_key in lines]
            
            # Calculate geographic bounds
            lats = [s['latitude'] for s in community_stations if s['latitude']]
            lons = [s['longitude'] for s in community_stations if s['longitude']]
            
            geo_bounds = {
                'min_lat': min(lats) if lats else None,
                'max_lat': max(lats) if lats else None,
                'min_lon': min(lons) if lons else None,
                'max_lon': max(lons) if lons else None
            }
            
            operational_metrics = self._calculate_operational_metrics(community_lines)
            
            # Find parent bezirk
            parent_bezirk = community_stations[0]['bezirk'] if community_stations else None
            political_context = community_stations[0]['bezirk_east_west'] if community_stations else 'unknown'
            
            community = TransportCommunity(
                id=f"geo_ortsteil_{ortsteil_name.lower().replace(' ', '_')}",
                type="geographic",
                level=1,
                name=f"Ortsteil {ortsteil_name}",
                stations=community_stations,
                lines=community_lines,
                administrative_areas=[
                    {'name': ortsteil_name, 'type': 'ortsteil'},
                    {'name': parent_bezirk, 'type': 'bezirk'}
                ],
                temporal_span={'year_filter': network_data['year_filter']},
                geographic_bounds=geo_bounds,
                operational_metrics=operational_metrics,
                political_context=political_context,
                parent_community=f"geo_bezirk_{parent_bezirk.lower().replace(' ', '_')}" if parent_bezirk else None
            )
            
            communities.append(community)
        
        return communities
    
    async def _detect_operational_communities(self, network_data: Dict[str, Any]) -> List[TransportCommunity]:
        """
        Detect operational communities based on network topology and service patterns
        """
        communities = []
        stations = network_data['stations']
        lines = network_data['lines']
        
        # Create NetworkX graph for topological analysis
        G = nx.Graph()
        
        # Add nodes (stations)
        for station_key, station in stations.items():
            G.add_node(station_key, **station)
        
        # Add edges (connections via lines)
        for line_key, line in lines.items():
            connected_stations = line['connected_stations']
            for i in range(len(connected_stations)):
                for j in range(i+1, len(connected_stations)):
                    if connected_stations[i] in G.nodes and connected_stations[j] in G.nodes:
                        G.add_edge(connected_stations[i], connected_stations[j], line=line_key)
        
        # Use Leiden algorithm for community detection (or Louvain as fallback)
        try:
            if LEIDEN_AVAILABLE:
                # Use Leiden algorithm from graspologic
                leiden_communities_result = leiden(G, resolution=1.0)
            else:
                # Fallback to Louvain algorithm from NetworkX
                leiden_communities_result = louvain_communities(G, resolution=1.0)
            
            for idx, community_nodes in enumerate(leiden_communities_result):
                if len(community_nodes) < 3:  # Skip very small communities
                    continue
                
                community_stations = [stations[node] for node in community_nodes if node in stations]
                
                # Get all lines serving these stations
                all_lines = set()
                for station in community_stations:
                    all_lines.update(station['connected_lines'])
                
                community_lines = [lines[line_key] for line_key in all_lines if line_key in lines]
                
                # Calculate operational metrics
                operational_metrics = self._calculate_operational_metrics(community_lines)
                
                # Geographic bounds
                lats = [s['latitude'] for s in community_stations if s['latitude']]
                lons = [s['longitude'] for s in community_stations if s['longitude']]
                
                geo_bounds = {
                    'min_lat': min(lats) if lats else None,
                    'max_lat': max(lats) if lats else None,
                    'min_lon': min(lons) if lons else None,
                    'max_lon': max(lons) if lons else None
                }
                
                # Determine political context
                political_contexts = [s['east_west'] for s in community_stations if s['east_west']]
                if political_contexts:
                    political_context = max(set(political_contexts), key=political_contexts.count)
                else:
                    political_context = 'unknown'
                
                community = TransportCommunity(
                    id=f"operational_cluster_{idx}",
                    type="operational",
                    level=0,
                    name=f"Operational Cluster {idx + 1}",
                    stations=community_stations,
                    lines=community_lines,
                    administrative_areas=[],
                    temporal_span={'year_filter': network_data['year_filter']},
                    geographic_bounds=geo_bounds,
                    operational_metrics=operational_metrics,
                    political_context=political_context
                )
                
                communities.append(community)
        
        except Exception as e:
            print(f"Error in operational community detection: {e}")
            # Fallback to simple connectivity-based clustering
            pass
        
        return communities
    
    async def _detect_service_type_communities(self, network_data: Dict[str, Any]) -> List[TransportCommunity]:
        """
        Detect communities based on transport service types
        """
        communities = []
        stations = network_data['stations']
        lines = network_data['lines']
        
        # Group by transport type
        service_type_groups = defaultdict(list)
        
        for line_key, line in lines.items():
            service_type_groups[line['type']].append(line_key)
        
        for service_type, line_keys in service_type_groups.items():
            if len(line_keys) < 2:
                continue
            
            community_lines = [lines[line_key] for line_key in line_keys]
            
            # Get all stations served by these lines
            all_stations = set()
            for line in community_lines:
                all_stations.update(line['connected_stations'])
            
            community_stations = [stations[station_key] for station_key in all_stations if station_key in stations]
            
            # Calculate operational metrics
            operational_metrics = self._calculate_operational_metrics(community_lines)
            
            # Geographic bounds
            lats = [s['latitude'] for s in community_stations if s['latitude']]
            lons = [s['longitude'] for s in community_stations if s['longitude']]
            
            geo_bounds = {
                'min_lat': min(lats) if lats else None,
                'max_lat': max(lats) if lats else None,
                'min_lon': min(lons) if lons else None,
                'max_lon': max(lons) if lons else None
            }
            
            # Political context
            political_contexts = [s['east_west'] for s in community_stations if s['east_west']]
            if political_contexts:
                political_context = max(set(political_contexts), key=political_contexts.count)
            else:
                political_context = 'unknown'
            
            community = TransportCommunity(
                id=f"service_{service_type}",
                type="service_type",
                level=0,
                name=f"{service_type.title()} Network",
                stations=community_stations,
                lines=community_lines,
                administrative_areas=[],
                temporal_span={'year_filter': network_data['year_filter']},
                geographic_bounds=geo_bounds,
                operational_metrics=operational_metrics,
                political_context=political_context
            )
            
            communities.append(community)
        
        return communities
    
    async def _detect_temporal_communities(self, network_data: Dict[str, Any]) -> List[TransportCommunity]:
        """
        Detect temporal communities based on activity periods and evolution patterns
        Supports both synchronic (snapshot-based) and diachronic (evolution-based) analysis
        """
        communities = []
        
        # Get temporal data from CoreStation activity periods
        temporal_query = """
        MATCH (cs:CoreStation)
        WHERE cs.activity_period IS NOT NULL
        RETURN cs.name, cs.core_id, cs.activity_period, cs.east_west
        """
        
        result = await self.neo4j_client.execute_read_query(temporal_query)
        
        if not result.success:
            print("Failed to get temporal data from CoreStation")
            return communities
        
        print(f"Found {len(result.records)} CoreStations with temporal data")
        
        # Parse activity periods and group by temporal patterns
        temporal_groups = defaultdict(list)
        evolution_groups = defaultdict(list)
        snapshot_groups = defaultdict(list)
        
        for record in result.records:
            try:
                # Convert Neo4j record to dictionary
                record_dict = dict(record)
                
                activity_period_str = record_dict.get('cs.activity_period', '')
                if not activity_period_str:
                    continue
                    
                activity_period = json.loads(activity_period_str)
                start_year = activity_period.get('start_snapshot')
                end_year = activity_period.get('end_snapshot')
                observed_snapshots = activity_period.get('observed_snapshots', [])
                
                # Create station record for community
                station_record = {
                    'name': record_dict.get('cs.name', 'Unknown'),
                    'core_id': record_dict.get('cs.core_id', ''),
                    'east_west': record_dict.get('cs.east_west', 'unknown'),
                    'activity_period': activity_period
                }
                
                # Create temporal era buckets (diachronic analysis)
                if start_year and end_year:
                    if start_year <= 1949:
                        temporal_groups['post_war_1946_1949'].append(station_record)
                    elif start_year <= 1961:
                        temporal_groups['pre_wall_1950_1961'].append(station_record)
                    elif start_year <= 1975:
                        temporal_groups['wall_era_1962_1975'].append(station_record)
                    else:
                        temporal_groups['late_era_1976_1989'].append(station_record)
                
                # Create evolution pattern buckets
                duration = end_year - start_year if start_year and end_year else 0
                if duration == 0:
                    evolution_groups['single_year_operations'].append(station_record)
                elif duration <= 5:
                    evolution_groups['short_term_operations'].append(station_record)
                elif duration <= 15:
                    evolution_groups['medium_term_operations'].append(station_record)
                else:
                    evolution_groups['long_term_operations'].append(station_record)
                
                # Create snapshot-specific buckets for key years
                key_years = [1946, 1950, 1961, 1970, 1975, 1980, 1989]
                for year in key_years:
                    if year in observed_snapshots:
                        snapshot_record = {
                            **station_record,
                            'snapshot_year': year
                        }
                        snapshot_groups[f'snapshot_{year}'].append(snapshot_record)
                        
            except (json.JSONDecodeError, KeyError) as e:
                station_name = record_dict.get('cs.name', 'unknown') if 'record_dict' in locals() else 'unknown'
                print(f"Error parsing activity period for {station_name}: {e}")
                continue
        
        # Create diachronic communities (temporal eras)
        for period_name, stations_data in temporal_groups.items():
            if len(stations_data) < 10:  # Reduced threshold
                continue
            
            community = TransportCommunity(
                id=f"temporal_era_{period_name}",
                type="temporal",
                level=0,
                name=f"Transport Era: {period_name.replace('_', ' ').title()}",
                stations=stations_data,
                lines=[],
                administrative_areas=[],
                temporal_span={
                    'type': 'era',
                    'period': period_name, 
                    'station_count': len(stations_data)
                },
                geographic_bounds={},
                operational_metrics={},
                political_context='mixed'
            )
            
            communities.append(community)
        
        # Create evolution pattern communities 
        for pattern_name, stations_data in evolution_groups.items():
            if len(stations_data) < 20:  # Higher threshold for evolution patterns
                continue
                
            community = TransportCommunity(
                id=f"temporal_evolution_{pattern_name}",
                type="temporal",
                level=1,
                name=f"Evolution Pattern: {pattern_name.replace('_', ' ').title()}",
                stations=stations_data,
                lines=[],
                administrative_areas=[],
                temporal_span={
                    'type': 'evolution',
                    'pattern': pattern_name,
                    'station_count': len(stations_data)
                },
                geographic_bounds={},
                operational_metrics={},
                political_context='mixed'
            )
            
            communities.append(community)
        
        # Create synchronic communities (key year snapshots)
        for snapshot_name, stations_data in snapshot_groups.items():
            if len(stations_data) < 50:  # Higher threshold for snapshots
                continue
                
            year = snapshot_name.split('_')[1]
            community = TransportCommunity(
                id=f"temporal_{snapshot_name}",
                type="temporal",
                level=2,
                name=f"Network Snapshot: {year}",
                stations=stations_data,
                lines=[],
                administrative_areas=[],
                temporal_span={
                    'type': 'snapshot',
                    'year': int(year),
                    'station_count': len(stations_data)
                },
                geographic_bounds={},
                operational_metrics={},
                political_context='mixed'
            )
            
            communities.append(community)
        
        print(f"Created {len(communities)} temporal communities")
        return communities
    
    def _calculate_operational_metrics(self, lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate operational metrics for a set of lines
        """
        if not lines:
            return {}
        
        capacities = [line['capacity'] for line in lines if line.get('capacity')]
        frequencies = [line['frequency'] for line in lines if line.get('frequency')]
        lengths = [line['length_km'] for line in lines if line.get('length_km')]
        
        return {
            'total_lines': len(lines),
            'avg_capacity': sum(capacities) / len(capacities) if capacities else 0,
            'avg_frequency': sum(frequencies) / len(frequencies) if frequencies else 0,
            'total_length_km': sum(lengths) if lengths else 0,
            'transport_types': list(set(line['type'] for line in lines if line.get('type'))),
            'political_distribution': {
                'east': len([l for l in lines if l.get('east_west') == 'east']),
                'west': len([l for l in lines if l.get('east_west') == 'west']),
                'unified': len([l for l in lines if l.get('east_west') == 'unified'])
            }
        }
    
    def _create_hierarchy(self, communities: Dict[str, List[TransportCommunity]]) -> Dict[str, List[TransportCommunity]]:
        """
        Create hierarchical relationships between communities
        """
        # Link geographic communities (Bezirk -> Ortsteil)
        geographic_communities = communities.get('geographic', [])
        
        bezirk_communities = {c.id: c for c in geographic_communities if c.level == 0}
        ortsteil_communities = [c for c in geographic_communities if c.level == 1]
        
        for ortsteil_community in ortsteil_communities:
            if ortsteil_community.parent_community and ortsteil_community.parent_community in bezirk_communities:
                parent = bezirk_communities[ortsteil_community.parent_community]
                parent.child_communities.append(ortsteil_community.id)
        
        return communities

class TransportCommunitySummarizer:
    """
    Generates transport-specific community summaries using LLM
    """
    
    def __init__(self, llm_provider: str = "openai"):
        self.llm_provider = llm_provider
        self.llm_client = create_llm_client(llm_provider)
    
    async def summarize_community(self, community: TransportCommunity, use_cache: bool = True) -> str:
        """
        Generate a comprehensive summary of a transport community with caching support
        """
        
        # Try to load from cache first
        if use_cache:
            cached_summary = await graphrag_cache.load_summary(community.id, self.llm_provider)
            if cached_summary is not None:
                return cached_summary
        
        prompt = self._create_community_summary_prompt(community)
        
        try:
            if self.llm_client is None:
                summary = self._create_fallback_summary(community)
            else:
                response = await self.llm_client.generate(
                    prompt=prompt,
                    max_tokens=1000,
                    temperature=0.3
                )
                summary = response.text
            
            # Save to cache
            if use_cache:
                await graphrag_cache.save_summary(community.id, summary, self.llm_provider)
            
            return summary
        
        except Exception as e:
            print(f"Error generating community summary: {e}")
            fallback_summary = self._create_fallback_summary(community)
            
            # Save fallback to cache as well
            if use_cache:
                await graphrag_cache.save_summary(community.id, fallback_summary, self.llm_provider)
            
            return fallback_summary
    
    def _create_community_summary_prompt(self, community: TransportCommunity) -> str:
        """
        Create a detailed prompt for community summarization
        Handles different types of temporal analysis: era, evolution, and snapshot communities
        """
        
        station_info = f"{len(community.stations)} stations"
        line_info = f"{len(community.lines)} lines"
        transport_types = ", ".join(community.get_transport_types())
        
        # Determine if this is a temporal community and what type
        is_temporal = community.type == "temporal"
        temporal_type = None
        if is_temporal and 'type' in community.temporal_span:
            temporal_type = community.temporal_span['type']
        
        prompt = f"""
        Analyze this Berlin transport network community and provide a comprehensive summary:

        ## Community: {community.name}
        **Type**: {community.type.title()}
        **Level**: {community.level}
        **Political Context**: {community.political_context}
        """
        
        # Add temporal-specific context
        if is_temporal:
            if temporal_type == "era":
                prompt += f"""
        **Temporal Analysis Type**: Diachronic (Historical Era)
        **Time Period**: {community.temporal_span.get('period', 'Unknown')}
        **Analysis Focus**: Development patterns and changes during this historical era
        """
            elif temporal_type == "evolution":
                prompt += f"""
        **Temporal Analysis Type**: Evolution Pattern Analysis
        **Pattern**: {community.temporal_span.get('pattern', 'Unknown')}
        **Analysis Focus**: Operational lifecycle and duration characteristics
        """
            elif temporal_type == "snapshot":
                prompt += f"""
        **Temporal Analysis Type**: Synchronic (Network Snapshot)
        **Snapshot Year**: {community.temporal_span.get('year', 'Unknown')}
        **Analysis Focus**: Network state and characteristics at this specific point in time
        """
        
        prompt += f"""

        ## Infrastructure Overview
        - **Stations**: {station_info}
        - **Lines**: {line_info}
        - **Transport Types**: {transport_types}

        ## Operational Metrics
        """
        
        if community.operational_metrics:
            metrics = community.operational_metrics
            prompt += f"""
        - **Average Capacity**: {metrics.get('avg_capacity', 'N/A')} passengers
        - **Average Frequency**: {metrics.get('avg_frequency', 'N/A')} minutes
        - **Total Network Length**: {metrics.get('total_length_km', 'N/A')} km
        - **Political Distribution**: East: {metrics.get('political_distribution', {}).get('east', 0)}, West: {metrics.get('political_distribution', {}).get('west', 0)}, Unified: {metrics.get('political_distribution', {}).get('unified', 0)}
        """
        
        if community.administrative_areas:
            areas = ", ".join([area['name'] for area in community.administrative_areas])
            prompt += f"""
        
        ## Geographic Coverage
        - **Administrative Areas**: {areas}
        """
        
        if community.geographic_bounds and any(community.geographic_bounds.values()):
            bounds = community.geographic_bounds
            prompt += f"""
        - **Geographic Bounds**: {bounds.get('min_lat', 'N/A')}-{bounds.get('max_lat', 'N/A')} lat, {bounds.get('min_lon', 'N/A')}-{bounds.get('max_lon', 'N/A')} lon
        """
        
        prompt += f"""
        
        ## Historical Context
        - **Time Period**: {community.temporal_span}
        - **Political Division**: Berlin was divided into East and West sectors during 1949-1989
        """
        
        # Customize analysis focus based on temporal type
        if is_temporal:
            if temporal_type == "era":
                prompt += """
        
        Please provide a detailed **DIACHRONIC ANALYSIS** covering:
        1. **Historical Development**: Major transport developments and policy changes during this era
        2. **Political Influence**: How East/West division shaped transport planning in this period
        3. **Infrastructure Evolution**: Key expansions, closures, or modifications
        4. **Service Changes**: How transport operations adapted to political and social conditions
        5. **Legacy Impact**: How developments in this era influenced later transport planning
        6. **Cross-Temporal Patterns**: What trends emerged during this period
        
        Focus on temporal evolution, policy impacts, and how this era fits into Berlin's transport history.
        """
            elif temporal_type == "evolution":
                prompt += """
        
        Please provide a detailed **EVOLUTION PATTERN ANALYSIS** covering:
        1. **Operational Lifecycle**: Characteristics of stations/lines with this duration pattern
        2. **Planning Strategy**: Why certain infrastructure had this temporal profile
        3. **Political Factors**: How division affected infrastructure longevity and planning
        4. **Service Adaptation**: How operations evolved based on duration characteristics
        5. **Strategic Role**: Function of short vs. long-term infrastructure in the network
        6. **Historical Context**: What historical events influenced these patterns
        
        Focus on operational patterns, planning strategies, and infrastructure lifecycle analysis.
        """
            elif temporal_type == "snapshot":
                prompt += """
        
        Please provide a detailed **SYNCHRONIC ANALYSIS** covering:
        1. **Network State**: Comprehensive overview of transport infrastructure at this point in time
        2. **Political Context**: Specific political situation and its impact on transport in this year
        3. **Service Characteristics**: Transport operations, capacity, and efficiency at this moment
        4. **Geographic Coverage**: Spatial distribution and accessibility patterns
        5. **Historical Significance**: Why this year was important for Berlin's transport development
        6. **Comparative Context**: How this snapshot compares to earlier/later periods
        
        Focus on the specific state of the network at this moment in time and its historical significance.
        """
        else:
            prompt += """
        
        Please provide a detailed analysis covering:
        1. **Network Characteristics**: Key infrastructure and connectivity patterns
        2. **Service Quality**: Operational efficiency and service levels
        3. **Geographic Significance**: Area coverage and accessibility
        4. **Historical Development**: How this community fits into Berlin's transport evolution
        5. **Political Impact**: Effects of East/West division on transport planning
        6. **Strategic Importance**: Role in the overall Berlin transport system
        
        Focus on transport infrastructure, operations, and historical significance. Be specific about the transport modes and their characteristics.
        """
        
        return prompt
    
    def _create_fallback_summary(self, community: TransportCommunity) -> str:
        """
        Create a basic summary when LLM fails
        """
        transport_types = ", ".join(community.get_transport_types())
        
        summary = f"""
        {community.name} is a {community.type} transport community containing {len(community.stations)} stations and {len(community.lines)} lines.
        
        Transport modes include: {transport_types}
        Political context: {community.political_context}
        
        This community represents an important part of Berlin's historical transport network during the period of study.
        """
        
        return summary.strip()

class GraphRAGTransportPipeline(BasePipeline):
    """
    GraphRAG-inspired pipeline for transport network analysis using hierarchical communities
    """
    
    def __init__(self):
        super().__init__(
            name="GraphRAG Transport Analysis",
            description="Hierarchical community-based transport network analysis inspired by Microsoft's GraphRAG"
        )
        
        self.community_detector = TransportCommunityDetector(neo4j_client)
        self.community_summarizer = TransportCommunitySummarizer()
        
        # Use persistent cache instead of in-memory cache
        self.cache = graphrag_cache
    
    async def process_query(
        self,
        question: str,
        llm_provider: str = "openai",
        year_filter: Optional[int] = None,
        community_types: Optional[List[str]] = None,
        **kwargs
    ) -> PipelineResult:
        """
        Process a question using GraphRAG-inspired transport analysis
        """
        
        start_time = time.time()
        
        try:
            # Step 1: Determine if this is a global or local question
            question_type = await self._analyze_question_type(question, llm_provider)
            
            if question_type == "global":
                result = await self._process_global_question(question, llm_provider, year_filter, community_types)
            else:
                result = await self._process_local_question(question, llm_provider, year_filter)
            
            execution_time = time.time() - start_time
            
            return PipelineResult(
                answer=result["answer"],
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=True,
                retrieved_context=result.get("context", []),
                metadata={
                    "question_type": question_type,
                    "year_filter": year_filter,
                    "community_types": community_types,
                    "communities_analyzed": result.get("communities_analyzed", 0)
                }
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            
            return PipelineResult(
                answer=f"I apologize, but I encountered an error analyzing the transport network: {str(e)}",
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=False,
                error_message=str(e),
                error_stage="query_processing"
            )
    
    async def _analyze_question_type(self, question: str, llm_provider: str) -> str:
        """
        Determine if question requires global (community-based) or local (specific entity) analysis
        """
        
        global_indicators = [
            "overall", "main", "key", "primary", "major", "most important",
            "trends", "patterns", "development", "evolution", "changes",
            "comparison", "compare", "differences", "similarities",
            "network", "system", "infrastructure", "coverage",
            "east", "west", "political", "division", "sector"
        ]
        
        local_indicators = [
            "specific", "particular", "individual", "single",
            "station", "line", "route", "connection",
            "how to get", "travel from", "journey", "trip"
        ]
        
        question_lower = question.lower()
        
        global_score = sum(1 for indicator in global_indicators if indicator in question_lower)
        local_score = sum(1 for indicator in local_indicators if indicator in question_lower)
        
        return "global" if global_score > local_score else "local"
    
    async def _process_global_question(
        self,
        question: str,
        llm_provider: str,
        year_filter: Optional[int] = None,
        community_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process global questions using community summaries and map-reduce approach
        """
        
                # Get or detect communities
        all_communities = await self.community_detector.detect_all_communities(year_filter)
        
        # Filter communities by type if specified
        if community_types:
            filtered_communities = []
            for community_type in community_types:
                if community_type in all_communities:
                    filtered_communities.extend(all_communities[community_type])
        else:
            filtered_communities = []
            for community_list in all_communities.values():
                filtered_communities.extend(community_list)
        
        # Generate summaries for all relevant communities
        community_summaries = []
        for community in filtered_communities:
            summary = await self.community_summarizer.summarize_community(community)
            community_summaries.append({
                "community": community,
                "summary": summary
            })
        
        # Map-reduce approach: Generate answers from each community summary
        community_answers = []
        for item in community_summaries:
            community_answer = await self._generate_community_answer(
                question, item["community"], item["summary"], llm_provider
            )
            community_answers.append(community_answer)
        
        # Reduce: Combine all community answers into final answer
        final_answer = await self._reduce_community_answers(question, community_answers, llm_provider)
        
        return {
            "answer": final_answer,
            "context": [item["summary"] for item in community_summaries],
            "communities_analyzed": len(filtered_communities)
        }
    
    async def _process_local_question(
        self,
        question: str,
        llm_provider: str,
        year_filter: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process local questions using direct graph queries
        """
        
        # For local questions, fall back to existing approaches
        # This could integrate with your existing path traversal or vector pipelines
        
        answer = f"""
        This appears to be a specific question about individual transport entities. For detailed routing and specific station/line information, I recommend using the Path Traversal or Vector pipelines which are optimized for these types of queries.
        
        The GraphRAG Transport pipeline specializes in analyzing overall network patterns, trends, and comprehensive transport system questions.
        
        Your question: "{question}"
        
        Would you like me to rephrase this as a broader transport network analysis question?
        """
        
        return {
            "answer": answer,
            "context": [],
            "communities_analyzed": 0
        }
    
    async def _generate_community_answer(
        self,
        question: str,
        community: TransportCommunity,
        summary: str,
        llm_provider: str
    ) -> str:
        """
        Generate an answer to the question based on a single community summary
        """
        
        prompt = f"""
        Based on the following transport community analysis, answer the specific question:

        Question: {question}

        Community Analysis:
        {summary}

        Please provide a focused answer that addresses the question using information from this transport community. If the community doesn't contain relevant information for the question, indicate that clearly.
        
        Keep your response concise and specific to this community's contribution to answering the question.
        """
        
        try:
            llm_client = create_llm_client(llm_provider)
            if llm_client is None:
                return f"Unable to analyze community {community.name}: LLM client not available"
                
            response = await llm_client.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3
            )
            
            return response.text
        
        except Exception as e:
            return f"Unable to analyze community {community.name}: {str(e)}"
    
    async def _reduce_community_answers(
        self,
        question: str,
        community_answers: List[str],
        llm_provider: str
    ) -> str:
        """
        Combine community answers into a comprehensive final answer
        """
        
        combined_answers = "\n\n".join([f"Community Analysis {i+1}:\n{answer}" for i, answer in enumerate(community_answers)])
        
        prompt = f"""
        You are analyzing Berlin's historical transport network (1946-1989). Based on multiple community analyses, provide a comprehensive answer to the question.

        Question: {question}

        Community Analyses:
        {combined_answers}

        Please synthesize these community analyses into a comprehensive, well-structured answer that:
        1. Directly addresses the question
        2. Integrates insights from different transport communities
        3. Provides specific examples and data where available
        4. Considers the historical context of divided Berlin
        5. Discusses transport infrastructure, operations, and development patterns

        Structure your response clearly with sections or bullet points as appropriate.
        """
        
        try:
            llm_client = create_llm_client(llm_provider)
            if llm_client is None:
                return f"I analyzed {len(community_answers)} transport communities but the LLM client is not available for synthesizing the final answer."
                
            response = await llm_client.generate(
                prompt=prompt,
                max_tokens=1500,
                temperature=0.4
            )
            
            return response.text
        
        except Exception as e:
            return f"I analyzed {len(community_answers)} transport communities but encountered an error synthesizing the final answer: {str(e)}"
    
    def get_required_capabilities(self) -> List[str]:
        """Return list of capabilities this pipeline requires"""
        return ["neo4j_database", "llm_client", "community_detection"] 