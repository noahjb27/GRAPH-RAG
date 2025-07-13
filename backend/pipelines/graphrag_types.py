"""
GraphRAG Data Types - Shared data structures for GraphRAG transport pipeline
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field

@dataclass
class TransportCommunity:
    """Represents a community in the transport network"""
    
    id: str
    type: str  # geographic, operational, temporal, service_type
    level: int  # hierarchical level (0 = highest, increasing = more granular)
    name: str
    stations: List[Dict[str, Any]]
    lines: List[Dict[str, Any]]
    administrative_areas: List[Dict[str, Any]]
    temporal_span: Dict[str, Any]
    geographic_bounds: Dict[str, Any]
    operational_metrics: Dict[str, Any]
    political_context: str  # east, west, unified
    parent_community: Optional[str] = None
    child_communities: List[str] = field(default_factory=list)
    summary: Optional[str] = None
    
    def get_station_count(self) -> int:
        return len(self.stations)
    
    def get_line_count(self) -> int:
        return len(self.lines)
    
    def get_transport_types(self) -> Set[str]:
        return {line.get('type', 'unknown') for line in self.lines}
    
    def get_political_distribution(self) -> Dict[str, int]:
        """Get distribution of stations by political side"""
        distribution = {"east": 0, "west": 0, "unified": 0}
        for station in self.stations:
            side = station.get('political_side', 'unified')
            distribution[side] = distribution.get(side, 0) + 1
        return distribution 