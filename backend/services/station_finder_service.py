"""
Station Finder Service for finding closest stations to coordinates
Uses Neo4j spatial functions to calculate distances
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import math

from ..database.neo4j_client import neo4j_client
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
        self.query_executor = QueryExecutor(neo4j_client)
        
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
        
        # Radius of earth in kilometers
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
            max_distance_km: Maximum distance to search (default 2km)
            max_results: Maximum number of results to return
            year_filter: Optional year filter (e.g., 1971)
            transport_types: Optional list of transport types to filter
            
        Returns:
            List of StationMatch objects sorted by distance
        """
        
        # Build year filter clause
        year_clause = ""
        if year_filter:
            year_clause = f"AND EXISTS((s)-[:IN_YEAR]->(:Year {{year: {year_filter}}}))"
        
        # Build transport type filter clause
        transport_clause = ""
        if transport_types:
            transport_types_str = "', '".join(transport_types)
            transport_clause = f"AND s.type IN ['{transport_types_str}']"
        
        # Query to find stations with approximate distance filtering
        # Using rough lat/lon bounds first for efficiency
        lat_range = max_distance_km / 111.0  # Approximate km to degrees
        lon_range = max_distance_km / (111.0 * math.cos(math.radians(latitude)))
        
        query = f"""
        MATCH (s:Station)
        WHERE s.latitude > {latitude - lat_range} 
          AND s.latitude < {latitude + lat_range}
          AND s.longitude > {longitude - lon_range}
          AND s.longitude < {longitude + lon_range}
          AND s.latitude IS NOT NULL 
          AND s.longitude IS NOT NULL
          {year_clause}
          {transport_clause}
        
        OPTIONAL MATCH (s)-[:IN_YEAR]->(y:Year)
        OPTIONAL MATCH (s)-[:LOCATED_IN]->(area:HistoricalOrtsteil)
        OPTIONAL MATCH (area)-[:PART_OF]->(bezirk:HistoricalBezirk)
        
        RETURN 
            s.stop_id as station_id,
            s.name as station_name,
            s.type as transport_type,
            s.latitude as latitude,
            s.longitude as longitude,
            s.east_west as political_side,
            y.year as year,
            area.name as area_name,
            bezirk.name as bezirk_name
        
        ORDER BY 
            (s.latitude - {latitude}) * (s.latitude - {latitude}) + 
            (s.longitude - {longitude}) * (s.longitude - {longitude})
        LIMIT {max_results * 3}
        """
        
        try:
            result = await self.query_executor.execute_query_safely(query)
            
            if not result.success:
                logger.error(f"Station finder query failed: {result.error_message}")
                return []
            
            # Calculate exact distances and filter
            station_matches = []
            
            for record in result.records:
                station_lat = record.get('latitude')
                station_lon = record.get('longitude')
                
                if station_lat is None or station_lon is None:
                    continue
                
                # Calculate exact distance
                distance = self._haversine_distance(
                    latitude, longitude, 
                    station_lat, station_lon
                )
                
                # Filter by max distance
                if distance > max_distance_km:
                    continue
                
                station_match = StationMatch(
                    station_id=record.get('station_id', ''),
                    station_name=record.get('station_name', ''),
                    transport_type=record.get('transport_type', ''),
                    latitude=station_lat,
                    longitude=station_lon,
                    distance_km=distance,
                    political_side=record.get('political_side', ''),
                    year=record.get('year'),
                    area_name=record.get('area_name'),
                    bezirk_name=record.get('bezirk_name')
                )
                
                station_matches.append(station_match)
            
            # Sort by distance and return top results
            station_matches.sort(key=lambda x: x.distance_km)
            return station_matches[:max_results]
            
        except Exception as e:
            logger.error(f"Error finding closest stations: {str(e)}")
            return []
    
    async def find_stations_in_area(
        self,
        center_latitude: float,
        center_longitude: float,
        radius_km: float,
        year_filter: Optional[int] = None
    ) -> List[StationMatch]:
        """
        Find all stations within a circular area
        
        Args:
            center_latitude: Center latitude
            center_longitude: Center longitude
            radius_km: Radius in kilometers
            year_filter: Optional year filter
            
        Returns:
            List of all stations within the area
        """
        return await self.find_closest_stations(
            center_latitude,
            center_longitude,
            max_distance_km=radius_km,
            max_results=100,  # Get all stations in area
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
            station_id: Station ID to lookup
            year_filter: Optional year filter
            
        Returns:
            Dictionary with station details or None if not found
        """
        year_clause = ""
        if year_filter:
            year_clause = f"AND EXISTS((s)-[:IN_YEAR]->(:Year {{year: {year_filter}}}))"
        
        query = f"""
        MATCH (s:Station {{stop_id: '{station_id}'}})
        WHERE s.latitude IS NOT NULL AND s.longitude IS NOT NULL
        {year_clause}
        
        OPTIONAL MATCH (s)-[:IN_YEAR]->(y:Year)
        OPTIONAL MATCH (s)-[:LOCATED_IN]->(area:HistoricalOrtsteil)
        OPTIONAL MATCH (area)-[:PART_OF]->(bezirk:HistoricalBezirk)
        OPTIONAL MATCH (s)<-[:SERVES]-(l:Line)
        
        RETURN 
            s.stop_id as station_id,
            s.name as station_name,
            s.type as transport_type,
            s.latitude as latitude,
            s.longitude as longitude,
            s.east_west as political_side,
            collect(DISTINCT y.year) as years,
            area.name as area_name,
            bezirk.name as bezirk_name,
            collect(DISTINCT l.name) as lines
        
        LIMIT 1
        """
        
        try:
            result = await self.query_executor.execute_query_safely(query)
            
            if not result.success or not result.records:
                return None
            
            record = result.records[0]
            
            return {
                'station_id': record.get('station_id'),
                'station_name': record.get('station_name'),
                'transport_type': record.get('transport_type'),
                'latitude': record.get('latitude'),
                'longitude': record.get('longitude'),
                'political_side': record.get('political_side'),
                'years': record.get('years', []),
                'area_name': record.get('area_name'),
                'bezirk_name': record.get('bezirk_name'),
                'lines': record.get('lines', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting station details for {station_id}: {str(e)}")
            return None

# Global instance
_station_finder_service = None

def get_station_finder_service() -> StationFinderService:
    """Get the singleton station finder service instance"""
    global _station_finder_service
    if _station_finder_service is None:
        _station_finder_service = StationFinderService()
    return _station_finder_service 