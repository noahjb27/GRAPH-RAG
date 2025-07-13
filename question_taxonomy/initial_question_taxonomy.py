"""
Extended Berlin Transport Graph-RAG Question Taxonomy
Comprehensive evaluation covering all pipeline types

Extensions:
- Path traversal questions for PathTraversalPipeline
- Semantic similarity questions for VectorPipeline  
- Natural language variants for ChatbotPipeline routing
- General knowledge questions for NoRAGPipeline
- Routing challenge questions for pipeline selection
- Failure case questions for robustness testing
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field

@dataclass
class EvaluationQuestion:
    question_id: str
    question_text: str
    category: str
    sub_category: str
    required_capabilities: List[str]
    ground_truth: Any
    ground_truth_type: str
    cypher_query: str
    difficulty: int
    historical_context: str
    evaluation_method: str
    optimal_pipeline: str = "direct_cypher"  # New field
    acceptable_pipelines: List[str] = field(default_factory=list)  # New field
    notes: str = ""

    def __post_init__(self):
        if self.acceptable_pipelines is None:
            self.acceptable_pipelines = []

class ExtendedBerlinTransportQuestionTaxonomy:
    """Extended question taxonomy covering all pipeline types"""
    
    def create_factual_questions(self) -> List[EvaluationQuestion]:
        """Factual queries - verified entity names and years"""
        
        return [
            EvaluationQuestion(
                question_id="fact_001",
                question_text="What was the frequency of tram Line 1 in 1964?",
                category="factual",
                sub_category="line_property_lookup",
                required_capabilities=["property_access", "filtering"],
                ground_truth=None,
                ground_truth_type="exact",
                cypher_query="""
                MATCH (l:Line {name: '1', type: 'tram'})-[:IN_YEAR]->(y:Year {year: 1964})
                RETURN l.frequency as frequency
                """,
                difficulty=1,
                historical_context="Tram operations before East-West division crystallized",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["multi_query_cypher"],
                notes="Line 1 existed as tram in 1964, later became U-Bahn in West"
            ),
            
            EvaluationQuestion(
                question_id="fact_002",
                question_text="What transport types were available at Alexanderplatz in 1965?",
                category="factual",
                sub_category="station_property_lookup",
                required_capabilities=["entity_lookup", "property_access", "aggregation"],
                ground_truth=None,
                ground_truth_type="list",
                cypher_query="""
                MATCH (s:Station)-[:IN_YEAR]->(y:Year {year: 1965})
                WHERE s.name = 'Alexanderplatz'
                RETURN DISTINCT s.type as transport_type
                ORDER BY s.type
                """,
                difficulty=1,
                historical_context="Major East Berlin hub with multiple transport modes",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["vector", "path_traversal"]
            ),
            
            EvaluationQuestion(
                question_id="fact_003",
                question_text="How many autobus stations existed in West Berlin in 1967?",
                category="factual",
                sub_category="aggregation_count",
                required_capabilities=["filtering", "aggregation", "counting"],
                ground_truth=None,
                ground_truth_type="exact",
                cypher_query="""
                MATCH (s:Station {type: 'autobus', east_west: 'west'})-[:IN_YEAR]->(y:Year {year: 1967})
                RETURN count(s) as autobus_stations
                """,
                difficulty=2,
                historical_context="West Berlin bus network expansion in late 1960s",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["multi_query_cypher"]
            ),
            
            EvaluationQuestion(
                question_id="fact_004",
                question_text="What was the standardized capacity of S-Bahn lines in 1971?",
                category="factual",
                sub_category="capacity_standard",
                required_capabilities=["filtering", "property_access"],
                ground_truth=None,
                ground_truth_type="exact",
                cypher_query="""
                MATCH (l:Line {type: 's-bahn'})-[:IN_YEAR]->(y:Year {year: 1971})
                RETURN DISTINCT l.capacity as sbahn_capacity
                """,
                difficulty=1,
                historical_context="Standardized capacity values for historical analysis",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["vector"]
            ),
            
            EvaluationQuestion(
                question_id="fact_005",
                question_text="Which Ortsteile had ferry stations in 1971?",
                category="factual", 
                sub_category="geographic_listing",
                required_capabilities=["filtering", "relationship_traversal", "distinct_values"],
                ground_truth=None,
                ground_truth_type="list",
                cypher_query="""
                MATCH (s:Station {type: 'ferry'})-[:IN_YEAR]->(y:Year {year: 1971})
                MATCH (s)-[:LOCATED_IN]->(ho:HistoricalOrtsteil)
                MATCH (ho)-[:IN_YEAR]->(y)
                RETURN DISTINCT ho.name as ortsteil
                ORDER BY ho.name
                """,
                difficulty=2,
                historical_context="Ferry expansion in East Berlin by 1971",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["multi_query_cypher", "vector"]
            )
        ]
    
    def create_path_traversal_questions(self) -> List[EvaluationQuestion]:
        """Path finding and connection questions for PathTraversalPipeline"""
        
        return [
            EvaluationQuestion(
                question_id="path_001",
                question_text="How could someone travel from Kreuzberg to Mitte in 1967?",
                category="path_traversal",
                sub_category="route_finding",
                required_capabilities=["anchor_detection", "path_finding", "route_analysis"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (start:HistoricalOrtsteil {name: 'Kreuzberg'})-[:IN_YEAR]->(y:Year {year: 1967})
                MATCH (end:HistoricalOrtsteil {name: 'Mitte'})-[:IN_YEAR]->(y)
                MATCH (start)<-[:LOCATED_IN]-(s1:Station)-[:IN_YEAR]->(y)
                MATCH (end)<-[:LOCATED_IN]-(s2:Station)-[:IN_YEAR]->(y)
                MATCH path = shortestPath((s1)-[*1..4]-(s2))
                RETURN path LIMIT 5
                """,
                difficulty=4,
                historical_context="Cross-sector travel in divided Berlin",
                evaluation_method="consistency",
                optimal_pipeline="path_traversal",
                acceptable_pipelines=["vector", "multi_query_cypher"],
                notes="Tests district-to-district routing with political context"
            ),
            
            EvaluationQuestion(
                question_id="path_002", 
                question_text="What transport connections linked Alexanderplatz to Zoologischer Garten in 1965?",
                category="path_traversal",
                sub_category="station_connections",
                required_capabilities=["anchor_detection", "connection_analysis", "multi_modal_routing"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (alex:Station {name: 'Alexanderplatz'})-[:IN_YEAR]->(y:Year {year: 1965})
                MATCH (zoo:Station {name: 'Zoologischer Garten'})-[:IN_YEAR]->(y)
                MATCH path = shortestPath((alex)-[*1..5]-(zoo))
                RETURN path LIMIT 3
                """,
                difficulty=4,
                historical_context="Key East-West connection before full division",
                evaluation_method="consistency",
                optimal_pipeline="path_traversal",
                acceptable_pipelines=["multi_query_cypher"],
                notes="Tests major hub connections across political boundary"
            ),
            
            EvaluationQuestion(
                question_id="path_003",
                question_text="Which stations served as transfer points between different transport modes in 1967?",
                category="path_traversal", 
                sub_category="transfer_analysis",
                required_capabilities=["multi_modal_analysis", "hub_detection", "network_centrality"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (s:Station)-[:IN_YEAR]->(y:Year {year: 1967})
                MATCH (s)<-[:SERVES]-(l:Line)-[:IN_YEAR]->(y)
                WITH s, count(DISTINCT l.type) as transport_types, collect(DISTINCT l.type) as types
                WHERE transport_types > 1
                RETURN s.name as station, transport_types, types
                ORDER BY transport_types DESC
                """,
                difficulty=3,
                historical_context="Intermodal connectivity in mature network",
                evaluation_method="automatic",
                optimal_pipeline="path_traversal",
                acceptable_pipelines=["multi_query_cypher", "vector"],
                notes="Identifies multi-modal hubs"
            ),
            
            EvaluationQuestion(
                question_id="path_004",
                question_text="How were East and West Berlin transport networks connected in 1964?",
                category="path_traversal",
                sub_category="cross_boundary_analysis", 
                required_capabilities=["political_boundary_analysis", "network_connectivity", "cross_sector_routing"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (east_station:Station {east_west: 'east'})-[:IN_YEAR]->(y:Year {year: 1964})
                MATCH (west_station:Station {east_west: 'west'})-[:IN_YEAR]->(y)
                MATCH path = shortestPath((east_station)-[*1..3]-(west_station))
                RETURN path LIMIT 10
                """,
                difficulty=5,
                historical_context="Transport connections before full division",
                evaluation_method="expert",
                optimal_pipeline="path_traversal",
                acceptable_pipelines=["multi_query_cypher"],
                notes="Critical for understanding division impact"
            ),
            
            EvaluationQuestion(
                question_id="path_005",
                question_text="What was the shortest route between U-Bahn stations in West Berlin in 1971?",
                category="path_traversal",
                sub_category="intra_modal_routing",
                required_capabilities=["modal_filtering", "shortest_path", "same_system_routing"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (s1:Station {type: 'u-bahn', east_west: 'west'})-[:IN_YEAR]->(y:Year {year: 1971})
                MATCH (s2:Station {type: 'u-bahn', east_west: 'west'})-[:IN_YEAR]->(y)
                WHERE s1 <> s2
                MATCH path = shortestPath((s1)-[:CONNECTS_TO*1..5]-(s2))
                RETURN path ORDER BY length(path) LIMIT 5
                """,
                difficulty=3,
                historical_context="West Berlin U-Bahn network connectivity",
                evaluation_method="automatic",
                optimal_pipeline="path_traversal",
                acceptable_pipelines=["direct_cypher"],
                notes="Tests single-mode routing optimization"
            )
        ]
    
    def create_vector_similarity_questions(self) -> List[EvaluationQuestion]:
        """Semantic similarity questions for VectorPipeline"""
        
        return [
            EvaluationQuestion(
                question_id="vector_001",
                question_text="What stations were functionally similar to Alexanderplatz in 1967?",
                category="vector_similarity",
                sub_category="functional_similarity",
                required_capabilities=["semantic_similarity", "structural_similarity", "functional_analysis"],
                ground_truth=None,
                ground_truth_type="similarity_ranking",
                cypher_query="""
                MATCH (alex:Station {name: 'Alexanderplatz'})-[:IN_YEAR]->(y:Year {year: 1967})
                MATCH (alex)<-[:SERVES]-(l:Line)-[:IN_YEAR]->(y)
                WITH alex, count(l) as alex_lines, collect(DISTINCT l.type) as alex_types
                MATCH (other:Station)-[:IN_YEAR]->(y)
                WHERE other <> alex
                MATCH (other)<-[:SERVES]-(ol:Line)-[:IN_YEAR]->(y)
                WITH other, count(ol) as other_lines, collect(DISTINCT ol.type) as other_types, alex_lines, alex_types
                WHERE abs(other_lines - alex_lines) <= 2
                RETURN other.name as similar_station, other_lines, other_types
                ORDER BY abs(other_lines - alex_lines), other.name
                """,
                difficulty=4,
                historical_context="Major transport hubs with similar connectivity",
                evaluation_method="similarity_analysis",
                optimal_pipeline="vector",
                acceptable_pipelines=["multi_query_cypher"],
                notes="Tests topological similarity detection"
            ),
            
            EvaluationQuestion(
                question_id="vector_002",
                question_text="Which neighborhoods had transport patterns similar to Kreuzberg in 1965?",
                category="vector_similarity",
                sub_category="neighborhood_similarity",
                required_capabilities=["area_analysis", "transport_pattern_matching", "administrative_similarity"],
                ground_truth=None,
                ground_truth_type="similarity_ranking",
                cypher_query="""
                MATCH (kreuz:HistoricalOrtsteil {name: 'Kreuzberg'})-[:IN_YEAR]->(y:Year {year: 1965})
                MATCH (kreuz)<-[:LOCATED_IN]-(s:Station)-[:IN_YEAR]->(y)
                WITH kreuz, count(s) as kreuz_stations, collect(DISTINCT s.type) as kreuz_types
                MATCH (other:HistoricalOrtsteil)-[:IN_YEAR]->(y)
                WHERE other <> kreuz
                MATCH (other)<-[:LOCATED_IN]-(os:Station)-[:IN_YEAR]->(y)
                WITH other, count(os) as other_stations, collect(DISTINCT os.type) as other_types, kreuz_stations, kreuz_types
                WHERE abs(other_stations - kreuz_stations) <= 3
                RETURN other.name as similar_area, other_stations, other_types
                ORDER BY abs(other_stations - kreuz_stations)
                """,
                difficulty=4,
                historical_context="District-level transport accessibility patterns",
                evaluation_method="similarity_analysis",
                optimal_pipeline="vector",
                acceptable_pipelines=["multi_query_cypher"],
                notes="Tests neighborhood-level pattern matching"
            ),
            
            EvaluationQuestion(
                question_id="vector_003",
                question_text="Find areas with transport accessibility comparable to central Berlin in 1967",
                category="vector_similarity",
                sub_category="accessibility_similarity",
                required_capabilities=["accessibility_analysis", "centrality_comparison", "transport_density"],
                ground_truth=None,
                ground_truth_type="similarity_ranking",
                cypher_query="""
                // Find central areas (Mitte, areas with high station density)
                MATCH (ho:HistoricalOrtsteil)-[:IN_YEAR]->(y:Year {year: 1967})
                MATCH (ho)<-[:LOCATED_IN]-(s:Station)-[:IN_YEAR]->(y)
                WITH ho, count(s) as station_count, count(DISTINCT s.type) as transport_diversity
                WHERE station_count >= 3 AND transport_diversity >= 2
                RETURN ho.name as accessible_area, station_count, transport_diversity
                ORDER BY transport_diversity DESC, station_count DESC
                """,
                difficulty=3,
                historical_context="Transport accessibility distribution across Berlin",
                evaluation_method="consistency",
                optimal_pipeline="vector",
                acceptable_pipelines=["multi_query_cypher"],
                notes="Tests conceptual similarity (accessibility)"
            ),
            
            EvaluationQuestion(
                question_id="vector_004",
                question_text="What transport hubs had roles similar to Zoologischer Garten in the network?",
                category="vector_similarity",
                sub_category="hub_role_similarity",
                required_capabilities=["hub_analysis", "role_similarity", "network_importance"],
                ground_truth=None,
                ground_truth_type="similarity_ranking",
                cypher_query="""
                MATCH (zoo:Station {name: 'Zoologischer Garten'})-[:IN_YEAR]->(y:Year {year: 1967})
                MATCH (zoo)<-[:SERVES]-(l:Line)-[:IN_YEAR]->(y)
                WITH zoo, count(l) as zoo_lines, collect(DISTINCT l.type) as zoo_types, size(collect(DISTINCT l.type)) as zoo_diversity
                MATCH (other:Station)-[:IN_YEAR]->(y)
                WHERE other <> zoo
                MATCH (other)<-[:SERVES]-(ol:Line)-[:IN_YEAR]->(y)
                WITH other, count(ol) as other_lines, collect(DISTINCT ol.type) as other_types, size(collect(DISTINCT ol.type)) as other_diversity, zoo_lines, zoo_diversity
                WHERE other_lines >= 3 AND other_diversity >= 2
                RETURN other.name as similar_hub, other_lines, other_types, other_diversity
                ORDER BY abs(other_diversity - zoo_diversity), abs(other_lines - zoo_lines)
                """,
                difficulty=4,
                historical_context="Major West Berlin transport interchange",
                evaluation_method="similarity_analysis",
                optimal_pipeline="vector",
                acceptable_pipelines=["multi_query_cypher"],
                notes="Tests hub role and importance similarity"
            ),
            
            EvaluationQuestion(
                question_id="vector_005",
                question_text="Which districts had transport development patterns like those in divided cities?",
                category="vector_similarity",
                sub_category="pattern_recognition",
                required_capabilities=["pattern_analysis", "conceptual_similarity", "historical_pattern_matching"],
                ground_truth=None,
                ground_truth_type="subjective",
                cypher_query="""
                // Look at transport diversity and political context
                MATCH (ho:HistoricalOrtsteil)-[:IN_YEAR]->(y:Year {year: 1967})
                MATCH (ho)<-[:LOCATED_IN]-(s:Station)-[:IN_YEAR]->(y)
                WHERE s.east_west IN ['east', 'west']
                WITH ho, s.east_west as political_side, count(s) as stations, count(DISTINCT s.type) as diversity
                RETURN ho.name as area, political_side, stations, diversity
                ORDER BY political_side, diversity DESC
                """,
                difficulty=5,
                historical_context="Transport patterns under political division",
                evaluation_method="expert",
                optimal_pipeline="vector",
                acceptable_pipelines=["no_rag"],
                notes="Tests abstract pattern recognition"
            )
        ]
    
    def create_natural_language_questions(self) -> List[EvaluationQuestion]:
        """Natural language variants for ChatBot routing testing"""
        
        return [
            EvaluationQuestion(
                question_id="natural_001",
                question_text="I lived in Mitte and worked in Kreuzberg - how was my commute in 1967?",
                category="natural_language",
                sub_category="personal_scenario",
                required_capabilities=["natural_language_processing", "scenario_analysis", "route_planning"],
                ground_truth=None,
                ground_truth_type="narrative",
                cypher_query="""
                MATCH (mitte:HistoricalOrtsteil {name: 'Mitte'})-[:IN_YEAR]->(y:Year {year: 1967})
                MATCH (kreuz:HistoricalOrtsteil {name: 'Kreuzberg'})-[:IN_YEAR]->(y)
                MATCH (mitte)<-[:LOCATED_IN]-(s1:Station)-[:IN_YEAR]->(y)
                MATCH (kreuz)<-[:LOCATED_IN]-(s2:Station)-[:IN_YEAR]->(y)
                RETURN s1.name as mitte_stations, s2.name as kreuzberg_stations, s1.type, s2.type
                """,
                difficulty=4,
                historical_context="Daily life in divided Berlin",
                evaluation_method="narrative_quality",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["path_traversal", "vector"],
                notes="Tests natural language scenario understanding"
            ),
            
            EvaluationQuestion(
                question_id="natural_002",
                question_text="Getting around East Berlin in the late 60s - what were the options?",
                category="natural_language",
                sub_category="informal_inquiry",
                required_capabilities=["informal_language", "temporal_interpretation", "area_analysis"],
                ground_truth=None,
                ground_truth_type="narrative",
                cypher_query="""
                MATCH (s:Station {east_west: 'east'})-[:IN_YEAR]->(y:Year)
                WHERE y.year IN [1967, 1968, 1969]
                RETURN s.type as transport_option, count(s) as station_count
                ORDER BY station_count DESC
                """,
                difficulty=3,
                historical_context="East Berlin transport system late 1960s",
                evaluation_method="narrative_quality",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["vector", "multi_query_cypher"],
                notes="Tests informal temporal and spatial references"
            ),
            
            EvaluationQuestion(
                question_id="natural_003",
                question_text="Was it convenient to live without a car in 1960s Berlin?",
                category="natural_language",
                sub_category="lifestyle_question",
                required_capabilities=["lifestyle_analysis", "convenience_assessment", "historical_context"],
                ground_truth=None,
                ground_truth_type="subjective",
                cypher_query="""
                MATCH (s:Station)-[:IN_YEAR]->(y:Year)
                WHERE y.year >= 1965 AND y.year <= 1969
                RETURN y.year, count(s) as total_stations, count(DISTINCT s.type) as transport_diversity
                ORDER BY y.year
                """,
                difficulty=4,
                historical_context="Car ownership and public transport reliance",
                evaluation_method="narrative_quality",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["no_rag", "vector"],
                notes="Tests lifestyle and convenience reasoning"
            ),
            
            EvaluationQuestion(
                question_id="natural_004",
                question_text="My grandmother said Alexanderplatz was always busy - what transport was there?",
                category="natural_language",
                sub_category="anecdotal_inquiry",
                required_capabilities=["anecdotal_processing", "entity_recognition", "contextual_understanding"],
                ground_truth=None,
                ground_truth_type="narrative",
                cypher_query="""
                MATCH (s:Station {name: 'Alexanderplatz'})-[:IN_YEAR]->(y:Year)
                MATCH (s)<-[:SERVES]-(l:Line)-[:IN_YEAR]->(y)
                RETURN y.year, collect(DISTINCT s.type) as transport_types, count(l) as line_count
                ORDER BY y.year
                """,
                difficulty=2,
                historical_context="Alexanderplatz as major East Berlin hub",
                evaluation_method="narrative_quality",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["direct_cypher", "vector"],
                notes="Tests anecdotal and family story processing"
            ),
            
            EvaluationQuestion(
                question_id="natural_005",
                question_text="How did people get to work across the city back then?",
                category="natural_language",
                sub_category="general_lifestyle",
                required_capabilities=["general_inquiry", "lifestyle_analysis", "temporal_vagueness"],
                ground_truth=None,
                ground_truth_type="narrative",
                cypher_query="""
                MATCH (s:Station)-[:IN_YEAR]->(y:Year {year: 1967})
                MATCH (s)<-[:SERVES]-(l:Line)-[:IN_YEAR]->(y)
                RETURN s.type as transport_mode, avg(l.frequency) as avg_frequency, count(s) as stations
                ORDER BY stations DESC
                """,
                difficulty=3,
                historical_context="Commuting patterns in 1960s Berlin",
                evaluation_method="narrative_quality",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["vector", "no_rag"],
                notes="Tests vague temporal and general lifestyle questions"
            )
        ]
    
    def create_general_knowledge_questions(self) -> List[EvaluationQuestion]:
        """General knowledge questions for NoRAG baseline"""
        
        return [
            EvaluationQuestion(
                question_id="general_001",
                question_text="Why was Berlin divided after World War II?",
                category="general_knowledge",
                sub_category="historical_background",
                required_capabilities=["historical_knowledge", "political_context"],
                ground_truth="Berlin was divided among the four Allied powers (US, UK, France, Soviet Union) after WWII, leading to East-West division",
                ground_truth_type="factual",
                cypher_query="// No database query - general knowledge",
                difficulty=2,
                historical_context="Post-WWII occupation and Cold War origins",
                evaluation_method="factual_accuracy",
                optimal_pipeline="no_rag",
                acceptable_pipelines=[],
                notes="Tests pure parametric knowledge vs database knowledge"
            ),
            
            EvaluationQuestion(
                question_id="general_002",
                question_text="What was the purpose of the Berlin Wall?",
                category="general_knowledge",
                sub_category="political_history",
                required_capabilities=["political_knowledge", "historical_context"],
                ground_truth="To stop East Germans from fleeing to West Berlin and prevent brain drain",
                ground_truth_type="factual",
                cypher_query="// No database query - general knowledge",
                difficulty=2,
                historical_context="Cold War tensions and population movements",
                evaluation_method="factual_accuracy",
                optimal_pipeline="no_rag",
                acceptable_pipelines=[],
                notes="Essential context for transport network understanding"
            ),
            
            EvaluationQuestion(
                question_id="general_003",
                question_text="How does Berlin's public transport compare to other European cities?",
                category="general_knowledge",
                sub_category="comparative_analysis",
                required_capabilities=["comparative_analysis", "urban_transport_knowledge"],
                ground_truth=None,
                ground_truth_type="comparative",
                cypher_query="// No database query - general knowledge",
                difficulty=3,
                historical_context="Urban transport development patterns",
                evaluation_method="comparative_quality",
                optimal_pipeline="no_rag",
                acceptable_pipelines=[],
                notes="Tests knowledge beyond the specific database"
            ),
            
            EvaluationQuestion(
                question_id="general_004",
                question_text="What are typical public transport frequencies in major cities?",
                category="general_knowledge",
                sub_category="transport_standards",
                required_capabilities=["transport_knowledge", "urban_planning"],
                ground_truth=None,
                ground_truth_type="ranges",
                cypher_query="// No database query - general knowledge",
                difficulty=2,
                historical_context="Urban transport operational standards",
                evaluation_method="factual_accuracy",
                optimal_pipeline="no_rag",
                acceptable_pipelines=[],
                notes="Baseline transport knowledge question"
            ),
            
            EvaluationQuestion(
                question_id="general_005",
                question_text="How long does it typically take to build a metro system?",
                category="general_knowledge",
                sub_category="infrastructure_development",
                required_capabilities=["infrastructure_knowledge", "project_timelines"],
                ground_truth=None,
                ground_truth_type="ranges",
                cypher_query="// No database query - general knowledge",
                difficulty=3,
                historical_context="Urban infrastructure development",
                evaluation_method="factual_accuracy",
                optimal_pipeline="no_rag",
                acceptable_pipelines=[],
                notes="Tests infrastructure development knowledge"
            )
        ]
    
    def create_routing_challenge_questions(self) -> List[EvaluationQuestion]:
        """Ambiguous questions for testing pipeline routing logic"""
        
        return [
            EvaluationQuestion(
                question_id="routing_001",
                question_text="Tell me about Berlin transport in 1967",
                category="routing_challenge",
                sub_category="ambiguous_scope",
                required_capabilities=["scope_determination", "query_classification"],
                ground_truth=None,
                ground_truth_type="multi_approach",
                cypher_query="// Could use multiple approaches",
                difficulty=3,
                historical_context="Peak of divided Berlin transport development",
                evaluation_method="routing_analysis",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["vector", "multi_query_cypher", "no_rag"],
                notes="Tests routing for broad, open-ended questions"
            ),
            
            EvaluationQuestion(
                question_id="routing_002",
                question_text="How connected was the transport network?",
                category="routing_challenge",
                sub_category="connectivity_analysis",
                required_capabilities=["connectivity_analysis", "network_metrics"],
                ground_truth=None,
                ground_truth_type="multi_approach",
                cypher_query="// Could use path analysis or vector similarity",
                difficulty=4,
                historical_context="Network connectivity under political division",
                evaluation_method="routing_analysis",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["path_traversal", "vector", "multi_query_cypher"],
                notes="Tests routing between path analysis and similarity search"
            ),
            
            EvaluationQuestion(
                question_id="routing_003",
                question_text="What changed in Berlin transport after 1961?",
                category="routing_challenge",
                sub_category="temporal_change",
                required_capabilities=["temporal_analysis", "change_detection"],
                ground_truth=None,
                ground_truth_type="multi_approach",
                cypher_query="// Could use temporal queries or general knowledge",
                difficulty=4,
                historical_context="Transport changes after Berlin Wall construction",
                evaluation_method="routing_analysis",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["multi_query_cypher", "no_rag", "vector"],
                notes="Tests routing between database queries and general knowledge"
            ),
            
            EvaluationQuestion(
                question_id="routing_004",
                question_text="Transport efficiency in divided Berlin",
                category="routing_challenge",
                sub_category="efficiency_analysis",
                required_capabilities=["efficiency_analysis", "political_context"],
                ground_truth=None,
                ground_truth_type="multi_approach",
                cypher_query="// Multiple analytical approaches possible",
                difficulty=5,
                historical_context="Operational efficiency under political constraints",
                evaluation_method="routing_analysis",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["multi_query_cypher", "vector", "no_rag"],
                notes="Tests routing for analytical questions"
            ),
            
            EvaluationQuestion(
                question_id="routing_005",
                question_text="Getting around the city back then",
                category="routing_challenge",
                sub_category="lifestyle_vague",
                required_capabilities=["lifestyle_analysis", "temporal_vagueness"],
                ground_truth=None,
                ground_truth_type="multi_approach",
                cypher_query="// Very open-ended, multiple approaches valid",
                difficulty=3,
                historical_context="General mobility in historical Berlin",
                evaluation_method="routing_analysis",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["vector", "no_rag", "path_traversal"],
                notes="Tests routing for very vague, conversational questions"
            )
        ]
    
    def create_graphrag_global_questions(self) -> List[EvaluationQuestion]:
        """Global system-wide questions that benefit from GraphRAG hierarchical analysis"""
        
        return [
            EvaluationQuestion(
                question_id="graphrag_001",
                question_text="What were the major transport communities in Berlin and how did they evolve from 1946 to 1989?",
                category="global_analysis",
                sub_category="system_evolution",
                required_capabilities=["community_detection", "temporal_analysis", "system_overview"],
                ground_truth=None,
                ground_truth_type="descriptive",
                cypher_query="// Complex multi-dimensional analysis requiring GraphRAG",
                difficulty=4,
                historical_context="Requires understanding of entire transport system evolution through political division",
                evaluation_method="human_expert",
                optimal_pipeline="graphrag_transport",
                acceptable_pipelines=["chatbot"],
                notes="Global question requiring system-wide community analysis across time"
            ),
            
            EvaluationQuestion(
                question_id="graphrag_002", 
                question_text="How did the geographic distribution of transport services differ between East and West Berlin communities?",
                category="global_analysis",
                sub_category="political_geography",
                required_capabilities=["community_detection", "geographic_analysis", "political_context"],
                ground_truth=None,
                ground_truth_type="descriptive",
                cypher_query="// Requires geographic community analysis",
                difficulty=4,
                historical_context="Political division created distinct transport communities",
                evaluation_method="human_expert",
                optimal_pipeline="graphrag_transport",
                acceptable_pipelines=["hybrid"],
                notes="Benefits from geographic community detection and summarization"
            ),
            
            EvaluationQuestion(
                question_id="graphrag_003",
                question_text="What were the dominant transport service patterns across different temporal periods in Berlin?",
                category="global_analysis", 
                sub_category="temporal_patterns",
                required_capabilities=["community_detection", "temporal_analysis", "service_analysis"],
                ground_truth=None,
                ground_truth_type="descriptive",
                cypher_query="// Requires temporal community analysis",
                difficulty=4,
                historical_context="Transport service patterns changed with political and economic conditions",
                evaluation_method="human_expert",
                optimal_pipeline="graphrag_transport",
                acceptable_pipelines=["chatbot"],
                notes="Temporal community analysis reveals service evolution patterns"
            ),
            
            EvaluationQuestion(
                question_id="graphrag_004",
                question_text="Which transport communities had the highest operational complexity and integration?",
                category="global_analysis",
                sub_category="operational_complexity",
                required_capabilities=["community_detection", "operational_analysis", "integration_metrics"],
                ground_truth=None,
                ground_truth_type="descriptive", 
                cypher_query="// Requires operational community analysis",
                difficulty=4,
                historical_context="Some areas had multiple overlapping transport modes",
                evaluation_method="human_expert",
                optimal_pipeline="graphrag_transport",
                acceptable_pipelines=["graph_embedding"],
                notes="Operational community detection identifies complex integration patterns"
            ),
            
            EvaluationQuestion(
                question_id="graphrag_005",
                question_text="How did the service type distribution across Berlin communities reflect political priorities?",
                category="global_analysis",
                sub_category="political_priorities",
                required_capabilities=["community_detection", "service_analysis", "political_context"],
                ground_truth=None,
                ground_truth_type="descriptive",
                cypher_query="// Requires service type community analysis",
                difficulty=4,
                historical_context="East and West had different transport investment priorities",
                evaluation_method="human_expert",
                optimal_pipeline="graphrag_transport",
                acceptable_pipelines=["chatbot"],
                notes="Service type communities reveal political transport strategies"
            ),
            
            EvaluationQuestion(
                question_id="graphrag_006",
                question_text="What were the key transport network vulnerabilities and resilience patterns across Berlin communities?",
                category="global_analysis",
                sub_category="network_resilience",
                required_capabilities=["community_detection", "network_analysis", "resilience_assessment"],
                ground_truth=None,
                ground_truth_type="descriptive",
                cypher_query="// Requires multi-dimensional community analysis",
                difficulty=4,
                historical_context="Political division created network vulnerabilities and required resilience strategies",
                evaluation_method="human_expert",
                optimal_pipeline="graphrag_transport",
                acceptable_pipelines=["path_traversal"],
                notes="Community analysis reveals network vulnerability patterns"
            ),
            
            EvaluationQuestion(
                question_id="graphrag_007",
                question_text="How did the hierarchical organization of transport communities change during major political events?",
                category="global_analysis",
                sub_category="political_events",
                required_capabilities=["community_detection", "hierarchical_analysis", "event_analysis"],
                ground_truth=None,
                ground_truth_type="descriptive",
                cypher_query="// Requires temporal community hierarchy analysis",
                difficulty=4,
                historical_context="Wall construction and other events disrupted transport hierarchies",
                evaluation_method="human_expert",
                optimal_pipeline="graphrag_transport",
                acceptable_pipelines=["chatbot"],
                notes="Hierarchical community analysis shows organizational changes"
            ),
            
            EvaluationQuestion(
                question_id="graphrag_008",
                question_text="What transport community characteristics best predicted long-term network evolution?",
                category="global_analysis",
                sub_category="predictive_analysis",
                required_capabilities=["community_detection", "predictive_modeling", "evolution_analysis"],
                ground_truth=None,
                ground_truth_type="descriptive",
                cypher_query="// Requires comprehensive community analysis",
                difficulty=4,
                historical_context="Some community patterns persisted while others transformed",
                evaluation_method="human_expert",
                optimal_pipeline="graphrag_transport",
                acceptable_pipelines=["hybrid"],
                notes="Community characteristics as predictors of network evolution"
            )
        ]
    
    def create_failure_case_questions(self) -> List[EvaluationQuestion]:
        """Questions for testing graceful failure and robustness"""
        
        return [
            EvaluationQuestion(
                question_id="failure_001",
                question_text="What about transport in 1975?",
                category="failure_case",
                sub_category="temporal_out_of_bounds",
                required_capabilities=["temporal_boundary_detection", "graceful_failure"],
                ground_truth="Outside database temporal coverage",
                ground_truth_type="failure",
                cypher_query="""
                MATCH (y:Year {year: 1975})
                RETURN count(y) as year_exists
                """,
                difficulty=2,
                historical_context="Year outside database coverage",
                evaluation_method="failure_handling",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["no_rag"],
                notes="Tests handling of out-of-scope temporal queries"
            ),
            
            EvaluationQuestion(
                question_id="failure_002",
                question_text="How to get to London from Berlin?",
                category="failure_case",
                sub_category="geographic_out_of_scope",
                required_capabilities=["scope_detection", "geographic_boundary_awareness"],
                ground_truth="Outside database geographic scope",
                ground_truth_type="failure",
                cypher_query="// No valid query - outside scope",
                difficulty=2,
                historical_context="Geographic scope boundary",
                evaluation_method="failure_handling",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["no_rag"],
                notes="Tests geographic scope boundary detection"
            ),
            
            EvaluationQuestion(
                question_id="failure_003",
                question_text="What were transport ticket prices in 1967?",
                category="failure_case",
                sub_category="missing_data_type",
                required_capabilities=["data_availability_detection", "alternative_suggestion"],
                ground_truth="Data type not available in database",
                ground_truth_type="partial_failure",
                cypher_query="""
                MATCH (l:Line)-[:IN_YEAR]->(y:Year {year: 1967})
                RETURN l.price LIMIT 1
                """,
                difficulty=3,
                historical_context="Economic data not modeled in transport database",
                evaluation_method="failure_handling",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["no_rag", "direct_cypher"],
                notes="Tests handling of realistic but unavailable data"
            ),
            
            EvaluationQuestion(
                question_id="failure_004",
                question_text="Stations near Potsdamer Platz",
                category="failure_case",
                sub_category="potentially_problematic_entity",
                required_capabilities=["entity_validation", "alternative_processing"],
                ground_truth=None,
                ground_truth_type="uncertain",
                cypher_query="""
                MATCH (s:Station)
                WHERE s.name CONTAINS 'Potsdamer'
                RETURN s.name, s.stop_id
                """,
                difficulty=3,
                historical_context="Historically significant but potentially problematic location",
                evaluation_method="robustness",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["path_traversal", "vector"],
                notes="Tests handling of historically complex locations"
            ),
            
            EvaluationQuestion(
                question_id="failure_005",
                question_text="Modern Berlin transport vs historical",
                category="failure_case",
                sub_category="partially_answerable",
                required_capabilities=["scope_partitioning", "partial_answer_generation"],
                ground_truth=None,
                ground_truth_type="partial",
                cypher_query="// Can answer historical part only",
                difficulty=4,
                historical_context="Comparison requires modern data not in database",
                evaluation_method="partial_handling",
                optimal_pipeline="chatbot",
                acceptable_pipelines=["no_rag", "vector"],
                notes="Tests handling of partially answerable questions"
            )
        ]
    
    # Keep all original methods from the base taxonomy
    def create_relational_questions(self) -> List[EvaluationQuestion]:
        """Relational queries using verified relationships"""
        
        return [
            EvaluationQuestion(
                question_id="rel_001",
                question_text="Which stations did U-Bahn Line 6 serve in West Berlin in 1971?",
                category="relational",
                sub_category="line_stations",
                required_capabilities=["relationship_traversal", "filtering", "ordering"],
                ground_truth=None,
                ground_truth_type="list",
                cypher_query="""
                MATCH (l:Line {name: '6', type: 'u-bahn', east_west: 'west'})-[:IN_YEAR]->(y:Year {year: 1971})
                MATCH (l)-[r:SERVES]->(s:Station)
                RETURN s.name as station_name
                ORDER BY r.stop_order
                """,
                difficulty=2,
                historical_context="U-Bahn Line 6 in West Berlin network",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["path_traversal"]
            ),
            
            EvaluationQuestion(
                question_id="rel_002",
                question_text="How many stations were located in Mitte Ortsteil in 1965?",
                category="relational",
                sub_category="geographic_aggregation",
                required_capabilities=["geographic_filtering", "relationship_traversal", "counting"],
                ground_truth=None,
                ground_truth_type="exact",
                cypher_query="""
                MATCH (s:Station)-[:LOCATED_IN]->(ho:HistoricalOrtsteil {name: 'Mitte'})
                MATCH (s)-[:IN_YEAR]->(y:Year {year: 1965})
                MATCH (ho)-[:IN_YEAR]->(y)
                RETURN count(s) as stations_in_mitte
                """,
                difficulty=2,
                historical_context="Central Berlin before full division impact",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["multi_query_cypher"]
            ),
            
            EvaluationQuestion(
                question_id="rel_003",
                question_text="How many different transport types served Zoologischer Garten in 1967?",
                category="relational",
                sub_category="node_diversity",
                required_capabilities=["entity_lookup", "aggregation", "diversity_metrics"],
                ground_truth=None,
                ground_truth_type="exact",
                cypher_query="""
                MATCH (s:Station {name: 'Zoologischer Garten'})-[:IN_YEAR]->(y:Year {year: 1967})
                RETURN count(DISTINCT s.type) as transport_types_count
                """,
                difficulty=2,
                historical_context="Major West Berlin transport hub diversity",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["vector"]
            ),
            
            EvaluationQuestion(
                question_id="rel_004",
                question_text="Which lines served both East and West Berlin stations in 1964?",
                category="relational",
                sub_category="cross_boundary_analysis",
                required_capabilities=["relationship_traversal", "filtering", "boundary_crossing"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (l:Line)-[:IN_YEAR]->(y:Year {year: 1964})
                MATCH (l)-[:SERVES]->(s1:Station {east_west: 'east'})
                MATCH (l)-[:SERVES]->(s2:Station {east_west: 'west'})
                RETURN DISTINCT l.name as line_name, l.type as transport_type,
                       count(DISTINCT s1) as east_stations, count(DISTINCT s2) as west_stations
                ORDER BY l.name
                """,
                difficulty=4,
                historical_context="Cross-sector transport after division began",
                evaluation_method="automatic",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["path_traversal"]
            ),
            
            EvaluationQuestion(
                question_id="rel_005",
                question_text="What was the average frequency of tram lines in East Berlin in 1971?",
                category="relational",
                sub_category="aggregation_statistics",
                required_capabilities=["filtering", "aggregation", "statistics"],
                ground_truth=None,
                ground_truth_type="approximate",
                cypher_query="""
                MATCH (l:Line {type: 'tram', east_west: 'east'})-[:IN_YEAR]->(y:Year {year: 1971})
                WHERE l.frequency IS NOT NULL
                RETURN avg(l.frequency) as average_frequency
                """,
                difficulty=2,
                historical_context="East Berlin tram system efficiency in early 1970s",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["multi_query_cypher"]
            )
        ]
    
    def create_temporal_questions(self) -> List[EvaluationQuestion]:
        """Temporal queries using actual available years"""
        
        return [
            EvaluationQuestion(
                question_id="temp_001",
                question_text="How did the number of stations change from 1960 to 1967?",
                category="temporal",
                sub_category="change_over_time",
                required_capabilities=["temporal_filtering", "aggregation", "comparison"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (s:Station)-[:IN_YEAR]->(y:Year)
                WHERE y.year IN [1960, 1967]
                RETURN y.year as year, count(s) as station_count
                ORDER BY y.year
                """,
                difficulty=3,
                historical_context="Network changes across Berlin Wall construction period",
                evaluation_method="automatic",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["direct_cypher"]
            ),
            
            EvaluationQuestion(
                question_id="temp_002",
                question_text="When did oberleitungsbus (trolleybus) service first appear?",
                category="temporal",
                sub_category="first_occurrence",
                required_capabilities=["temporal_analysis", "minimum_finding"],
                ground_truth=None,
                ground_truth_type="exact",
                cypher_query="""
                MATCH (l:Line {type: 'oberleitungsbus'})-[:IN_YEAR]->(y:Year)
                RETURN min(y.year) as first_year_trolleybus
                """,
                difficulty=2,
                historical_context="Introduction of electric trolleybus service",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["multi_query_cypher"]
            ),
            
            EvaluationQuestion(
                question_id="temp_003",
                question_text="Which year had the highest total line capacity in East Berlin between 1964-1971?",
                category="temporal",
                sub_category="temporal_maximum",
                required_capabilities=["temporal_aggregation", "capacity_calculation", "maximum_finding"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (l:Line {east_west: 'east'})-[:IN_YEAR]->(y:Year)
                WHERE l.capacity IS NOT NULL AND y.year >= 1964 AND y.year <= 1971
                WITH y.year as year, sum(l.capacity) as total_capacity
                RETURN year, total_capacity
                ORDER BY total_capacity DESC
                LIMIT 1
                """,
                difficulty=4,
                historical_context="Peak capacity development in East Berlin",
                evaluation_method="automatic",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["direct_cypher"]
            ),
            
            EvaluationQuestion(
                question_id="temp_004",
                question_text="How did tram vs autobus distribution change from 1965 to 1967?",
                category="temporal",
                sub_category="modal_evolution",
                required_capabilities=["temporal_comparison", "modal_analysis", "proportion_calculation"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (s:Station)-[:IN_YEAR]->(y:Year)
                WHERE s.type IN ['tram', 'autobus'] AND y.year IN [1965, 1967]
                RETURN y.year as year, s.type as transport_type, count(s) as station_count
                ORDER BY year, transport_type
                """,
                difficulty=4,
                historical_context="Modal shift patterns in late 1960s",
                evaluation_method="consistency",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["vector"]
            ),
            
            EvaluationQuestion(
                question_id="temp_005",
                question_text="What was the trend in average line frequency from 1964 to 1971?",
                category="temporal",
                sub_category="trend_analysis",
                required_capabilities=["temporal_series", "trend_calculation", "statistical_analysis"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (l:Line)-[:IN_YEAR]->(y:Year)
                WHERE l.frequency IS NOT NULL AND y.year >= 1964 AND y.year <= 1971
                WITH y.year as year, avg(l.frequency) as avg_frequency
                RETURN year, avg_frequency
                ORDER BY year
                """,
                difficulty=4,
                historical_context="Service frequency evolution through division period",
                evaluation_method="consistency",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["vector"]
            )
        ]
    
    def create_spatial_questions(self) -> List[EvaluationQuestion]:
        """Spatial queries using verified administrative hierarchy"""
        
        return [
            EvaluationQuestion(
                question_id="spat_001",
                question_text="Which stations were located in Kreuzberg Bezirk in 1967?",
                category="spatial",
                sub_category="district_stations",
                required_capabilities=["geographic_filtering", "administrative_traversal"],
                ground_truth=None,
                ground_truth_type="list",
                cypher_query="""
                MATCH (s:Station)-[:LOCATED_IN]->(ho:HistoricalOrtsteil)-[:PART_OF]->(hb:HistoricalBezirk {name: 'Kreuzberg'})
                MATCH (s)-[:IN_YEAR]->(y:Year {year: 1967})
                MATCH (ho)-[:IN_YEAR]->(y)
                MATCH (hb)-[:IN_YEAR]->(y)
                RETURN s.name as station_name, s.type as transport_type, ho.name as ortsteil
                ORDER BY ho.name, s.name
                """,
                difficulty=2,
                historical_context="West Berlin district with complex transport history",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["multi_query_cypher"]
            ),
            
            EvaluationQuestion(
                question_id="spat_002",
                question_text="How many transport types were available in each political sector in 1967?",
                category="spatial",
                sub_category="political_transport_diversity",
                required_capabilities=["political_filtering", "diversity_analysis"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (s:Station)-[:IN_YEAR]->(y:Year {year: 1967})
                WHERE s.east_west IN ['east', 'west']
                RETURN s.east_west as political_sector,
                       count(DISTINCT s.type) as transport_diversity,
                       collect(DISTINCT s.type) as transport_types
                ORDER BY political_sector
                """,
                difficulty=2,
                historical_context="Transport availability across political division",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["multi_query_cypher", "vector"]
            ),
            
            EvaluationQuestion(
                question_id="spat_003",
                question_text="Which Bezirke had U-Bahn access in 1971?",
                category="spatial",
                sub_category="transit_accessibility",
                required_capabilities=["transport_filtering", "administrative_analysis"],
                ground_truth=None,
                ground_truth_type="list",
                cypher_query="""
                MATCH (s:Station {type: 'u-bahn'})-[:LOCATED_IN]->(ho:HistoricalOrtsteil)-[:PART_OF]->(hb:HistoricalBezirk)
                MATCH (s)-[:IN_YEAR]->(y:Year {year: 1971})
                MATCH (ho)-[:IN_YEAR]->(y)
                MATCH (hb)-[:IN_YEAR]->(y)
                RETURN DISTINCT hb.name as bezirk_with_ubahn
                ORDER BY hb.name
                """,
                difficulty=2,
                historical_context="U-Bahn network coverage by administrative area",
                evaluation_method="automatic",
                optimal_pipeline="direct_cypher",
                acceptable_pipelines=["multi_query_cypher"]
            ),
            
            EvaluationQuestion(
                question_id="spat_004",
                question_text="How did ferry service coverage differ between East and West in 1971?",
                category="spatial",
                sub_category="modal_geographic_analysis",
                required_capabilities=["transport_filtering", "political_comparison", "geographic_analysis"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (s:Station {type: 'ferry'})-[:IN_YEAR]->(y:Year {year: 1971})
                WHERE s.east_west IN ['east', 'west']
                MATCH (s)-[:LOCATED_IN]->(ho:HistoricalOrtsteil)
                MATCH (ho)-[:IN_YEAR]->(y)
                RETURN s.east_west as political_sector,
                       count(s) as ferry_stations,
                       count(DISTINCT ho.name) as ortsteile_with_ferry
                ORDER BY political_sector
                """,
                difficulty=3,
                historical_context="Ferry expansion pattern differences",
                evaluation_method="automatic",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["direct_cypher"]
            ),
            
            EvaluationQuestion(
                question_id="spat_005",
                question_text="Which Ortsteile had the most diverse transport options in 1965?",
                category="spatial",
                sub_category="transport_diversity_ranking",
                required_capabilities=["geographic_grouping", "diversity_calculation", "ranking"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (s:Station)-[:LOCATED_IN]->(ho:HistoricalOrtsteil)
                MATCH (s)-[:IN_YEAR]->(y:Year {year: 1965})
                MATCH (ho)-[:IN_YEAR]->(y)
                WITH ho.name as ortsteil, count(DISTINCT s.type) as transport_diversity,
                     collect(DISTINCT s.type) as transport_types
                RETURN ortsteil, transport_diversity, transport_types
                ORDER BY transport_diversity DESC, ortsteil
                LIMIT 10
                """,
                difficulty=3,
                historical_context="Transport diversity before full network separation",
                evaluation_method="automatic",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["vector"]
            )
        ]
    
    def create_complex_questions(self) -> List[EvaluationQuestion]:
        """Complex multi-hop queries using sophisticated capabilities"""
        
        return [
            EvaluationQuestion(
                question_id="complex_001",
                question_text="How did the political division affect transport network connectivity from 1961 to 1967?",
                category="multi_hop",
                sub_category="political_network_analysis",
                required_capabilities=["multi_temporal_analysis", "political_analysis", "connectivity_metrics"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (s:Station)-[:IN_YEAR]->(y:Year)
                WHERE s.east_west IN ['east', 'west'] AND y.year IN [1961, 1967]
                RETURN y.year as year, s.east_west as political_sector,
                       count(s) as stations,
                       count(DISTINCT s.type) as transport_diversity
                ORDER BY year, political_sector
                """,
                difficulty=5,
                historical_context="Infrastructure development under political division",
                evaluation_method="consistency",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["path_traversal", "vector"]
            ),
            
            EvaluationQuestion(
                question_id="complex_002",
                question_text="What was the relationship between line capacity and frequency across transport modes in 1967?",
                category="multi_hop",
                sub_category="operational_efficiency_analysis",
                required_capabilities=["capacity_frequency_correlation", "transport_mode_comparison"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (l:Line)-[:IN_YEAR]->(y:Year {year: 1967})
                WHERE l.capacity IS NOT NULL AND l.frequency IS NOT NULL
                RETURN l.type as transport_mode,
                       avg(l.capacity) as avg_capacity,
                       avg(l.frequency) as avg_frequency_minutes,
                       count(l) as line_count,
                       round(avg(l.capacity) / avg(l.frequency), 2) as capacity_frequency_ratio
                ORDER BY avg_capacity DESC
                """,
                difficulty=4,
                historical_context="Operational efficiency across transport modes",
                evaluation_method="consistency",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["vector"]
            ),
            
            EvaluationQuestion(
                question_id="complex_003",
                question_text="How did administrative areas adapt their transport offerings between 1964 and 1971?",
                category="multi_hop",
                sub_category="administrative_adaptation_analysis",
                required_capabilities=["temporal_comparison", "administrative_analysis", "adaptation_metrics"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (s:Station)-[:LOCATED_IN]->(ho:HistoricalOrtsteil)-[:PART_OF]->(hb:HistoricalBezirk)
                MATCH (s)-[:IN_YEAR]->(y:Year)
                MATCH (ho)-[:IN_YEAR]->(y)
                MATCH (hb)-[:IN_YEAR]->(y)
                WHERE y.year IN [1964, 1971]
                RETURN y.year as year, hb.name as bezirk,
                       count(s) as total_stations,
                       count(DISTINCT s.type) as transport_diversity,
                       collect(DISTINCT s.type) as transport_types
                ORDER BY year, bezirk
                """,
                difficulty=5,
                historical_context="Administrative response to changing transport needs",
                evaluation_method="expert",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["vector"]
            ),
            
            EvaluationQuestion(
                question_id="complex_004",
                question_text="Which transport investments showed the most growth between East and West from 1965-1971?",
                category="multi_hop",
                sub_category="investment_comparison_analysis",
                required_capabilities=["growth_calculation", "political_comparison", "investment_analysis"],
                ground_truth=None,
                ground_truth_type="complex",
                cypher_query="""
                MATCH (s:Station)-[:IN_YEAR]->(y:Year)
                WHERE s.east_west IN ['east', 'west'] AND y.year IN [1965, 1971]
                RETURN y.year as year, s.east_west as political_sector, s.type as transport_type,
                       count(s) as station_count
                ORDER BY year, political_sector, transport_type
                """,
                difficulty=5,
                historical_context="Comparative infrastructure investment patterns",
                evaluation_method="consistency",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["vector"]
            ),
            
            EvaluationQuestion(
                question_id="complex_005",
                question_text="How did the Berlin transport network demonstrate Cold War political ideology through infrastructure choices?",
                category="multi_hop",
                sub_category="ideology_infrastructure_analysis",
                required_capabilities=["political_analysis", "infrastructure_patterns", "ideological_interpretation"],
                ground_truth=None,
                ground_truth_type="subjective",
                cypher_query="""
                // Compare network characteristics by political sector 1967
                MATCH (s:Station)-[:IN_YEAR]->(y:Year {year: 1967})
                WHERE s.east_west IN ['east', 'west']
                OPTIONAL MATCH (s)<-[:SERVES]-(l:Line)-[:IN_YEAR]->(y)
                RETURN s.east_west as political_sector,
                       count(DISTINCT s) as stations,
                       count(DISTINCT s.type) as transport_diversity,
                       count(DISTINCT l) as lines,
                       avg(l.frequency) as avg_frequency,
                       avg(l.capacity) as avg_capacity
                ORDER BY political_sector
                """,
                difficulty=5,
                historical_context="Material manifestation of Cold War ideology",
                evaluation_method="expert",
                optimal_pipeline="multi_query_cypher",
                acceptable_pipelines=["vector", "no_rag"]
            )
        ]
    
    def get_all_questions(self) -> List[EvaluationQuestion]:
        """Return complete extended question taxonomy"""
        
        all_questions = []
        all_questions.extend(self.create_factual_questions())
        all_questions.extend(self.create_relational_questions())
        all_questions.extend(self.create_temporal_questions())
        all_questions.extend(self.create_spatial_questions())
        all_questions.extend(self.create_complex_questions())
        
        # New question categories
        all_questions.extend(self.create_path_traversal_questions())
        all_questions.extend(self.create_vector_similarity_questions())
        all_questions.extend(self.create_natural_language_questions())
        all_questions.extend(self.create_general_knowledge_questions())
        all_questions.extend(self.create_routing_challenge_questions())
        all_questions.extend(self.create_graphrag_global_questions())
        all_questions.extend(self.create_failure_case_questions())
        
        return all_questions

def generate_extended_taxonomy_summary():
    """Generate summary of extended question taxonomy"""
    
    taxonomy = ExtendedBerlinTransportQuestionTaxonomy()
    questions = taxonomy.get_all_questions()
    
    summary = {
        "total_questions": len(questions),
        "by_category": {},
        "by_optimal_pipeline": {},
        "by_difficulty": {},
        "by_evaluation_method": {},
        "new_categories": [
            "path_traversal", "vector_similarity", "natural_language", 
            "general_knowledge", "routing_challenge", "failure_case"
        ],
        "pipeline_coverage": {
            "direct_cypher": 0,
            "multi_query_cypher": 0,
            "vector": 0,
            "path_traversal": 0,
            "chatbot": 0,
            "no_rag": 0
        }
    }
    
    for question in questions:
        # Count by category
        summary["by_category"][question.category] = summary["by_category"].get(question.category, 0) + 1
        
        # Count by optimal pipeline
        summary["by_optimal_pipeline"][question.optimal_pipeline] = summary["by_optimal_pipeline"].get(question.optimal_pipeline, 0) + 1
        
        # Count by difficulty
        summary["by_difficulty"][question.difficulty] = summary["by_difficulty"].get(question.difficulty, 0) + 1
        
        # Count by evaluation method
        summary["by_evaluation_method"][question.evaluation_method] = summary["by_evaluation_method"].get(question.evaluation_method, 0) + 1
        
        # Pipeline coverage
        if question.optimal_pipeline in summary["pipeline_coverage"]:
            summary["pipeline_coverage"][question.optimal_pipeline] += 1
        
        # Also count acceptable pipelines
        for pipeline in question.acceptable_pipelines:
            if pipeline in summary["pipeline_coverage"]:
                summary["pipeline_coverage"][pipeline] += 0.5  # Partial credit
    
    return summary

if __name__ == "__main__":
    # Generate and display extended summary
    summary = generate_extended_taxonomy_summary()
    print("=== EXTENDED QUESTION TAXONOMY SUMMARY ===")
    print(f"Total Questions: {summary['total_questions']}")
    print(f"\nNew Categories Added: {summary['new_categories']}")
    print("\nCategory Distribution:")
    for category, count in summary['by_category'].items():
        print(f"  {category}: {count}")
    print("\nOptimal Pipeline Distribution:")
    for pipeline, count in summary['by_optimal_pipeline'].items():
        print(f"  {pipeline}: {count}")
    print("\nPipeline Coverage (including acceptable):")
    for pipeline, count in summary['pipeline_coverage'].items():
        print(f"  {pipeline}: {count:.1f}")
    print("\nDifficulty Distribution:")
    for difficulty, count in summary['by_difficulty'].items():
        print(f"  Level {difficulty}: {count}")