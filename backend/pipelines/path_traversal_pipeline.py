"""
Path Traversal Pipeline - Neighborhood/Path-based retrieval from graph structure
Finds paths between anchor nodes mentioned in user questions
"""

import time
import re
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from .base_pipeline import BasePipeline, PipelineResult
from ..llm_clients.client_factory import create_llm_client
from ..database.neo4j_client import neo4j_client
from ..database.schema_analyzer import SchemaAnalyzer
from ..database.query_executor import QueryExecutor
from ..config import settings

@dataclass
class PathTraversalResult:
    """Result from path traversal operations"""
    anchor_nodes: List[Dict[str, Any]]
    paths: List[Dict[str, Any]]
    subgraph_edges: List[Dict[str, Any]]
    traversal_stats: Dict[str, Any]

class PathTraversalPipeline(BasePipeline):
    """
    Path Traversal Pipeline for finding connections between entities
    
    Process:
    1. Anchor detection - Find entities mentioned in the question
    2. Path traversal - Find paths between anchors using BFS/DFS
    3. Ranking/pruning - Score paths by relevance and length
    4. Serialization - Convert subgraph to readable format for LLM
    """
    
    def __init__(self):
        super().__init__(
            name="Path Traversal",
            description="Finds paths and connections between entities mentioned in questions"
        )
        
        self.schema_analyzer = SchemaAnalyzer(neo4j_client)
        self.query_executor = QueryExecutor(neo4j_client)
        self._schema_cache = None
        
        # Common Berlin location patterns for anchor detection
        self.location_patterns = [
            r'\b([A-ZÄÖÜ][a-zäöü]+(?:\s+[A-ZÄÖÜ][a-zäöü]+)*(?:platz|straße|str\.|bahnhof|station|bf\.?))\b',
            r'\b([A-ZÄÖÜ][a-zäöü]+(?:\s+[A-ZÄÖÜ][a-zäöü]+)*(?:berg|burg|dorf|felde|hagen|hof|ow|stedt|thal|wald|werder))\b',
            r'\b(U\d+|S\d+|Bus\s+\d+|Linie\s+\d+)\b'
        ]
        
        # Relationship types for traversal with weights
        self.traversal_relationships = {
            'SERVES': 1.0,           # Line serves station
            'CONNECTS_TO': 1.2,      # Direct station connections
            'LOCATED_IN': 1.5,       # Station in administrative area
            'PART_OF': 2.0,          # Administrative hierarchy
            'SERVES_CORE': 1.1,      # Core line-station relationships
            'HAS_SNAPSHOT': 2.5      # Temporal relationships (lower priority)
        }
    
    async def process_query(
        self,
        question: str,
        llm_provider: str = "mistral",
        max_hops: int = 3,
        max_paths: int = 10,
        year_filter: Optional[int] = None,
        **kwargs
    ) -> PipelineResult:
        """Process a question using path traversal"""
        
        start_time = time.time()
        
        try:
            # Step 1: Anchor detection
            anchor_nodes = await self._detect_anchors(question, year_filter)
            
            if len(anchor_nodes) == 0:
                return PipelineResult(
                    answer="I couldn't identify any specific locations or entities in your question. Could you mention specific stations, areas, or transit lines?",
                    approach=self.name,
                    llm_provider=llm_provider,
                    execution_time_seconds=time.time() - start_time,
                    success=False,
                    error_message="No anchor nodes detected",
                    error_stage="anchor_detection"
                )
            
            # Step 2: Path traversal
            traversal_result = await self._traverse_paths(
                anchor_nodes, max_hops, max_paths, year_filter
            )
            
            # Step 3: Ranking and pruning
            ranked_paths = self._rank_and_prune_paths(
                traversal_result.paths, max_paths
            )
            
            # Step 4: Serialization
            context = self._serialize_subgraph(
                anchor_nodes, ranked_paths, traversal_result.subgraph_edges
            )
            
            # Step 5: Generate answer using LLM
            answer = await self._generate_answer(
                question, context, llm_provider, traversal_result.traversal_stats
            )
            
            execution_time = time.time() - start_time
            
            return PipelineResult(
                answer=answer["answer"],
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=True,
                llm_response=answer.get("llm_response"),
                retrieved_context=[context],
                metadata={
                    "anchor_nodes": [node["name"] for node in anchor_nodes],
                    "path_count": len(ranked_paths),
                    "traversal_stats": traversal_result.traversal_stats,
                    "year_filter": year_filter
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return PipelineResult(
                answer=f"I encountered an error while analyzing the connections: {str(e)}",
                approach=self.name,
                llm_provider=llm_provider,
                execution_time_seconds=execution_time,
                success=False,
                error_message=str(e),
                error_stage="path_traversal"
            )
    
    async def _detect_anchors(self, question: str, year_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """Detect anchor nodes mentioned in the question"""
        
        # Extract potential location names using regex patterns
        potential_anchors = set()
        
        for pattern in self.location_patterns:
            matches = re.findall(pattern, question, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    potential_anchors.update(match)
                else:
                    potential_anchors.add(match)
        
        # Also look for simple capitalized words that might be locations
        words = re.findall(r'\b[A-ZÄÖÜ][a-zäöü]+\b', question)
        potential_anchors.update(words)
        
        # Clean up anchors
        cleaned_anchors = []
        for anchor in potential_anchors:
            anchor = anchor.strip()
            if len(anchor) > 2 and anchor not in ['Von', 'Nach', 'Bis', 'Und', 'Der', 'Die', 'Das']:
                cleaned_anchors.append(anchor)
        
        if not cleaned_anchors:
            return []
        
        # Search for these entities in the database
        year_clause = ""
        if year_filter:
            year_clause = f"AND EXISTS((s)-[:IN_YEAR]->(y:Year {{year: {year_filter}}}))"
        
        search_query = f"""
        WITH {json.dumps(cleaned_anchors)} AS anchor_names
        UNWIND anchor_names AS anchor_name
        
        // Search in stations
        OPTIONAL MATCH (s:Station)
        WHERE s.name CONTAINS anchor_name {year_clause}
        
        // Search in core stations
        OPTIONAL MATCH (cs:CoreStation)
        WHERE cs.name CONTAINS anchor_name
        
        // Search in lines
        OPTIONAL MATCH (l:Line)
        WHERE l.name CONTAINS anchor_name OR l.line_id CONTAINS anchor_name
        {f"AND EXISTS((l)-[:IN_YEAR]->(y:Year {{year: {year_filter}}}))" if year_filter else ""}
        
        // Search in administrative areas
        OPTIONAL MATCH (o:CoreOrtsteil)
        WHERE o.name CONTAINS anchor_name
        
        RETURN 
            anchor_name,
            s.name AS station_name, s.stop_id AS station_id, s.type AS station_type,
            cs.name AS core_station_name, cs.core_id AS core_station_id,
            l.name AS line_name, l.line_id AS line_id, l.type AS line_type,
            o.name AS ortsteil_name, o.core_id AS ortsteil_id,
            'station' AS entity_type
        ORDER BY anchor_name
        """
        
        query_result = await self.query_executor.execute_query_safely(search_query)
        
        if not query_result.success:
            return []
        
        # Process results to create anchor nodes
        anchor_nodes = []
        seen_entities = set()
        
        for result in query_result.records:
            if result.get("station_name") and result["station_name"] not in seen_entities:
                anchor_nodes.append({
                    "name": result["station_name"],
                    "id": result["station_id"],
                    "type": "station",
                    "subtype": result.get("station_type", "unknown"),
                    "original_mention": result["anchor_name"]
                })
                seen_entities.add(result["station_name"])
            
            elif result.get("core_station_name") and result["core_station_name"] not in seen_entities:
                anchor_nodes.append({
                    "name": result["core_station_name"],
                    "id": result["core_station_id"],
                    "type": "core_station",
                    "original_mention": result["anchor_name"]
                })
                seen_entities.add(result["core_station_name"])
            
            elif result.get("line_name") and result["line_name"] not in seen_entities:
                anchor_nodes.append({
                    "name": result["line_name"],
                    "id": result["line_id"],
                    "type": "line",
                    "subtype": result.get("line_type", "unknown"),
                    "original_mention": result["anchor_name"]
                })
                seen_entities.add(result["line_name"])
            
            elif result.get("ortsteil_name") and result["ortsteil_name"] not in seen_entities:
                anchor_nodes.append({
                    "name": result["ortsteil_name"],
                    "id": result["ortsteil_id"],
                    "type": "ortsteil",
                    "original_mention": result["anchor_name"]
                })
                seen_entities.add(result["ortsteil_name"])
        
        return anchor_nodes[:10]  # Limit to prevent explosion
    
    async def _traverse_paths(
        self,
        anchor_nodes: List[Dict[str, Any]],
        max_hops: int,
        max_paths: int,
        year_filter: Optional[int] = None
    ) -> PathTraversalResult:
        """Find paths between anchor nodes"""
        
        if len(anchor_nodes) < 2:
            # Single anchor - find neighborhood
            return await self._find_neighborhood(anchor_nodes[0], max_hops, year_filter)
        
        # Multiple anchors - find paths between them
        paths = []
        subgraph_edges = []
        stats = {"total_paths": 0, "unique_nodes": set(), "relationship_types": {}}
        
        # Find paths between all pairs of anchors
        for i in range(len(anchor_nodes)):
            for j in range(i + 1, len(anchor_nodes)):
                anchor_a = anchor_nodes[i]
                anchor_b = anchor_nodes[j]
                
                pair_paths = await self._find_paths_between_anchors(
                    anchor_a, anchor_b, max_hops, year_filter
                )
                
                paths.extend(pair_paths)
                
                # Collect edges from paths
                for path in pair_paths:
                    for edge in path.get("edges", []):
                        subgraph_edges.append(edge)
                        stats["unique_nodes"].add(edge["start_node"])
                        stats["unique_nodes"].add(edge["end_node"])
                        rel_type = edge["type"]  # Use "type" instead of "relationship_type"
                        stats["relationship_types"][rel_type] = stats["relationship_types"].get(rel_type, 0) + 1
        
        stats["total_paths"] = len(paths)
        stats["unique_nodes"] = len(stats["unique_nodes"])
        
        return PathTraversalResult(
            anchor_nodes=anchor_nodes,
            paths=paths,
            subgraph_edges=subgraph_edges,
            traversal_stats=stats
        )
    
    async def _find_paths_between_anchors(
        self,
        anchor_a: Dict[str, Any],
        anchor_b: Dict[str, Any],
        max_hops: int,
        year_filter: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Find paths between two specific anchors"""
        
        # Build match clause based on anchor types
        match_a = self._build_anchor_match_clause(anchor_a, "a")
        match_b = self._build_anchor_match_clause(anchor_b, "b")
        
        year_clause = ""
        if year_filter:
            year_clause = f"""
            AND ALL(node IN nodes(path) WHERE 
                NOT EXISTS(node.year) OR node.year = {year_filter}
            )
            """
        
        # Find shortest paths
        path_query = f"""
        {match_a}
        {match_b}
        
        MATCH path = shortestPath((a)-[*1..{max_hops}]-(b))
        WHERE a <> b {year_clause}
        
        WITH path, length(path) as path_length
        ORDER BY path_length
        LIMIT 10
        
        RETURN 
            path,
            path_length,
            [node IN nodes(path) | {{
                name: COALESCE(node.name, node.core_id, node.line_id, node.stop_id, 'unknown'),
                type: labels(node)[0],
                id: COALESCE(node.core_id, node.stop_id, node.line_id, id(node))
            }}] as nodes,
            [rel IN relationships(path) | {{
                type: type(rel),
                start_node: COALESCE(startNode(rel).name, startNode(rel).core_id, startNode(rel).stop_id, 'unknown'),
                end_node: COALESCE(endNode(rel).name, endNode(rel).core_id, endNode(rel).stop_id, 'unknown'),
                properties: properties(rel)
            }}] as edges
        """
        
        query_result = await self.query_executor.execute_query_safely(path_query)
        
        if not query_result.success:
            return []
        
        results = query_result.records
        
        paths = []
        for result in results:
            paths.append({
                "start_anchor": anchor_a["name"],
                "end_anchor": anchor_b["name"],
                "length": result["path_length"],
                "nodes": result["nodes"],
                "edges": result["edges"],
                "score": self._calculate_path_score(result["edges"], result["path_length"])
            })
        
        return paths
    
    async def _find_neighborhood(
        self,
        anchor: Dict[str, Any],
        max_hops: int,
        year_filter: Optional[int] = None
    ) -> PathTraversalResult:
        """Find neighborhood around a single anchor"""
        
        match_clause = self._build_anchor_match_clause(anchor, "center")
        
        year_clause = ""
        if year_filter:
            year_clause = f"AND n.year = {year_filter} OR NOT EXISTS(n.year)"
        
        neighborhood_query = f"""
        {match_clause}
        
        MATCH (center)-[r*1..{max_hops}]-(n)
        WHERE center <> n {year_clause}
        
        WITH center, n, r, length(r) as distance
        ORDER BY distance
        LIMIT 50
        
        RETURN 
            center.name as center_name,
            n.name as neighbor_name,
            labels(n)[0] as neighbor_type,
            distance,
            [rel IN r | type(rel)] as relationship_path
        """
        
        query_result = await self.query_executor.execute_query_safely(neighborhood_query)
        
        if not query_result.success:
            return PathTraversalResult(
                anchor_nodes=[anchor],
                paths=[],
                subgraph_edges=[],
                traversal_stats={"error": query_result.error_message}
            )
        
        results = query_result.records
        
        # Build neighborhood paths
        paths = []
        subgraph_edges = []
        stats = {"total_paths": len(results), "unique_nodes": set(), "relationship_types": {}}
        
        for result in results:
            path_info = {
                "center_node": result["center_name"],
                "neighbor_node": result["neighbor_name"],
                "neighbor_type": result["neighbor_type"],
                "distance": result["distance"],
                "relationship_path": result["relationship_path"],
                "score": 1.0 / result["distance"]  # Closer nodes score higher
            }
            paths.append(path_info)
            
            stats["unique_nodes"].add(result["center_name"])
            stats["unique_nodes"].add(result["neighbor_name"])
            
            for rel_type in result["relationship_path"]:
                stats["relationship_types"][rel_type] = stats["relationship_types"].get(rel_type, 0) + 1
        
        stats["unique_nodes"] = len(stats["unique_nodes"])
        
        return PathTraversalResult(
            anchor_nodes=[anchor],
            paths=paths,
            subgraph_edges=subgraph_edges,
            traversal_stats=stats
        )
    
    def _build_anchor_match_clause(self, anchor: Dict[str, Any], var_name: str) -> str:
        """Build Cypher MATCH clause for an anchor node"""
        
        anchor_type = anchor["type"]
        anchor_name = anchor["name"]
        anchor_id = anchor.get("id")
        
        if anchor_type == "station":
            return f'MATCH ({var_name}:Station) WHERE {var_name}.name = "{anchor_name}"'
        elif anchor_type == "core_station":
            return f'MATCH ({var_name}:CoreStation) WHERE {var_name}.name = "{anchor_name}"'
        elif anchor_type == "line":
            return f'MATCH ({var_name}:Line) WHERE {var_name}.name = "{anchor_name}" OR {var_name}.line_id = "{anchor_id}"'
        elif anchor_type == "ortsteil":
            return f'MATCH ({var_name}:CoreOrtsteil) WHERE {var_name}.name = "{anchor_name}"'
        else:
            # Generic match
            return f'MATCH ({var_name}) WHERE {var_name}.name = "{anchor_name}"'
    
    def _calculate_path_score(self, edges: List[Dict[str, Any]], path_length: int) -> float:
        """Calculate relevance score for a path"""
        
        score = 1.0
        
        # Penalize longer paths
        score *= (1.0 / (path_length + 1))
        
        # Boost score based on relationship types
        for edge in edges:
            rel_type = edge["type"]
            weight = self.traversal_relationships.get(rel_type, 3.0)
            score *= (1.0 / weight)
        
        return score
    
    def _rank_and_prune_paths(self, paths: List[Dict[str, Any]], max_paths: int) -> List[Dict[str, Any]]:
        """Rank paths by score and prune to max_paths"""
        
        # Sort by score (descending)
        sorted_paths = sorted(paths, key=lambda p: p.get("score", 0), reverse=True)
        
        # Return top paths
        return sorted_paths[:max_paths]
    
    def _serialize_subgraph(
        self,
        anchor_nodes: List[Dict[str, Any]],
        paths: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> str:
        """Convert subgraph to readable format for LLM"""
        
        context_parts = []
        
        # Anchor nodes
        context_parts.append("=== ANCHOR ENTITIES ===")
        for anchor in anchor_nodes:
            context_parts.append(f"• {anchor['name']} ({anchor['type']})")
        
        # Paths
        if len(anchor_nodes) > 1:
            context_parts.append("\n=== PATHS BETWEEN ENTITIES ===")
            for i, path in enumerate(paths[:5], 1):  # Show top 5 paths
                if "start_anchor" in path and "end_anchor" in path:
                    context_parts.append(f"\nPath {i}: {path['start_anchor']} → {path['end_anchor']}")
                    context_parts.append(f"  Length: {path['length']} hops")
                    context_parts.append(f"  Score: {path['score']:.3f}")
                    
                    # Show nodes in path
                    if "nodes" in path:
                        node_names = [node["name"] for node in path["nodes"]]
                        context_parts.append(f"  Route: {' → '.join(node_names)}")
                    
                    # Show relationships
                    if "edges" in path:
                        rel_types = [edge["type"] for edge in path["edges"]]
                        context_parts.append(f"  Connections: {' → '.join(rel_types)}")
        
        # Neighborhood info for single anchor
        elif len(anchor_nodes) == 1:
            context_parts.append(f"\n=== NEIGHBORHOOD AROUND {anchor_nodes[0]['name']} ===")
            
            # Group by relationship type
            by_rel_type = {}
            for path in paths[:10]:  # Show top 10 neighbors
                if "relationship_path" in path:
                    rel_type = path["relationship_path"][0] if path["relationship_path"] else "UNKNOWN"
                    if rel_type not in by_rel_type:
                        by_rel_type[rel_type] = []
                    by_rel_type[rel_type].append(path)
            
            for rel_type, rel_paths in by_rel_type.items():
                context_parts.append(f"\n{rel_type} connections:")
                for path in rel_paths[:5]:  # Top 5 per type
                    context_parts.append(f"  • {path['neighbor_node']} ({path['neighbor_type']}) - distance: {path['distance']}")
        
        # Statistics
        context_parts.append("\n=== TRAVERSAL STATISTICS ===")
        if paths:
            stats = paths[0] if "traversal_stats" in paths[0] else {}
            context_parts.append(f"Total paths found: {len(paths)}")
            context_parts.append(f"Unique nodes: {stats.get('unique_nodes', 'N/A')}")
            context_parts.append(f"Relationship types: {list(stats.get('relationship_types', {}).keys())}")
        
        return "\n".join(context_parts)
    
    async def _generate_answer(
        self,
        question: str,
        context: str,
        llm_provider: str,
        stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate final answer using LLM"""
        
        system_prompt = """You are an expert on Berlin's historical transportation network (1946-1989). 
        You have been provided with path traversal results showing connections between entities mentioned in the user's question.
        
        Your task is to:
        1. Analyze the path information to understand connections between entities
        2. Explain how the entities are connected through the transit network
        3. Provide historical context where relevant
        4. Be specific about routes, connections, and relationships
        5. If multiple paths exist, explain the different connection options
        
        Focus on being helpful and informative while staying grounded in the provided path data."""
        
        user_prompt = f"""
        QUESTION: {question}
        
        PATH TRAVERSAL RESULTS:
        {context}
        
        Based on the path traversal results above, please answer the user's question about connections and relationships in Berlin's historical transit network. 
        
        Explain:
        - How the mentioned entities are connected
        - What paths exist between them
        - The types of connections (transport lines, administrative boundaries, etc.)
        - Any interesting patterns or insights from the traversal
        
        If no clear paths were found, explain what entities were identified and suggest alternative approaches.
        """
        
        llm_client = create_llm_client(llm_provider)
        
        if not llm_client:
            return {
                "answer": f"LLM provider {llm_provider} not available",
                "llm_response": None
            }
        
        llm_response = await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=500
        )
        
        return {
            "answer": llm_response.text,
            "llm_response": llm_response
        }
    
    def get_required_capabilities(self) -> List[str]:
        """Return required capabilities for this pipeline"""
        return [
            "graph_traversal",
            "entity_recognition",
            "path_finding",
            "subgraph_extraction"
        ] 