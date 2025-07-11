"""
Graph-to-Text Conversion Module for Vector-based RAG Pipeline

This module converts Neo4j graph data into textual representations
that can be embedded and stored in a vector database.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
from ..database.neo4j_client import Neo4jClient, Neo4jQueryResult
from ..config import settings

@dataclass
class GraphTextChunk:
    """A chunk of text derived from graph data"""
    
    id: str
    content: str
    metadata: Dict[str, Any]
    source_entities: List[str]
    temporal_context: Optional[str] = None
    spatial_context: Optional[str] = None
    chunk_type: str = "narrative"  # "triple", "narrative", "hybrid"
    
    def __post_init__(self):
        if not self.metadata:
            self.metadata = {}

class GraphToTextConverter:
    """Converts Neo4j graph data to textual representations"""
    
    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j_client = neo4j_client
        self.chunk_counter = 0
        
    async def convert_entire_graph(self) -> List[GraphTextChunk]:
        """Convert the entire graph to text chunks - comprehensive factual coverage"""
        
        chunks = []
        
        print("Converting comprehensive graph data to text...")
        
        # PHASE 1: Individual entity property chunks (extremely granular)
        print("  Phase 1: Converting individual entity properties...")
        chunks.extend(await self._convert_individual_station_properties())
        chunks.extend(await self._convert_individual_line_properties())
        
        # PHASE 2: Individual relationship chunks  
        print("  Phase 2: Converting individual relationships...")
        chunks.extend(await self._convert_individual_serves_relationships())
        chunks.extend(await self._convert_individual_location_relationships())
        chunks.extend(await self._convert_individual_temporal_relationships())
        chunks.extend(await self._convert_individual_connection_relationships())
        
        # PHASE 3: Aggregated narrative chunks (existing comprehensive methods)
        if settings.graph_to_text_strategy in ["narrative", "hybrid"]:
            print("  Phase 3: Converting aggregated narratives...")
            chunks.extend(await self._convert_stations_comprehensive())
            chunks.extend(await self._convert_lines_comprehensive())
            chunks.extend(await self._convert_temporal_snapshots())
            chunks.extend(await self._convert_administrative_areas())
        
        # PHASE 4: Complex relationship patterns
        print("  Phase 4: Converting complex relationship patterns...")
        chunks.extend(await self._convert_station_line_relationships())
        chunks.extend(await self._convert_geographic_relationships())
        chunks.extend(await self._convert_temporal_relationships())
        chunks.extend(await self._convert_line_operational_data())
        chunks.extend(await self._convert_political_division_data())
        
        # PHASE 5: Structured triples for every relationship type
        if settings.graph_to_text_strategy in ["triple", "hybrid"]:
            print("  Phase 5: Converting all relationships to structured triples...")
            chunks.extend(await self._convert_all_relationships_to_triples())
            
        print(f"  Total chunks created: {len(chunks)}")
        return chunks
    
    async def _convert_stations_narrative(self) -> List[GraphTextChunk]:
        """Convert station data to narrative descriptions"""
        
        query = """
        MATCH (s:Station)-[:IN_YEAR]->(y:Year)
        OPTIONAL MATCH (s)-[:LOCATED_IN]->(area:HistoricalOrtsteil)
        OPTIONAL MATCH (s)<-[:SERVES]-(l:Line)
        WITH s, y, area, collect(DISTINCT l.name) as lines
        ORDER BY s.name, y.year
        RETURN s, y, area, lines
        LIMIT 1000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            station = record.get('s', {})
            year = record.get('y', {})
            area = record.get('area', {})
            lines = record.get('lines', [])
            
            # Create narrative description
            narrative = self._create_station_narrative(station, year, area, lines)
            
            chunk = GraphTextChunk(
                id=f"station_{station.get('stop_id', 'unknown')}_{year.get('year', 'unknown')}_{self.chunk_counter}",
                content=narrative,
                metadata={
                    "entity_type": "station",
                    "station_id": station.get('stop_id'),
                    "year": year.get('year'),
                    "transport_type": station.get('type'),
                    "political_side": station.get('east_west'),
                    "area_name": area.get('name') if area else None
                },
                source_entities=[f"station:{station.get('stop_id')}"],
                temporal_context=f"Year {year.get('year')}" if year.get('year') else None,
                spatial_context=area.get('name') if area else None,
                chunk_type="narrative"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks
    
    def _create_station_narrative(self, station: Dict, year: Dict, area: Dict, lines: List[str]) -> str:
        """Create a narrative description of a station"""
        
        name = station.get('name', 'Unknown Station')
        transport_type = station.get('type', 'unknown')
        political_side = station.get('east_west', 'unknown')
        year_val = year.get('year', 'unknown year')
        
        narrative = f"In {year_val}, {name} was a {transport_type} station"
        
        if political_side != 'unknown':
            narrative += f" located in {political_side} Berlin"
            
        if area and area.get('name'):
            narrative += f" in the {area.get('name')} area"
            
        if lines:
            line_text = ', '.join([l for l in lines if l])
            narrative += f". It was served by the following transit lines: {line_text}"
            
        # Add geographic context if available
        if station.get('latitude') and station.get('longitude'):
            narrative += f". The station is located at coordinates {station.get('latitude'):.4f}, {station.get('longitude'):.4f}"
            
        narrative += "."
        
        return narrative
    
    async def _convert_lines_narrative(self) -> List[GraphTextChunk]:
        """Convert line data to narrative descriptions"""
        
        query = """
        MATCH (l:Line)-[:IN_YEAR]->(y:Year)
        OPTIONAL MATCH (l)-[:SERVES]->(s:Station)
        WITH l, y, collect(DISTINCT s.name) as stations
        ORDER BY l.name, y.year
        RETURN l, y, stations
        LIMIT 500
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            line = record.get('l', {})
            year = record.get('y', {})
            stations = record.get('stations', [])
            
            narrative = self._create_line_narrative(line, year, stations)
            
            chunk = GraphTextChunk(
                id=f"line_{line.get('line_id', 'unknown')}_{year.get('year', 'unknown')}_{self.chunk_counter}",
                content=narrative,
                metadata={
                    "entity_type": "line",
                    "line_id": line.get('line_id'),
                    "year": year.get('year'),
                    "transport_type": line.get('type'),
                    "political_side": line.get('east_west'),
                    "frequency": line.get('frequency'),
                    "capacity": line.get('capacity')
                },
                source_entities=[f"line:{line.get('line_id')}"],
                temporal_context=f"Year {year.get('year')}" if year.get('year') else None,
                chunk_type="narrative"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks
    
    def _create_line_narrative(self, line: Dict, year: Dict, stations: List[str]) -> str:
        """Create a narrative description of a transit line"""
        
        name = line.get('name', 'Unknown Line')
        line_id = line.get('line_id', 'unknown')
        transport_type = line.get('type', 'unknown')
        political_side = line.get('east_west', 'unknown')
        year_val = year.get('year', 'unknown year')
        frequency = line.get('frequency')
        capacity = line.get('capacity')
        
        narrative = f"In {year_val}, {transport_type} line {name} (ID: {line_id})"
        
        if political_side != 'unknown':
            narrative += f" operated in {political_side} Berlin"
            
        if frequency:
            narrative += f" with a service frequency of {frequency} minutes"
            
        if capacity:
            narrative += f" and a capacity of {capacity} passengers"
            
        if stations:
            # Limit station list to avoid very long chunks
            station_list = stations[:10]  # First 10 stations
            station_text = ', '.join([s for s in station_list if s])
            narrative += f". The line served stations including: {station_text}"
            if len(stations) > 10:
                narrative += f" and {len(stations) - 10} additional stations"
                
        narrative += "."
        
        return narrative
    
    async def _convert_temporal_snapshots(self) -> List[GraphTextChunk]:
        """Convert temporal evolution data to narrative descriptions"""
        
        query = """
        MATCH (y:Year)
        OPTIONAL MATCH (s:Station)-[:IN_YEAR]->(y)
        OPTIONAL MATCH (l:Line)-[:IN_YEAR]->(y)
        WITH y, count(DISTINCT s) as station_count, count(DISTINCT l) as line_count
        ORDER BY y.year
        RETURN y, station_count, line_count
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            year = record.get('y', {})
            station_count = record.get('station_count', 0)
            line_count = record.get('line_count', 0)
            
            year_val = year.get('year')
            if not year_val:
                continue
                
            narrative = f"In {year_val}, Berlin's public transport network consisted of {station_count} stations and {line_count} transit lines."
            
            # Add historical context
            if year_val <= 1960:
                narrative += " This was during the unified Berlin period before the construction of the Berlin Wall."
            elif year_val >= 1961:
                narrative += " This was during the divided Berlin period after the construction of the Berlin Wall in 1961."
                
            chunk = GraphTextChunk(
                id=f"temporal_snapshot_{year_val}_{self.chunk_counter}",
                content=narrative,
                metadata={
                    "entity_type": "temporal_snapshot",
                    "year": year_val,
                    "station_count": station_count,
                    "line_count": line_count
                },
                source_entities=[f"year:{year_val}"],
                temporal_context=f"Year {year_val}",
                chunk_type="narrative"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks
    
    async def _convert_administrative_areas(self) -> List[GraphTextChunk]:
        """Convert administrative area data to narrative descriptions"""
        
        query = """
        MATCH (area:HistoricalOrtsteil)-[:IN_YEAR]->(y:Year)
        OPTIONAL MATCH (area)-[:PART_OF]->(bezirk:HistoricalBezirk)
        OPTIONAL MATCH (s:Station)-[:LOCATED_IN]->(area)
        WITH area, y, bezirk, count(DISTINCT s) as station_count
        ORDER BY area.name, y.year
        RETURN area, y, bezirk, station_count
        LIMIT 200
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            area = record.get('area', {})
            year = record.get('y', {})
            bezirk = record.get('bezirk', {})
            station_count = record.get('station_count', 0)
            
            narrative = self._create_area_narrative(area, year, bezirk, station_count)
            
            chunk = GraphTextChunk(
                id=f"area_{area.get('historical_ortsteil_id', 'unknown')}_{year.get('year', 'unknown')}_{self.chunk_counter}",
                content=narrative,
                metadata={
                    "entity_type": "administrative_area",
                    "area_id": area.get('historical_ortsteil_id'),
                    "area_name": area.get('name'),
                    "year": year.get('year'),
                    "bezirk_name": bezirk.get('name') if bezirk else None,
                    "station_count": station_count,
                    "population": area.get('population'),
                    "area_km2": area.get('area_km2')
                },
                source_entities=[f"area:{area.get('historical_ortsteil_id')}"],
                temporal_context=f"Year {year.get('year')}" if year.get('year') else None,
                spatial_context=area.get('name'),
                chunk_type="narrative"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks
    
    def _create_area_narrative(self, area: Dict, year: Dict, bezirk: Dict, station_count: int) -> str:
        """Create a narrative description of an administrative area"""
        
        area_name = area.get('name', 'Unknown Area')
        year_val = year.get('year', 'unknown year')
        population = area.get('population')
        area_km2 = area.get('area_km2')
        bezirk_name = bezirk.get('name') if bezirk else None
        
        narrative = f"In {year_val}, {area_name}"
        
        if bezirk_name:
            narrative += f" (part of {bezirk_name} district)"
            
        if population:
            narrative += f" had a population of {population:,} residents"
            
        if area_km2:
            narrative += f" covering an area of {area_km2:.2f} square kilometers"
            
        if station_count > 0:
            narrative += f". The area was served by {station_count} public transport stations"
        else:
            narrative += f". The area had no public transport stations during this period"
            
        narrative += "."
        
        return narrative
    
    async def _convert_relationships_to_triples(self) -> List[GraphTextChunk]:
        """Convert graph relationships to structured triples"""
        
        query = """
        MATCH (s:Station)-[r:SERVES]-(l:Line)
        WHERE exists(s.name) AND exists(l.name)
        RETURN s.name as station_name, type(r) as relationship, l.name as line_name
        LIMIT 2000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            station_name = record.get('station_name', 'Unknown')
            relationship = record.get('relationship', 'CONNECTED_TO')
            line_name = record.get('line_name', 'Unknown')
            
            triple_content = f"TRIPLE: {station_name} - {relationship} - {line_name}"
            
            chunk = GraphTextChunk(
                id=f"triple_{self.chunk_counter}",
                content=triple_content,
                metadata={
                    "entity_type": "relationship_triple",
                    "subject": station_name,
                    "predicate": relationship,
                    "object": line_name
                },
                source_entities=[station_name, line_name],
                chunk_type="triple"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks

    async def _convert_stations_comprehensive(self) -> List[GraphTextChunk]:
        """Convert station data with comprehensive details for factual search"""
        
        query = """
        MATCH (s:Station)-[:IN_YEAR]->(y:Year)
        OPTIONAL MATCH (s)-[:LOCATED_IN]->(area:HistoricalOrtsteil)
        OPTIONAL MATCH (area)-[:PART_OF]->(bezirk:Bezirk)
        OPTIONAL MATCH (s)<-[:SERVES]-(l:Line)
        WITH s, y, area, bezirk, collect(DISTINCT l) as lines
        ORDER BY s.name, y.year
        RETURN s, y, area, bezirk, lines
        LIMIT 1500
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            station = record.get('s', {})
            year = record.get('y', {})
            area = record.get('area', {})
            bezirk = record.get('bezirk', {})
            lines = record.get('lines', [])
            
            narrative = self._create_comprehensive_station_narrative(station, year, area, bezirk, lines)
            
            chunk = GraphTextChunk(
                id=f"station_comprehensive_{station.get('stop_id', 'unknown')}_{year.get('year', 'unknown')}_{self.chunk_counter}",
                content=narrative,
                metadata={
                    "entity_type": "station",
                    "station_id": station.get('stop_id'),
                    "station_name": station.get('name'),
                    "year": year.get('year'),
                    "transport_type": station.get('type'),
                    "political_side": station.get('east_west'),
                    "area_name": area.get('name') if area else None,
                    "bezirk_name": bezirk.get('name') if bezirk else None,
                    "latitude": station.get('latitude'),
                    "longitude": station.get('longitude'),
                    "line_count": len(lines)
                },
                source_entities=[f"station:{station.get('stop_id')}"],
                temporal_context=f"Year {year.get('year')}" if year.get('year') else None,
                spatial_context=area.get('name') if area else bezirk.get('name') if bezirk else None,
                chunk_type="narrative"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks

    def _create_comprehensive_station_narrative(self, station: Dict, year: Dict, area: Dict, bezirk: Dict, lines: List[Dict]) -> str:
        """Create comprehensive station description with all available facts"""
        
        name = station.get('name', 'Unknown Station')
        station_id = station.get('stop_id', 'unknown')
        transport_type = station.get('type', 'unknown')
        political_side = station.get('east_west', 'unknown')
        year_val = year.get('year', 'unknown year')
        lat = station.get('latitude')
        lon = station.get('longitude')
        
        narrative = f"Station {name} (ID: {station_id}) was a {transport_type} station in {year_val}"
        
        if political_side != 'unknown':
            narrative += f" operating in {political_side} Berlin"
            
        if area and area.get('name'):
            narrative += f" located in the {area.get('name')} neighborhood"
            
        if bezirk and bezirk.get('name'):
            narrative += f" within {bezirk.get('name')} district"
            
        if lat and lon:
            narrative += f". The station was positioned at geographic coordinates {lat:.4f}, {lon:.4f}"
            
        if lines:
            line_names = [l.get('name', '') for l in lines if l.get('name')]
            line_types = [l.get('type', '') for l in lines if l.get('type')]
            line_frequencies = [l.get('frequency') for l in lines if l.get('frequency')]
            
            if line_names:
                narrative += f". The station was served by {len(line_names)} transit lines: {', '.join(line_names)}"
                
            if line_types:
                unique_types = list(set(line_types))
                narrative += f". Transport types included: {', '.join(unique_types)}"
                
            if line_frequencies:
                avg_freq = sum(f for f in line_frequencies if f) / len([f for f in line_frequencies if f])
                narrative += f". Average service frequency was {avg_freq:.1f} minutes"
        else:
            narrative += ". No transit lines served this station in this year"
            
        narrative += "."
        return narrative

    async def _convert_lines_comprehensive(self) -> List[GraphTextChunk]:
        """Convert line data with comprehensive operational details"""
        
        query = """
        MATCH (l:Line)-[:IN_YEAR]->(y:Year)
        OPTIONAL MATCH (l)-[:SERVES]->(s:Station)
        OPTIONAL MATCH (s)-[:LOCATED_IN]->(area:HistoricalOrtsteil)
        WITH l, y, collect(DISTINCT s) as stations, collect(DISTINCT area.name) as areas
        ORDER BY l.name, y.year
        RETURN l, y, stations, areas
        LIMIT 750
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            line = record.get('l', {})
            year = record.get('y', {})
            stations = record.get('stations', [])
            areas = record.get('areas', [])
            
            narrative = self._create_comprehensive_line_narrative(line, year, stations, areas)
            
            chunk = GraphTextChunk(
                id=f"line_comprehensive_{line.get('line_id', 'unknown')}_{year.get('year', 'unknown')}_{self.chunk_counter}",
                content=narrative,
                metadata={
                    "entity_type": "line",
                    "line_id": line.get('line_id'),
                    "line_name": line.get('name'),
                    "year": year.get('year'),
                    "transport_type": line.get('type'),
                    "political_side": line.get('east_west'),
                    "frequency": line.get('frequency'),
                    "capacity": line.get('capacity'),
                    "station_count": len(stations),
                    "area_count": len([a for a in areas if a])
                },
                source_entities=[f"line:{line.get('line_id')}"],
                temporal_context=f"Year {year.get('year')}" if year.get('year') else None,
                chunk_type="narrative"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks

    def _create_comprehensive_line_narrative(self, line: Dict, year: Dict, stations: List[Dict], areas: List[str]) -> str:
        """Create comprehensive line description with operational details"""
        
        name = line.get('name', 'Unknown Line')
        line_id = line.get('line_id', 'unknown')
        transport_type = line.get('type', 'unknown')
        political_side = line.get('east_west', 'unknown')
        year_val = year.get('year', 'unknown year')
        frequency = line.get('frequency')
        capacity = line.get('capacity')
        
        narrative = f"Transit line {name} (ID: {line_id}) was a {transport_type} line operating in {year_val}"
        
        if political_side != 'unknown':
            narrative += f" in {political_side} Berlin"
            
        if frequency:
            narrative += f" with a service frequency of {frequency} minutes between vehicles"
            
        if capacity:
            narrative += f" and a vehicle capacity of {capacity} passengers"
            
        if stations:
            station_names = [s.get('name', '') for s in stations if s.get('name')]
            narrative += f". The line served {len(station_names)} stations"
            
            if station_names:
                # Include first and last stations
                if len(station_names) >= 2:
                    narrative += f" from {station_names[0]} to {station_names[-1]}"
                    if len(station_names) > 2:
                        narrative += f", including intermediate stops at {', '.join(station_names[1:-1])}"
                elif len(station_names) == 1:
                    narrative += f": {station_names[0]}"
                    
        if areas:
            unique_areas = [a for a in areas if a]
            if unique_areas:
                narrative += f". The line route passed through {len(unique_areas)} neighborhoods: {', '.join(unique_areas[:10])}"
                if len(unique_areas) > 10:
                    narrative += f" and {len(unique_areas) - 10} additional areas"
                    
        narrative += "."
        return narrative

    async def _convert_station_line_relationships(self) -> List[GraphTextChunk]:
        """Convert station-line serving relationships to searchable text"""
        
        query = """
        MATCH (s:Station)<-[:SERVES]-(l:Line)
        MATCH (s)-[:IN_YEAR]->(y:Year)
        MATCH (l)-[:IN_YEAR]->(y)
        WHERE s.name IS NOT NULL AND l.name IS NOT NULL
        RETURN s.name as station_name, s.type as station_type, 
               l.name as line_name, l.type as line_type, 
               y.year as year, l.frequency as frequency
        ORDER BY y.year, s.name, l.name
        LIMIT 2000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            station_name = record.get('station_name', 'Unknown Station')
            station_type = record.get('station_type', 'unknown')
            line_name = record.get('line_name', 'Unknown Line')
            line_type = record.get('line_type', 'unknown')
            year = record.get('year', 'unknown')
            frequency = record.get('frequency')
            
            content = f"In {year}, {line_type} line {line_name} served {station_type} station {station_name}"
            
            if frequency:
                content += f" with {frequency}-minute service intervals"
                
            content += ". This service connection was part of Berlin's public transport network."
            
            chunk = GraphTextChunk(
                id=f"station_line_rel_{self.chunk_counter}",
                content=content,
                metadata={
                    "entity_type": "station_line_relationship",
                    "station_name": station_name,
                    "line_name": line_name,
                    "year": year,
                    "station_type": station_type,
                    "line_type": line_type,
                    "frequency": frequency
                },
                source_entities=[f"station:{station_name}", f"line:{line_name}"],
                temporal_context=f"Year {year}",
                chunk_type="relationship"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks

    async def _convert_geographic_relationships(self) -> List[GraphTextChunk]:
        """Convert geographic and administrative relationships to searchable text"""
        
        query = """
        MATCH (s:Station)-[:LOCATED_IN]->(area:HistoricalOrtsteil)-[:PART_OF]->(bezirk:Bezirk)
        MATCH (s)-[:IN_YEAR]->(y:Year)
        WHERE s.name IS NOT NULL AND area.name IS NOT NULL AND bezirk.name IS NOT NULL
        RETURN DISTINCT s.name as station_name, s.type as station_type,
               area.name as area_name, bezirk.name as bezirk_name,
               y.year as year, s.east_west as political_side
        ORDER BY y.year, bezirk.name, area.name, s.name
        LIMIT 1500
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            station_name = record.get('station_name', 'Unknown')
            station_type = record.get('station_type', 'unknown')
            area_name = record.get('area_name', 'Unknown Area')
            bezirk_name = record.get('bezirk_name', 'Unknown District')
            year = record.get('year', 'unknown')
            political_side = record.get('political_side', 'unknown')
            
            content = f"In {year}, {station_type} station {station_name} was located in the {area_name} neighborhood"
            content += f" within {bezirk_name} district"
            
            if political_side != 'unknown':
                content += f" in {political_side} Berlin"
                
            content += ". This geographic placement determined the station's administrative jurisdiction and political accessibility."
            
            chunk = GraphTextChunk(
                id=f"geographic_rel_{self.chunk_counter}",
                content=content,
                metadata={
                    "entity_type": "geographic_relationship",
                    "station_name": station_name,
                    "area_name": area_name,
                    "bezirk_name": bezirk_name,
                    "year": year,
                    "political_side": political_side,
                    "station_type": station_type
                },
                source_entities=[f"station:{station_name}", f"area:{area_name}", f"bezirk:{bezirk_name}"],
                temporal_context=f"Year {year}",
                spatial_context=area_name,
                chunk_type="relationship"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks

    async def _convert_temporal_relationships(self) -> List[GraphTextChunk]:
        """Convert temporal evolution relationships to searchable text"""
        
        query = """
        MATCH (entity)-[:IN_YEAR]->(y1:Year), (entity)-[:IN_YEAR]->(y2:Year)
        WHERE y1.year < y2.year AND y2.year - y1.year <= 5
        AND (entity:Station OR entity:Line)
        WITH entity, y1, y2
        ORDER BY entity.name, y1.year
        RETURN entity.name as entity_name, 
               labels(entity)[0] as entity_type,
               y1.year as start_year, y2.year as end_year,
               entity.type as transport_type
        LIMIT 1000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            entity_name = record.get('entity_name', 'Unknown')
            entity_type = record.get('entity_type', 'Unknown').lower()
            start_year = record.get('start_year', 'unknown')
            end_year = record.get('end_year', 'unknown')
            transport_type = record.get('transport_type', 'unknown')
            
            content = f"The {transport_type} {entity_type} {entity_name} operated continuously from {start_year} to {end_year}"
            content += f" in Berlin's public transport system. This represents {end_year - start_year} years of service"
            
            if start_year <= 1961 <= end_year:
                content += " spanning the period before and after the Berlin Wall construction"
            elif start_year <= 1961:
                content += " during the unified Berlin period"
            elif start_year > 1961:
                content += " during the divided Berlin period"
                
            content += "."
            
            chunk = GraphTextChunk(
                id=f"temporal_rel_{self.chunk_counter}",
                content=content,
                metadata={
                    "entity_type": "temporal_relationship",
                    "entity_name": entity_name,
                    "transport_entity_type": entity_type,
                    "start_year": start_year,
                    "end_year": end_year,
                    "duration_years": end_year - start_year,
                    "transport_type": transport_type,
                    "spans_wall_period": start_year <= 1961 <= end_year
                },
                source_entities=[f"{entity_type}:{entity_name}"],
                temporal_context=f"Years {start_year}-{end_year}",
                chunk_type="relationship"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks

    async def _convert_line_operational_data(self) -> List[GraphTextChunk]:
        """Convert line operational data (frequency, capacity, routes) to searchable text"""
        
        query = """
        MATCH (l:Line)-[:IN_YEAR]->(y:Year)
        WHERE l.frequency IS NOT NULL OR l.capacity IS NOT NULL
        OPTIONAL MATCH (l)-[:SERVES]->(s:Station)
        WITH l, y, count(s) as station_count, 
             collect(DISTINCT s.east_west) as political_sides
        RETURN l.name as line_name, l.type as line_type,
               y.year as year, l.frequency as frequency, l.capacity as capacity,
               station_count, political_sides
        ORDER BY y.year, l.name
        LIMIT 1000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            line_name = record.get('line_name', 'Unknown Line')
            line_type = record.get('line_type', 'unknown')
            year = record.get('year', 'unknown')
            frequency = record.get('frequency')
            capacity = record.get('capacity')
            station_count = record.get('station_count', 0)
            political_sides = record.get('political_sides', [])
            
            content = f"In {year}, {line_type} line {line_name} provided public transport service"
            
            if frequency:
                content += f" with vehicles running every {frequency} minutes"
                
            if capacity:
                content += f" using vehicles with {capacity} passenger capacity"
                
            if station_count > 0:
                content += f" serving {station_count} stations along its route"
                
            # Analyze route political coverage
            clean_sides = [side for side in political_sides if side and side != 'unknown']
            if clean_sides:
                unique_sides = list(set(clean_sides))
                if len(unique_sides) > 1:
                    content += f" crossing between {' and '.join(unique_sides)} Berlin"
                else:
                    content += f" operating within {unique_sides[0]} Berlin"
                    
            content += ". This operational data reflects the service quality and accessibility of Berlin's public transport."
            
            chunk = GraphTextChunk(
                id=f"line_operational_{self.chunk_counter}",
                content=content,
                metadata={
                    "entity_type": "line_operational_data",
                    "line_name": line_name,
                    "line_type": line_type,
                    "year": year,
                    "frequency": frequency,
                    "capacity": capacity,
                    "station_count": station_count,
                    "crosses_political_boundary": len(set(clean_sides)) > 1,
                    "political_coverage": unique_sides if clean_sides else []
                },
                source_entities=[f"line:{line_name}"],
                temporal_context=f"Year {year}",
                chunk_type="operational_data"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks

    async def _convert_political_division_data(self) -> List[GraphTextChunk]:
        """Convert political division and cross-boundary data to searchable text"""
        
        query = """
        MATCH (s:Station)-[:IN_YEAR]->(y:Year)
        WHERE s.east_west IS NOT NULL AND s.east_west <> 'unknown'
        MATCH (s)<-[:SERVES]-(l:Line)
        WITH y.year as year, s.east_west as political_side, 
             count(DISTINCT s) as station_count,
             count(DISTINCT l) as line_count,
             collect(DISTINCT l.type) as transport_types
        ORDER BY year, political_side
        RETURN year, political_side, station_count, line_count, transport_types
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            year = record.get('year', 'unknown')
            political_side = record.get('political_side', 'unknown')
            station_count = record.get('station_count', 0)
            line_count = record.get('line_count', 0)
            transport_types = record.get('transport_types', [])
            
            content = f"In {year}, {political_side} Berlin had {station_count} public transport stations"
            content += f" served by {line_count} transit lines"
            
            if transport_types:
                clean_types = [t for t in transport_types if t]
                if clean_types:
                    content += f". Transport modes included: {', '.join(clean_types)}"
                    
            if year <= 1960:
                content += ". This was during the unified Berlin period with unrestricted movement"
            elif year >= 1961:
                content += ". This was during the divided Berlin period with restricted cross-boundary movement"
                if political_side == 'east':
                    content += " under East German administration"
                elif political_side == 'west':
                    content += " under West German administration"
                    
            content += "."
            
            chunk = GraphTextChunk(
                id=f"political_division_{self.chunk_counter}",
                content=content,
                metadata={
                    "entity_type": "political_division_data",
                    "year": year,
                    "political_side": political_side,
                    "station_count": station_count,
                    "line_count": line_count,
                    "transport_types": clean_types if transport_types else [],
                    "divided_period": year >= 1961,
                    "unified_period": year <= 1960
                },
                source_entities=[f"political_side:{political_side}"],
                temporal_context=f"Year {year}",
                spatial_context=f"{political_side} Berlin",
                chunk_type="political_data"
            )
            
            chunks.append(chunk)
            self.chunk_counter += 1
            
        return chunks 

    async def _convert_individual_station_properties(self) -> List[GraphTextChunk]:
        """Create individual chunks for each station property"""
        
        query = """
        MATCH (s:Station)-[:IN_YEAR]->(y:Year)
        OPTIONAL MATCH (s)-[:LOCATED_IN]->(area:HistoricalOrtsteil)
        OPTIONAL MATCH (area)-[:PART_OF]->(bezirk:Bezirk)
        RETURN s, y, area, bezirk
        LIMIT 20000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            station = record.get('s', {})
            year = record.get('y', {})
            area = record.get('area', {})
            bezirk = record.get('bezirk', {})
            
            station_id = station.get('stop_id', 'unknown')
            station_name = station.get('name', 'Unknown')
            year_val = year.get('year', 'unknown')
            
            # Create separate chunks for each property
            base_metadata = {
                "entity_type": "station_property",
                "station_id": station_id,
                "station_name": station_name,
                "year": year_val
            }
            
            # Station name chunk
            chunks.append(GraphTextChunk(
                id=f"station_name_{station_id}_{year_val}_{self.chunk_counter}",
                content=f"Station with ID {station_id} has the name '{station_name}' in {year_val}.",
                metadata={**base_metadata, "property": "name"},
                source_entities=[f"station:{station_id}"],
                temporal_context=f"Year {year_val}",
                chunk_type="property"
            ))
            self.chunk_counter += 1
            
            # Transport type chunk
            if station.get('type'):
                chunks.append(GraphTextChunk(
                    id=f"station_type_{station_id}_{year_val}_{self.chunk_counter}",
                    content=f"Station {station_name} (ID: {station_id}) is of transport type '{station.get('type')}' in {year_val}.",
                    metadata={**base_metadata, "property": "transport_type", "transport_type": station.get('type')},
                    source_entities=[f"station:{station_id}"],
                    temporal_context=f"Year {year_val}",
                    chunk_type="property"
                ))
                self.chunk_counter += 1
            
            # Political side chunk
            if station.get('east_west'):
                chunks.append(GraphTextChunk(
                    id=f"station_political_{station_id}_{year_val}_{self.chunk_counter}",
                    content=f"Station {station_name} (ID: {station_id}) was located on the {station.get('east_west')} side of Berlin in {year_val}.",
                    metadata={**base_metadata, "property": "political_side", "political_side": station.get('east_west')},
                    source_entities=[f"station:{station_id}"],
                    temporal_context=f"Year {year_val}",
                    spatial_context=f"{station.get('east_west')} Berlin",
                    chunk_type="property"
                ))
                self.chunk_counter += 1
            
            # Geographic coordinates chunk
            if station.get('latitude') and station.get('longitude'):
                chunks.append(GraphTextChunk(
                    id=f"station_coords_{station_id}_{year_val}_{self.chunk_counter}",
                    content=f"Station {station_name} (ID: {station_id}) is located at geographic coordinates {station.get('latitude'):.6f}, {station.get('longitude'):.6f} in {year_val}.",
                    metadata={**base_metadata, "property": "coordinates", "latitude": station.get('latitude'), "longitude": station.get('longitude')},
                    source_entities=[f"station:{station_id}"],
                    temporal_context=f"Year {year_val}",
                    chunk_type="property"
                ))
                self.chunk_counter += 1
        
        print(f"    Created {len(chunks)} individual station property chunks")
        return chunks
    
    async def _convert_individual_line_properties(self) -> List[GraphTextChunk]:
        """Create individual chunks for each line property"""
        
        query = """
        MATCH (l:Line)-[:IN_YEAR]->(y:Year)
        RETURN l, y
        LIMIT 15000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            line = record.get('l', {})
            year = record.get('y', {})
            
            line_id = line.get('line_id', 'unknown')
            line_name = line.get('name', 'Unknown')
            year_val = year.get('year', 'unknown')
            
            base_metadata = {
                "entity_type": "line_property",
                "line_id": line_id,
                "line_name": line_name,
                "year": year_val
            }
            
            # Line name chunk
            chunks.append(GraphTextChunk(
                id=f"line_name_{line_id}_{year_val}_{self.chunk_counter}",
                content=f"Transit line with ID {line_id} has the name '{line_name}' in {year_val}.",
                metadata={**base_metadata, "property": "name"},
                source_entities=[f"line:{line_id}"],
                temporal_context=f"Year {year_val}",
                chunk_type="property"
            ))
            self.chunk_counter += 1
            
            # Transport type chunk
            if line.get('type'):
                chunks.append(GraphTextChunk(
                    id=f"line_type_{line_id}_{year_val}_{self.chunk_counter}",
                    content=f"Transit line {line_name} (ID: {line_id}) operates as a {line.get('type')} service in {year_val}.",
                    metadata={**base_metadata, "property": "transport_type", "transport_type": line.get('type')},
                    source_entities=[f"line:{line_id}"],
                    temporal_context=f"Year {year_val}",
                    chunk_type="property"
                ))
                self.chunk_counter += 1
            
            # Frequency chunk
            if line.get('frequency'):
                chunks.append(GraphTextChunk(
                    id=f"line_frequency_{line_id}_{year_val}_{self.chunk_counter}",
                    content=f"Transit line {line_name} (ID: {line_id}) operates with a frequency of {line.get('frequency')} minutes between vehicles in {year_val}.",
                    metadata={**base_metadata, "property": "frequency", "frequency": line.get('frequency')},
                    source_entities=[f"line:{line_id}"],
                    temporal_context=f"Year {year_val}",
                    chunk_type="property"
                ))
                self.chunk_counter += 1
                
            # Capacity chunk
            if line.get('capacity'):
                chunks.append(GraphTextChunk(
                    id=f"line_capacity_{line_id}_{year_val}_{self.chunk_counter}",
                    content=f"Transit line {line_name} (ID: {line_id}) has vehicles with a passenger capacity of {line.get('capacity')} people in {year_val}.",
                    metadata={**base_metadata, "property": "capacity", "capacity": line.get('capacity')},
                    source_entities=[f"line:{line_id}"],
                    temporal_context=f"Year {year_val}",
                    chunk_type="property"
                ))
                self.chunk_counter += 1
            
            # Political side chunk
            if line.get('east_west'):
                chunks.append(GraphTextChunk(
                    id=f"line_political_{line_id}_{year_val}_{self.chunk_counter}",
                    content=f"Transit line {line_name} (ID: {line_id}) operated in {line.get('east_west')} Berlin in {year_val}.",
                    metadata={**base_metadata, "property": "political_side", "political_side": line.get('east_west')},
                    source_entities=[f"line:{line_id}"],
                    temporal_context=f"Year {year_val}",
                    spatial_context=f"{line.get('east_west')} Berlin",
                    chunk_type="property"
                ))
                self.chunk_counter += 1
                
        print(f"    Created {len(chunks)} individual line property chunks")
        return chunks
    
    async def _convert_individual_serves_relationships(self) -> List[GraphTextChunk]:
        """Create individual chunks for each SERVES relationship"""
        
        query = """
        MATCH (l:Line)-[:SERVES]->(s:Station)
        MATCH (l)-[:IN_YEAR]->(y:Year)
        MATCH (s)-[:IN_YEAR]->(y)
        RETURN l, s, y
        LIMIT 20000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            line = record.get('l', {})
            station = record.get('s', {})
            year = record.get('y', {})
            
            line_name = line.get('name', 'Unknown Line')
            station_name = station.get('name', 'Unknown Station')
            year_val = year.get('year', 'unknown')
            
            chunks.append(GraphTextChunk(
                id=f"serves_{line.get('line_id', 'unknown')}_{station.get('stop_id', 'unknown')}_{year_val}_{self.chunk_counter}",
                content=f"Transit line {line_name} serves station {station_name} in {year_val}.",
                metadata={
                    "entity_type": "relationship",
                    "relationship_type": "serves",
                    "line_id": line.get('line_id'),
                    "line_name": line_name,
                    "station_id": station.get('stop_id'),
                    "station_name": station_name,
                    "year": year_val,
                    "transport_type": line.get('type')
                },
                source_entities=[f"line:{line.get('line_id')}", f"station:{station.get('stop_id')}"],
                temporal_context=f"Year {year_val}",
                chunk_type="relationship"
            ))
            self.chunk_counter += 1
            
        print(f"    Created {len(chunks)} individual SERVES relationship chunks")
        return chunks
    
    async def _convert_individual_location_relationships(self) -> List[GraphTextChunk]:
        """Create individual chunks for each LOCATED_IN relationship"""
        
        query = """
        MATCH (s:Station)-[:LOCATED_IN]->(area:HistoricalOrtsteil)
        MATCH (s)-[:IN_YEAR]->(y:Year)
        OPTIONAL MATCH (area)-[:PART_OF]->(bezirk:Bezirk)
        RETURN s, area, bezirk, y
        LIMIT 15000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            station = record.get('s', {})
            area = record.get('area', {})
            bezirk = record.get('bezirk', {})
            year = record.get('y', {})
            
            station_name = station.get('name', 'Unknown Station')
            area_name = area.get('name', 'Unknown Area')
            year_val = year.get('year', 'unknown')
            
            # Station-Area relationship
            chunks.append(GraphTextChunk(
                id=f"located_in_{station.get('stop_id', 'unknown')}_{area.get('ortsteil_id', 'unknown')}_{year_val}_{self.chunk_counter}",
                content=f"Station {station_name} is located in the {area_name} neighborhood in {year_val}.",
                metadata={
                    "entity_type": "relationship",
                    "relationship_type": "located_in",
                    "station_id": station.get('stop_id'),
                    "station_name": station_name,
                    "area_id": area.get('ortsteil_id'),
                    "area_name": area_name,
                    "year": year_val
                },
                source_entities=[f"station:{station.get('stop_id')}", f"area:{area.get('ortsteil_id')}"],
                temporal_context=f"Year {year_val}",
                spatial_context=area_name,
                chunk_type="relationship"
            ))
            self.chunk_counter += 1
            
            # Area-District relationship if exists
            if bezirk and bezirk.get('name'):
                chunks.append(GraphTextChunk(
                    id=f"part_of_{area.get('ortsteil_id', 'unknown')}_{bezirk.get('bezirk_id', 'unknown')}_{year_val}_{self.chunk_counter}",
                    content=f"The {area_name} neighborhood is part of {bezirk.get('name')} district in {year_val}.",
                    metadata={
                        "entity_type": "relationship",
                        "relationship_type": "part_of",
                        "area_id": area.get('ortsteil_id'),
                        "area_name": area_name,
                        "district_id": bezirk.get('bezirk_id'),
                        "district_name": bezirk.get('name'),
                        "year": year_val
                    },
                    source_entities=[f"area:{area.get('ortsteil_id')}", f"district:{bezirk.get('bezirk_id')}"],
                    temporal_context=f"Year {year_val}",
                    spatial_context=bezirk.get('name'),
                    chunk_type="relationship"
                ))
                self.chunk_counter += 1
                
        print(f"    Created {len(chunks)} individual location relationship chunks")
        return chunks
        
    async def _convert_individual_temporal_relationships(self) -> List[GraphTextChunk]:
        """Create individual chunks for temporal relationships (IN_YEAR, HAS_SNAPSHOT)"""
        
        # IN_YEAR relationships
        query = """
        MATCH (entity)-[:IN_YEAR]->(y:Year)
        WHERE entity:Station OR entity:Line
        RETURN entity, y, labels(entity) as entity_labels
        LIMIT 25000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            entity = record.get('entity', {})
            year = record.get('y', {})
            labels = record.get('entity_labels', [])
            
            entity_type = "station" if "Station" in labels else "line"
            entity_name = entity.get('name', 'Unknown')
            entity_id = entity.get('stop_id' if entity_type == "station" else 'line_id', 'unknown')
            year_val = year.get('year', 'unknown')
            
            chunks.append(GraphTextChunk(
                id=f"in_year_{entity_type}_{entity_id}_{year_val}_{self.chunk_counter}",
                content=f"The {entity_type} {entity_name} existed and was operational in the year {year_val}.",
                metadata={
                    "entity_type": "relationship",
                    "relationship_type": "in_year",
                    f"{entity_type}_id": entity_id,
                    f"{entity_type}_name": entity_name,
                    "year": year_val,
                    "target_entity_type": entity_type
                },
                source_entities=[f"{entity_type}:{entity_id}", f"year:{year_val}"],
                temporal_context=f"Year {year_val}",
                chunk_type="relationship"
            ))
            self.chunk_counter += 1
            
        print(f"    Created {len(chunks)} individual temporal relationship chunks")
        return chunks
    
    async def _convert_individual_connection_relationships(self) -> List[GraphTextChunk]:
        """Create individual chunks for CONNECTS_TO relationships between stations"""
        
        query = """
        MATCH (s1:Station)-[:CONNECTS_TO]->(s2:Station)
        MATCH (s1)-[:IN_YEAR]->(y:Year)
        MATCH (s2)-[:IN_YEAR]->(y)
        RETURN s1, s2, y
        LIMIT 15000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            station1 = record.get('s1', {})
            station2 = record.get('s2', {})
            year = record.get('y', {})
            
            station1_name = station1.get('name', 'Unknown Station')
            station2_name = station2.get('name', 'Unknown Station')
            year_val = year.get('year', 'unknown')
            
            chunks.append(GraphTextChunk(
                id=f"connects_{station1.get('stop_id', 'unknown')}_{station2.get('stop_id', 'unknown')}_{year_val}_{self.chunk_counter}",
                content=f"Station {station1_name} has a direct connection to station {station2_name} in {year_val}.",
                metadata={
                    "entity_type": "relationship",
                    "relationship_type": "connects_to",
                    "station1_id": station1.get('stop_id'),
                    "station1_name": station1_name,
                    "station2_id": station2.get('stop_id'),
                    "station2_name": station2_name,
                    "year": year_val
                },
                source_entities=[f"station:{station1.get('stop_id')}", f"station:{station2.get('stop_id')}"],
                temporal_context=f"Year {year_val}",
                chunk_type="relationship"
            ))
            self.chunk_counter += 1
            
        print(f"    Created {len(chunks)} individual connection relationship chunks")
        return chunks
    
    async def _convert_all_relationships_to_triples(self) -> List[GraphTextChunk]:
        """Convert all relationships to structured triple format"""
        
        # Get all relationship types and create triples
        query = """
        MATCH (a)-[r]->(b)
        RETURN type(r) as rel_type, labels(a) as a_labels, labels(b) as b_labels, 
               a.name as a_name, b.name as b_name,
               id(a) as a_id, id(b) as b_id, r
        LIMIT 30000
        """
        
        result = await self.neo4j_client.execute_read_query(query)
        chunks = []
        
        for record in result.records:
            rel_type = record.get('rel_type', 'UNKNOWN')
            a_labels = record.get('a_labels', [])
            b_labels = record.get('b_labels', [])
            a_name = record.get('a_name', 'Unknown')
            b_name = record.get('b_name', 'Unknown')
            a_id = record.get('a_id', 'unknown')
            b_id = record.get('b_id', 'unknown')
            relationship = record.get('r', {})
            
            # Create structured triple
            triple_content = f"TRIPLE: ({a_name}:{'/'.join(a_labels)}) --[{rel_type}]--> ({b_name}:{'/'.join(b_labels)})"
            
            # Add relationship properties if any
            rel_props = []
            for key, value in relationship.items():
                if key not in ['type']:  # Skip internal properties
                    rel_props.append(f"{key}={value}")
            
            if rel_props:
                triple_content += f" WITH_PROPERTIES: {', '.join(rel_props)}"
            
            chunks.append(GraphTextChunk(
                id=f"triple_{rel_type}_{a_id}_{b_id}_{self.chunk_counter}",
                content=triple_content,
                metadata={
                    "entity_type": "triple",
                    "relationship_type": rel_type,
                    "subject_labels": a_labels,
                    "object_labels": b_labels,
                    "subject_name": a_name,
                    "object_name": b_name,
                    "subject_id": a_id,
                    "object_id": b_id
                },
                source_entities=[f"{a_labels[0].lower()}:{a_id}", f"{b_labels[0].lower()}:{b_id}"],
                chunk_type="triple"
            ))
            self.chunk_counter += 1
            
        print(f"    Created {len(chunks)} structured triple chunks")
        return chunks 