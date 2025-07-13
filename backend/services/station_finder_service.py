"""
Station Finder Service for finding closest stations to coordinates
Uses Neo4j spatial functions to calculate distances
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import math

from ..database.neo4j_client import Neo4jClient
from ..database.query_executor import QueryExecutor

logger = logging.getLogger(__name__)

@dataclass
class StationMatch:
    """A station match with distance and metadata"""
    station_id: str
    station_name: str
    transport_type: str
    latitude: float
    longitude: float
    distance_km: float
    political_side: str
    year: Optional[int] = None
    area_name: Optional[str] = None
    bezirk_name: Optional[str] = None

class StationFinderService:
    """Service for finding closest stations to coordinates"""
    
    def __init__(self):
        # Don't store client - create fresh ones to avoid event loop conflicts
        pass
        
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth
        using the Haversine formula
        
        Args:
            lat1, lon1: Latitude and longitude of first point
            lat2, lon2: Latitude and longitude of second point
            
        Returns:
            Distance in kilometers
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of Earth in kilometers
        r = 6371
        
        return c * r

    async def find_closest_stations(
        self,
        latitude: float,
        longitude: float,
        max_distance_km: float = 2.0,
        max_results: int = 10,
        year_filter: Optional[int] = None,
        transport_types: Optional[List[str]] = None
    ) -> List[StationMatch]:
        """
        Find the closest stations to given coordinates
        
        Args:
            latitude: Target latitude
            longitude: Target longitude
            max_distance_km: Maximum distance in kilometers
            max_results: Maximum number of results to return
            year_filter: Optional year to filter stations
            transport_types: Optional list of transport types to include
            
        Returns:
            List of StationMatch objects ordered by distance
        """
        
        # Create fresh client for this request to avoid event loop conflicts
        client = Neo4jClient()
        query_executor = QueryExecutor(client)
        
        try:
            await client.connect()
            
            # Build transport type filter
            transport_filter = ""
            if transport_types:
                types_str = "', '".join(transport_types)
                transport_filter = f"AND s.type IN ['{types_str}']"
            
            # Build year filter
            year_filter_clause = ""
            if year_filter:
                year_filter_clause = f"""
                AND (
                    s.year IS NULL OR 
                    EXISTS((s)-[:IN_YEAR]->(:Year {{year: {year_filter}}}))
                )
                """
            
            query = f"""
            MATCH (s:Station)
            WHERE s.latitude IS NOT NULL 
            AND s.longitude IS NOT NULL
            {transport_filter}
            {year_filter_clause}
            
            WITH s, 
                 point({{longitude: s.longitude, latitude: s.latitude}}) as station_point,
                 point({{longitude: {longitude}, latitude: {latitude}}}) as target_point
            
            WITH s, station_point, target_point,
                 point.distance(station_point, target_point) / 1000.0 as distance_km
            
            WHERE distance_km <= {max_distance_km}
            
            RETURN 
                s.stop_id as station_id,
                s.name as station_name,
                s.type as transport_type,
                s.latitude as latitude,
                s.longitude as longitude,
                distance_km,
                COALESCE(s.east_west, 'unknown') as political_side,
                s.year as year
            
            ORDER BY distance_km
            LIMIT {max_results}
            """
            
            result = await query_executor.execute_query_safely(query)
            
            if not result.success:
                logger.error(f"Station finder query failed: {result.error_message}")
                return []
            
            stations = []
            for record in result.records:
                # Use Haversine distance as fallback if Neo4j distance is not available
                calculated_distance = self._haversine_distance(
                    latitude, longitude,
                    record['latitude'], record['longitude']
                )
                
                station = StationMatch(
                    station_id=record['station_id'],
                    station_name=record['station_name'],
                    transport_type=record['transport_type'],
                    latitude=record['latitude'],
                    longitude=record['longitude'],
                    distance_km=record.get('distance_km', calculated_distance),
                    political_side=record['political_side'],
                    year=record.get('year'),
                )
                stations.append(station)
            
            return stations
            
        finally:
            await client.close()

    async def find_stations_in_area(
        self,
        center_latitude: float,
        center_longitude: float,
        radius_km: float,
        year_filter: Optional[int] = None
    ) -> List[StationMatch]:
        """
        Find all stations within a given radius
        
        Args:
            center_latitude: Center point latitude
            center_longitude: Center point longitude
            radius_km: Search radius in kilometers
            year_filter: Optional year filter
            
        Returns:
            List of stations within the area
        """
        return await self.find_closest_stations(
            center_latitude,
            center_longitude,
            max_distance_km=radius_km,
            max_results=100,  # Higher limit for area searches
            year_filter=year_filter
        )

    async def find_best_station_pairs(
        self,
        origin_lat: float,
        origin_lon: float,
        destination_lat: float,
        destination_lon: float,
        max_distance_km: float = 1.0,
        max_pairs: int = 5,
        year_filter: Optional[int] = None
    ) -> List[Tuple[StationMatch, StationMatch]]:
        """
        Find the best pairs of stations for route planning
        
        Args:
            origin_lat: Origin latitude
            origin_lon: Origin longitude
            destination_lat: Destination latitude
            destination_lon: Destination longitude
            max_distance_km: Maximum distance from address to station
            max_pairs: Maximum number of station pairs to return
            year_filter: Optional year filter
            
        Returns:
            List of (origin_station, destination_station) tuples
        """
        
        # Find stations near origin and destination
        origin_stations = await self.find_closest_stations(
            origin_lat, origin_lon,
            max_distance_km=max_distance_km,
            max_results=5,
            year_filter=year_filter
        )
        
        destination_stations = await self.find_closest_stations(
            destination_lat, destination_lon,
            max_distance_km=max_distance_km,
            max_results=5,
            year_filter=year_filter
        )
        
        if not origin_stations or not destination_stations:
            return []
        
        # Create all possible pairs and score them
        station_pairs = []
        
        for origin_station in origin_stations:
            for dest_station in destination_stations:
                # Skip if same station
                if origin_station.station_id == dest_station.station_id:
                    continue
                
                # Calculate total walking distance
                total_walking_distance = origin_station.distance_km + dest_station.distance_km
                
                # Score based on walking distance (lower is better)
                score = 1.0 / (1.0 + total_walking_distance)
                
                station_pairs.append((origin_station, dest_station, score))
        
        # Sort by score (descending) and return top pairs
        station_pairs.sort(key=lambda x: x[2], reverse=True)
        
        # Return tuples without score
        return [(pair[0], pair[1]) for pair in station_pairs[:max_pairs]]

    async def get_station_details(self, station_id: str, year_filter: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific station
        
        Args:
            station_id: Station identifier
            year_filter: Optional year filter
            
        Returns:
            Station details dictionary or None if not found
        """
        
        # Create fresh client for this request
        client = Neo4jClient()
        query_executor = QueryExecutor(client)
        
        try:
            await client.connect()
            
            year_filter_clause = ""
            if year_filter:
                year_filter_clause = f"""
                AND (
                    s.year IS NULL OR 
                    EXISTS((s)-[:IN_YEAR]->(:Year {{year: {year_filter}}}))
                )
                """
            
            query = f"""
            MATCH (s:Station {{stop_id: '{station_id}'}})
            WHERE 1=1 {year_filter_clause}
            
            OPTIONAL MATCH (s)-[:IN_AREA]->(area:AdministrativeArea)
            OPTIONAL MATCH (s)-[:IN_BEZIRK]->(bezirk:HistoricalBezirk)
            OPTIONAL MATCH (s)<-[:SERVES]-(line:Line)
            
            RETURN 
                s.stop_id as station_id,
                s.name as station_name,
                s.type as transport_type,
                s.latitude as latitude,
                s.longitude as longitude,
                s.east_west as political_side,
                s.year as year,
                collect(DISTINCT area.name) as areas,
                collect(DISTINCT bezirk.name) as bezirke,
                collect(DISTINCT line.name) as lines
            """
            
            result = await query_executor.execute_query_safely(query)
            
            if not result.success or not result.records:
                return None
            
            record = result.records[0]
            return {
                'station_id': record['station_id'],
                'station_name': record['station_name'],
                'transport_type': record['transport_type'],
                'latitude': record['latitude'],
                'longitude': record['longitude'],
                'political_side': record['political_side'],
                'year': record['year'],
                'areas': [area for area in record['areas'] if area],
                'bezirke': [bezirk for bezirk in record['bezirke'] if bezirk],
                'lines': [line for line in record['lines'] if line]
            }
            
        finally:
            await client.close()

def get_station_finder_service() -> StationFinderService:
    """Get the station finder service instance"""
    return StationFinderService() 