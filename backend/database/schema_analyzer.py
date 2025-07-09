"""
Schema analyzer for Neo4j graph database
Extracts and analyzes schema information for Cypher generation
"""

from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field
from .neo4j_client import Neo4jClient, Neo4jQueryResult

@dataclass
class NodeTypeInfo:
    """Information about a node type (label)"""
    label: str
    count: int
    properties: Dict[str, Any]
    sample_properties: Dict[str, Any]
    
@dataclass 
class RelationshipTypeInfo:
    """Information about a relationship type"""
    type: str
    count: int
    properties: Dict[str, Any]
    start_labels: Set[str]
    end_labels: Set[str]
    sample_properties: Dict[str, Any]

@dataclass
class GraphSchema:
    """Complete graph schema information"""
    node_types: Dict[str, NodeTypeInfo] = field(default_factory=dict)
    relationship_types: Dict[str, RelationshipTypeInfo] = field(default_factory=dict) 
    total_nodes: int = 0
    total_relationships: int = 0
    available_years: List[int] = field(default_factory=list)
    key_entities: Dict[str, List[str]] = field(default_factory=dict)
    
    def get_schema_summary(self) -> str:
        """Get human-readable schema summary for LLM context"""
        summary = [
            "=== NEO4J GRAPH SCHEMA ===",
            f"Total Nodes: {self.total_nodes:,}",
            f"Total Relationships: {self.total_relationships:,}",
            f"Available Years: {self.available_years}",
            "",
            "=== NODE TYPES ===",
        ]
        
        for label, info in self.node_types.items():
            summary.append(f"{label} ({info.count:,} nodes)")
            if info.properties:
                prop_list = [f"  - {prop}: {ptype}" for prop, ptype in info.properties.items()]
                summary.extend(prop_list)
            summary.append("")
            
        summary.append("=== RELATIONSHIP TYPES ===")
        for rel_type, info in self.relationship_types.items():
            summary.append(f"{rel_type} ({info.count:,} relationships)")
            summary.append(f"  From: {', '.join(info.start_labels)}")
            summary.append(f"  To: {', '.join(info.end_labels)}")
            if info.properties:
                prop_list = [f"  - {prop}: {ptype}" for prop, ptype in info.properties.items()]
                summary.extend(prop_list)
            summary.append("")
            
        if self.key_entities:
            summary.append("=== KEY ENTITIES ===")
            for entity_type, entities in self.key_entities.items():
                summary.append(f"{entity_type}: {', '.join(entities[:10])}")  # First 10
                if len(entities) > 10:
                    summary.append(f"  ... and {len(entities) - 10} more")
            summary.append("")
            
        return "\n".join(summary)

class SchemaAnalyzer:
    """Analyzes Neo4j graph schema for Cypher generation"""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.client = neo4j_client
        self._cached_schema: Optional[GraphSchema] = None
        
    async def analyze_schema(self, force_refresh: bool = False) -> GraphSchema:
        """Analyze and return complete graph schema"""
        
        if self._cached_schema and not force_refresh:
            return self._cached_schema
            
        schema = GraphSchema()
        
        # Get basic counts
        basic_info = await self.client.get_database_info()
        schema.total_nodes = basic_info.get("node_count", 0)
        schema.total_relationships = basic_info.get("relationship_count", 0) 
        schema.available_years = basic_info.get("available_years", [])
        
        # Analyze node types
        await self._analyze_node_types(schema)
        
        # Analyze relationship types
        await self._analyze_relationship_types(schema)
        
        # Extract key entities
        await self._extract_key_entities(schema)
        
        self._cached_schema = schema
        return schema
    
    async def _analyze_node_types(self, schema: GraphSchema):
        """Analyze all node types and their properties"""
        
        # Get all labels
        result = await self.client.execute_read_query(
            "CALL db.labels() YIELD label RETURN label"
        )
        
        if not result.success:
            return
            
        labels = [record["label"] for record in result.records]
        
        for label in labels:
            # Get node count
            count_result = await self.client.execute_read_query(
                f"MATCH (n:`{label}`) RETURN count(n) as count"
            )
            
            count = count_result.records[0]["count"] if count_result.success else 0
            
            # Get property information
            props_result = await self.client.execute_read_query(f"""
                MATCH (n:`{label}`)
                WITH n, keys(n) as props
                UNWIND props as prop
                RETURN prop, 
                       count(*) as frequency,
                       collect(DISTINCT type(n[prop]))[0..5] as types
                ORDER BY frequency DESC
                LIMIT 20
            """)
            
            properties = {}
            for record in props_result.records:
                prop_name = record["prop"]
                prop_types = record["types"]
                properties[prop_name] = prop_types[0] if prop_types else "unknown"
            
            # Get sample properties
            sample_result = await self.client.execute_read_query(f"""
                MATCH (n:`{label}`)
                RETURN properties(n) as props
                LIMIT 3
            """)
            
            sample_properties = {}
            if sample_result.success and sample_result.records:
                sample_properties = sample_result.records[0]["props"]
            
            schema.node_types[label] = NodeTypeInfo(
                label=label,
                count=count,
                properties=properties,
                sample_properties=sample_properties
            )
    
    async def _analyze_relationship_types(self, schema: GraphSchema):
        """Analyze all relationship types and their properties"""
        
        # Get all relationship types
        result = await self.client.execute_read_query(
            "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        )
        
        if not result.success:
            return
            
        rel_types = [record["relationshipType"] for record in result.records]
        
        for rel_type in rel_types:
            # Get relationship count and patterns
            pattern_result = await self.client.execute_read_query(f"""
                MATCH (start)-[r:`{rel_type}`]->(end)
                RETURN count(r) as count,
                       collect(DISTINCT labels(start)[0]) as start_labels,
                       collect(DISTINCT labels(end)[0]) as end_labels
            """)
            
            count = 0
            start_labels = set()
            end_labels = set()
            
            if pattern_result.success and pattern_result.records:
                record = pattern_result.records[0]
                count = record["count"]
                start_labels = set(record["start_labels"])
                end_labels = set(record["end_labels"])
            
            # Get property information
            props_result = await self.client.execute_read_query(f"""
                MATCH ()-[r:`{rel_type}`]->()
                WITH r, keys(r) as props
                UNWIND props as prop
                RETURN prop,
                       count(*) as frequency,
                       collect(DISTINCT type(r[prop]))[0..3] as types
                ORDER BY frequency DESC
                LIMIT 10
            """)
            
            properties = {}
            for record in props_result.records:
                prop_name = record["prop"]
                prop_types = record["types"]
                properties[prop_name] = prop_types[0] if prop_types else "unknown"
            
            # Get sample properties
            sample_result = await self.client.execute_read_query(f"""
                MATCH ()-[r:`{rel_type}`]->()
                RETURN properties(r) as props
                LIMIT 1
            """)
            
            sample_properties = {}
            if sample_result.success and sample_result.records:
                sample_properties = sample_result.records[0]["props"]
            
            schema.relationship_types[rel_type] = RelationshipTypeInfo(
                type=rel_type,
                count=count,
                properties=properties,
                start_labels=start_labels,
                end_labels=end_labels,
                sample_properties=sample_properties
            )
    
    async def _extract_key_entities(self, schema: GraphSchema):
        """Extract key entities for context"""
        
        key_queries = {
            "stations": """
                MATCH (s:Station)
                WHERE s.name IS NOT NULL
                RETURN DISTINCT s.name as name
                ORDER BY s.name
                LIMIT 50
            """,
            "lines": """
                MATCH (l:Line)
                WHERE l.name IS NOT NULL  
                RETURN DISTINCT l.name as name, l.type as type
                ORDER BY l.name
                LIMIT 30
            """,
            "ortsteile": """
                MATCH (o:HistoricalOrtsteil)
                WHERE o.name IS NOT NULL
                RETURN DISTINCT o.name as name
                ORDER BY o.name  
                LIMIT 30
            """,
            "bezirke": """
                MATCH (b:HistoricalBezirk)
                WHERE b.name IS NOT NULL
                RETURN DISTINCT b.name as name
                ORDER BY b.name
                LIMIT 20
            """
        }
        
        for entity_type, query in key_queries.items():
            result = await self.client.execute_read_query(query)
            if result.success:
                if entity_type == "lines":
                    entities = [f"{r['name']} ({r['type']})" for r in result.records]
                else:
                    entities = [r["name"] for r in result.records]
                schema.key_entities[entity_type] = entities
    
    async def get_schema_for_cypher_generation(self) -> str:
        """Get schema information optimized for Cypher generation"""
        
        schema = await self.analyze_schema()
        
        # Create concise schema for LLM
        cypher_schema = [
            "=== GRAPH SCHEMA FOR CYPHER GENERATION ===",
            "",
            "Node Labels:",
        ]
        
        for label, info in schema.node_types.items():
            props = ", ".join([f"{k}:{v}" for k, v in list(info.properties.items())[:5]])
            cypher_schema.append(f"- {label} ({info.count:,} nodes) - Properties: {props}")
        
        cypher_schema.append("\nRelationship Types:")
        for rel_type, info in schema.relationship_types.items():
            start_end = f"{'/'.join(info.start_labels)} -> {'/'.join(info.end_labels)}"
            props = ", ".join([f"{k}:{v}" for k, v in list(info.properties.items())[:3]])
            cypher_schema.append(f"- {rel_type} ({info.count:,}) - {start_end}")
            if props:
                cypher_schema.append(f"  Properties: {props}")
        
        cypher_schema.append(f"\nAvailable Years: {schema.available_years}")
        
        # Add key entities for reference
        if schema.key_entities:
            cypher_schema.append("\nKey Entities:")
            for entity_type, entities in schema.key_entities.items():
                cypher_schema.append(f"- {entity_type}: {', '.join(entities[:10])}")
        
        return "\n".join(cypher_schema) 