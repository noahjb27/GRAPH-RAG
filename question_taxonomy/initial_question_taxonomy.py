"""
Final Berlin Transport Graph-RAG Question Taxonomy
Based on actual database analysis and verified data availability

Key Updates:
- Uses actual available years and entities
- Accounts for political timeline (unified→divided)
- Uses correct station/line names found in database
- Addresses data quality issues discovered
- Focuses on high-quality, answerable questions
"""

from typing import List, Dict, Any
from dataclasses import dataclass

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
    notes: str = ""

class FinalBerlinTransportQuestionTaxonomy:
    """Final question taxonomy verified against actual database"""
    
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
            )
        ]
    
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="consistency"
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
                evaluation_method="consistency"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="automatic"
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
                evaluation_method="consistency"
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
                evaluation_method="consistency"
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
                evaluation_method="expert"
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
                evaluation_method="consistency"
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
                evaluation_method="expert"
            )
        ]
    
    def get_all_questions(self) -> List[EvaluationQuestion]:
        """Return complete question taxonomy"""
        
        all_questions = []
        all_questions.extend(self.create_factual_questions())
        all_questions.extend(self.create_relational_questions())
        all_questions.extend(self.create_temporal_questions())
        all_questions.extend(self.create_spatial_questions())
        all_questions.extend(self.create_complex_questions())
        
        return all_questions

# Additional verification queries for the final taxonomy
def get_final_verification_queries():
    """Verification queries for the final question set"""
    
    return {
        "verify_line_1_tram_1964": """
        MATCH (l:Line {name: '1', type: 'tram'})-[:IN_YEAR]->(y:Year {year: 1964})
        RETURN l.frequency, l.capacity, l.east_west
        """,
        
        "verify_alexanderplatz_1965": """
        MATCH (s:Station {name: 'Alexanderplatz'})-[:IN_YEAR]->(y:Year {year: 1965})
        RETURN s.type, s.east_west, count(*) as count
        """,
        
        "verify_zoologischer_garten_1967": """
        MATCH (s:Station {name: 'Zoologischer Garten'})-[:IN_YEAR]->(y:Year {year: 1967})
        RETURN s.type, s.east_west, count(*) as count
        """,
        
        "verify_ubahn_line_6_west_1971": """
        MATCH (l:Line {name: '6', type: 'u-bahn', east_west: 'west'})-[:IN_YEAR]->(y:Year {year: 1971})
        MATCH (l)-[:SERVES]->(s:Station)
        RETURN count(s) as stations_served
        """,
        
        "verify_mitte_ortsteil_stations_1965": """
        MATCH (s:Station)-[:LOCATED_IN]->(ho:HistoricalOrtsteil {name: 'Mitte'})
        MATCH (s)-[:IN_YEAR]->(y:Year {year: 1965})
        MATCH (ho)-[:IN_YEAR]->(y)
        RETURN count(s) as stations_in_mitte
        """,
        
        "verify_oberleitungsbus_years": """
        MATCH (l:Line {type: 'oberleitungsbus'})-[:IN_YEAR]->(y:Year)
        RETURN collect(DISTINCT y.year) as trolleybus_years
        """,
        
        "verify_ferry_1971_east_west": """
        MATCH (s:Station {type: 'ferry'})-[:IN_YEAR]->(y:Year {year: 1971})
        WHERE s.east_west IN ['east', 'west']
        RETURN s.east_west, count(s) as ferry_stations
        """
    }

# Summary statistics for the final taxonomy
def generate_taxonomy_summary():
    """Generate summary of final question taxonomy"""
    
    taxonomy = FinalBerlinTransportQuestionTaxonomy()
    questions = taxonomy.get_all_questions()
    
    summary = {
        "total_questions": len(questions),
        "by_category": {},
        "by_difficulty": {},
        "by_evaluation_method": {},
        "years_used": set(),
        "entities_referenced": set(),
        "key_improvements": [
            "Uses actual verified station names (Alexanderplatz, Zoologischer Garten)",
            "Accounts for political timeline (unified→divided)",
            "Uses available years only (1964, 1965, 1967, 1971)",
            "Addresses data quality issues (avoids problematic connection capacity)",
            "Focuses on high-quality answerable questions",
            "Includes sophisticated temporal modeling questions",
            "Leverages transport type evolution (oberleitungsbus, line type changes)"
        ]
    }
    
    for question in questions:
        # Count by category
        summary["by_category"][question.category] = summary["by_category"].get(question.category, 0) + 1
        
        # Count by difficulty
        summary["by_difficulty"][question.difficulty] = summary["by_difficulty"].get(question.difficulty, 0) + 1
        
        # Count by evaluation method
        summary["by_evaluation_method"][question.evaluation_method] = summary["by_evaluation_method"].get(question.evaluation_method, 0) + 1
        
        # Extract years from queries
        if "1964" in question.cypher_query:
            summary["years_used"].add(1964)
        if "1965" in question.cypher_query:
            summary["years_used"].add(1965)
        if "1967" in question.cypher_query:
            summary["years_used"].add(1967)
        if "1971" in question.cypher_query:
            summary["years_used"].add(1971)
        
        # Extract key entities
        if "Alexanderplatz" in question.cypher_query:
            summary["entities_referenced"].add("Alexanderplatz")
        if "Zoologischer Garten" in question.cypher_query:
            summary["entities_referenced"].add("Zoologischer Garten")
        if "Mitte" in question.cypher_query:
            summary["entities_referenced"].add("Mitte")
        if "Kreuzberg" in question.cypher_query:
            summary["entities_referenced"].add("Kreuzberg")
    
    # Convert sets to lists for JSON serialization
    summary["years_used"] = sorted(list(summary["years_used"]))
    summary["entities_referenced"] = sorted(list(summary["entities_referenced"]))
    
    return summary

if __name__ == "__main__":
    # Generate and display summary
    summary = generate_taxonomy_summary()
    print("=== FINAL QUESTION TAXONOMY SUMMARY ===")
    print(f"Total Questions: {summary['total_questions']}")
    print(f"Years Used: {summary['years_used']}")
    print(f"Key Entities: {summary['entities_referenced']}")
    print("\nCategory Distribution:")
    for category, count in summary['by_category'].items():
        print(f"  {category}: {count}")
    print("\nDifficulty Distribution:")
    for difficulty, count in summary['by_difficulty'].items():
        print(f"  Level {difficulty}: {count}")