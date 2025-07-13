"""
Graph preprocessing service for extracting NetworkX graphs from Neo4j
Used for training node embeddings and topological similarity analysis
"""

import networkx as nx
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from ..database.neo4j_client import Neo4jClient, neo4j_client
from ..config import settings

@dataclass
class GraphExtractionResult:
    """Result from graph extraction"""
    graph: nx.Graph
    node_mapping: Dict[str, str]  # neo4j_id -> nx_node_id
    reverse_mapping: Dict[str, str]  # nx_node_id -> neo4j_id
    node_attributes: Dict[str, Dict[str, Any]]  # node attributes for embeddings
    edge_attributes: Dict[Tuple[str, str], Dict[str, Any]]  # edge attributes
    extraction_stats: Dict[str, Any]

class GraphPreprocessingService:
    """Service for extracting and preprocessing graphs from Neo4j"""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
        
    async def extract_transport_network(
        self,
        year_filter: Optional[int] = None,
        include_administrative: bool = True,
        include_temporal: bool = False,
        max_nodes: Optional[int] = None
    ) -> GraphExtractionResult:
        """
        Extract the transport network as a NetworkX graph
        
        Args:
            year_filter: Filter to specific year (e.g., 1970)
            include_administrative: Include administrative areas
            include_temporal: Include temporal relationships
            max_nodes: Limit number of nodes for testing
        """
        
        # Build the extraction query
        node_query = self._build_node_extraction_query(
            year_filter, include_administrative, max_nodes
        )
        edge_query = self._build_edge_extraction_query(
            year_filter, include_administrative, include_temporal
        )
        
        # Extract nodes
        nodes_result = await self.client.execute_read_query(node_query)
        if not nodes_result.success:
            raise Exception(f"Failed to extract nodes: {nodes_result.error_message}")
            
        # Extract edges
        edges_result = await self.client.execute_read_query(edge_query)
        if not edges_result.success:
            raise Exception(f"Failed to extract edges: {edges_result.error_message}")
            
        # Build NetworkX graph
        return self._build_networkx_graph(nodes_result.records, edges_result.records)
    
    def _build_node_extraction_query(
        self,
        year_filter: Optional[int],
        include_administrative: bool,
        max_nodes: Optional[int]
    ) -> str:
        """Build Cypher query for extracting nodes"""
        
        # Base node types: stations and lines
        node_conditions = [
            "(n:Station)",
            "(n:CoreStation)", 
            "(n:Line)",
            "(n:CoreLine)"
        ]
        
        if include_administrative:
            node_conditions.extend([
                "(n:HistoricalOrtsteil)",
                "(n:CoreOrtsteil)",
                "(n:HistoricalBezirk)",
                "(n:CoreBezirk)"
            ])
            
        # Build WHERE clause with label filters
        label_conditions = []
        for condition in node_conditions:
            # Extract label from "(n:Label)" format
            label = condition.split(":")[1].replace(")", "")
            label_conditions.append(f"n:{label}")
        
        # Build WHERE clause combining labels and year filter
        where_conditions = [f"({' OR '.join(label_conditions)})"]
        
        # Add year filter if specified
        if year_filter:
            year_conditions = [
                f"(n:Year AND n.year = {year_filter})",
                f"(NOT n:Year AND EXISTS {{ MATCH (n)-[:IN_YEAR]->(y:Year) WHERE y.year = {year_filter} }})",
                "(n:CoreStation OR n:CoreLine OR n:CoreOrtsteil OR n:CoreBezirk)"
            ]
            where_conditions.append(f"({' OR '.join(year_conditions)})")
        
        query_parts = [
            "MATCH (n)",
            f"WHERE {' AND '.join(where_conditions)}"
        ]
            
        query_parts.append("""
        RETURN 
            id(n) as neo4j_id,
            labels(n) as labels,
            n.name as name,
            n.type as type,
            n.east_west as political_side,
            n.latitude as latitude,
            n.longitude as longitude,
            n.frequency as frequency,
            n.capacity as capacity,
            properties(n) as properties
        """)
        
        if max_nodes:
            query_parts.append(f"LIMIT {max_nodes}")
            
        return "\n".join(query_parts)
    
    def _build_edge_extraction_query(
        self,
        year_filter: Optional[int],
        include_administrative: bool,
        include_temporal: bool
    ) -> str:
        """Build Cypher query for extracting edges"""
        
        # Core transport relationships
        rel_conditions = [
            "SERVES", "CONNECTS_TO", "SERVES_CORE"
        ]
        
        if include_administrative:
            rel_conditions.extend(["LOCATED_IN", "PART_OF"])
            
        if include_temporal:
            rel_conditions.extend(["HAS_SNAPSHOT", "IN_YEAR"])
            
        query_parts = [
            f"MATCH (a)-[r:{'|'.join(rel_conditions)}]->(b)"
        ]
        
        # Add year filter if specified
        if year_filter:
            query_parts.append(f"""
            WHERE (r.year = {year_filter} OR r.year IS NULL)
               AND ((a:Year AND a.year = {year_filter}) OR NOT a:Year)
               AND ((b:Year AND b.year = {year_filter}) OR NOT b:Year)
            """)
            
        query_parts.append("""
        RETURN 
            id(a) as source_id,
            id(b) as target_id,
            type(r) as relationship_type,
            r.distance_meters as distance,
            r.hourly_capacity as capacity,
            r.hourly_services as services,
            r.frequencies as frequencies,
            properties(r) as properties
        """)
        
        return "\n".join(query_parts)
    
    def _build_networkx_graph(
        self,
        node_records: List[Dict[str, Any]],
        edge_records: List[Dict[str, Any]]
    ) -> GraphExtractionResult:
        """Build NetworkX graph from query results"""
        
        G = nx.Graph()
        node_mapping = {}
        reverse_mapping = {}
        node_attributes = {}
        edge_attributes = {}
        
        # Add nodes
        for i, record in enumerate(node_records):
            neo4j_id = str(record["neo4j_id"])
            nx_node_id = f"n_{i}"
            
            # Store mappings
            node_mapping[neo4j_id] = nx_node_id
            reverse_mapping[nx_node_id] = neo4j_id
            
            # Prepare node attributes for embedding
            labels = record.get("labels", [])
            properties = record.get("properties", {})
            
            # Create feature vector components
            attributes = {
                "name": record.get("name", ""),
                "type": record.get("type", ""),
                "political_side": record.get("political_side", ""),
                "latitude": record.get("latitude"),
                "longitude": record.get("longitude"),
                "frequency": record.get("frequency"),
                "capacity": record.get("capacity"),
                "labels": labels,
                "is_station": any(label in labels for label in ["Station", "CoreStation"]),
                "is_line": any(label in labels for label in ["Line", "CoreLine"]),
                "is_administrative": any(label in labels for label in ["HistoricalOrtsteil", "CoreOrtsteil", "HistoricalBezirk", "CoreBezirk"]),
                "properties": properties
            }
            
            G.add_node(nx_node_id, **attributes)
            node_attributes[nx_node_id] = attributes
        
        # Add edges
        for record in edge_records:
            source_neo4j = str(record["source_id"])
            target_neo4j = str(record["target_id"])
            
            # Skip if nodes not in our mapping (filtered out)
            if source_neo4j not in node_mapping or target_neo4j not in node_mapping:
                continue
                
            source_nx = node_mapping[source_neo4j]
            target_nx = node_mapping[target_neo4j]
            
            # Relationship attributes
            rel_type = record.get("relationship_type", "")
            distance = record.get("distance")
            capacity = record.get("capacity")
            services = record.get("services")
            frequencies = record.get("frequencies")
            properties = record.get("properties", {})
            
            # Calculate edge weight based on relationship type and actual properties
            edge_weight = self._calculate_edge_weight(rel_type, capacity, distance, services)
            
            edge_attrs = {
                "relationship_type": rel_type,
                "weight": edge_weight,
                "distance": distance,
                "capacity": capacity,
                "services": services,
                "frequencies": frequencies,
                "properties": properties
            }
            
            G.add_edge(source_nx, target_nx, **edge_attrs)
            edge_attributes[(source_nx, target_nx)] = edge_attrs
        
        # Extraction statistics
        num_nodes = G.number_of_nodes()
        num_edges = G.number_of_edges()
        
        # Calculate average degree safely
        if num_nodes > 0:
            # For undirected graph: average degree = 2 * edges / nodes
            avg_degree = (2 * num_edges) / num_nodes
        else:
            avg_degree = 0.0
            
        stats = {
            "total_nodes": num_nodes,
            "total_edges": num_edges,
            "node_types": self._analyze_node_types(node_attributes),
            "edge_types": self._analyze_edge_types(edge_attributes),
            "is_connected": nx.is_connected(G) if num_nodes > 0 else False,
            "number_of_components": nx.number_connected_components(G),
            "average_degree": avg_degree
        }
        
        return GraphExtractionResult(
            graph=G,
            node_mapping=node_mapping,
            reverse_mapping=reverse_mapping,
            node_attributes=node_attributes,
            edge_attributes=edge_attributes,
            extraction_stats=stats
        )
    
    def _calculate_edge_weight(
        self,
        rel_type: str,
        capacity: Optional[float],
        distance: Optional[float],
        services: Optional[float]
    ) -> float:
        """Calculate edge weight for graph traversal and embeddings"""
        
        # Base weights by relationship type (lower = closer)
        type_weights = {
            'SERVES': 1.0,
            'SERVES_CORE': 1.1,
            'CONNECTS_TO': 1.2,
            'LOCATED_IN': 1.5,
            'PART_OF': 2.0,
            'HAS_SNAPSHOT': 2.5,
            'IN_YEAR': 3.0
        }
        
        base_weight = type_weights.get(rel_type, 2.0)
        
        # Incorporate additional factors based on actual properties
        if capacity is not None and capacity > 0:
            # Higher capacity means stronger connection (lower weight)
            base_weight /= max(capacity / 1000.0, 0.1)  # Normalize by 1000 and avoid division by zero
        if services is not None and services > 0:
            # More services means stronger connection (lower weight)
            base_weight /= max(services / 10.0, 0.1)  # Normalize by 10 and avoid division by zero
        if distance is not None and distance > 0:
            # Normalize distance (assume max 50km in Berlin)
            normalized_distance = min(distance / 50000.0, 1.0)
            base_weight *= (1.0 + normalized_distance)
            
        return base_weight
    
    def _analyze_node_types(self, node_attributes: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        """Analyze distribution of node types"""
        type_counts = {}
        for attrs in node_attributes.values():
            node_type = attrs.get("type", "unknown")
            type_counts[node_type] = type_counts.get(node_type, 0) + 1
        return type_counts
    
    def _analyze_edge_types(self, edge_attributes: Dict[Tuple[str, str], Dict[str, Any]]) -> Dict[str, int]:
        """Analyze distribution of edge types"""
        type_counts = {}
        for attrs in edge_attributes.values():
            rel_type = attrs.get("relationship_type", "unknown")
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
        return type_counts

# Singleton instance
_graph_preprocessing_service = None

def get_graph_preprocessing_service() -> GraphPreprocessingService:
    """Get singleton graph preprocessing service"""
    global _graph_preprocessing_service
    if _graph_preprocessing_service is None:
        _graph_preprocessing_service = GraphPreprocessingService(neo4j_client)
    return _graph_preprocessing_service 