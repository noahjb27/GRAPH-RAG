"""
Enhanced Route Planning Service
Combines geocoding, closest station finding, and shortest path calculation
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import asyncio

from .geocoding_service import GeocodingService, GeocodeResult, get_geocoding_service
from .station_finder_service import StationFinderService, StationMatch, get_station_finder_service
from ..database.neo4j_client import neo4j_client
from ..database.query_executor import QueryExecutor

logger = logging.getLogger(__name__)

@dataclass
class RouteStep:
    """A single step in a route"""
    step_type: str  # 'walk', 'transit', 'transfer'
    description: str
    from_location: str
    to_location: str
    distance_km: Optional[float] = None
    estimated_time_minutes: Optional[float] = None
    transport_type: Optional[str] = None
    line_name: Optional[str] = None
    distance_meters: Optional[float] = None  # For walking connections

@dataclass
class RouteOption:
    """A complete route option from origin to destination"""
    origin_address: str
    destination_address: str
    origin_coordinates: Tuple[float, float]
    destination_coordinates: Tuple[float, float]
    origin_station: StationMatch
    destination_station: StationMatch
    steps: List[RouteStep]
    total_distance_km: float
    total_walking_distance_km: float
    estimated_total_time_minutes: float
    path_description: str
    year: Optional[int] = None
    confidence_score: float = 0.0

@dataclass
class RouteRequest:
    """Request for route planning"""
    origin_address: str
    destination_address: str
    year: Optional[int] = None
    transport_preferences: Optional[List[str]] = None
    max_walking_distance_km: float = 1.0
    max_route_options: int = 3

@dataclass
class RouteResponse:
    """Response from route planning"""
    request: RouteRequest
    route_options: List[RouteOption]
    geocoding_results: Dict[str, GeocodeResult]
    success: bool
    error_message: Optional[str] = None
    processing_time_seconds: float = 0.0

class RoutePlanningService:
    """Enhanced route planning service"""
    
    def __init__(self):
        self.geocoding_service = get_geocoding_service()
        self.station_finder_service = get_station_finder_service()
        self.query_executor = QueryExecutor(neo4j_client)
        
    async def plan_route(self, route_request: RouteRequest) -> RouteResponse:
        """
        Plan a route from origin to destination address
        
        Args:
            route_request: Route planning request
            
        Returns:
            RouteResponse with route options and metadata
        """
        
        import time
        start_time = time.time()
        
        try:
            # Step 1: Geocode both addresses
            geocoding_results = await self._geocode_addresses(route_request)
            
            if not geocoding_results['origin'].found or not geocoding_results['destination'].found:
                return RouteResponse(
                    request=route_request,
                    route_options=[],
                    geocoding_results=geocoding_results,
                    success=False,
                    error_message=f"Could not geocode addresses: Origin found={geocoding_results['origin'].found}, Destination found={geocoding_results['destination'].found}",
                    processing_time_seconds=time.time() - start_time
                )
            
            # Step 2: Find closest stations
            origin_coords = (geocoding_results['origin'].latitude, geocoding_results['origin'].longitude)
            dest_coords = (geocoding_results['destination'].latitude, geocoding_results['destination'].longitude)
            
            station_pairs = await self.station_finder_service.find_best_station_pairs(
                origin_coords[0], origin_coords[1],
                dest_coords[0], dest_coords[1],
                max_distance_km=route_request.max_walking_distance_km,
                max_pairs=route_request.max_route_options * 2,
                year_filter=route_request.year
            )
            
            if not station_pairs:
                return RouteResponse(
                    request=route_request,
                    route_options=[],
                    geocoding_results=geocoding_results,
                    success=False,
                    error_message="No nearby stations found within walking distance",
                    processing_time_seconds=time.time() - start_time
                )
            
            # Step 3: Calculate routes for each station pair
            route_options = []
            failed_attempts = 0
            
            for origin_station, dest_station in station_pairs:
                try:
                    route_option = await self._calculate_route_option(
                        route_request,
                        geocoding_results,
                        origin_station,
                        dest_station
                    )
                    
                    if route_option:
                        route_options.append(route_option)
                    else:
                        failed_attempts += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to calculate route option: {str(e)}")
                    failed_attempts += 1
                    continue
            
            # Step 4: Sort by confidence score and return best options
            route_options.sort(key=lambda x: x.confidence_score, reverse=True)
            route_options = route_options[:route_request.max_route_options]
            
            # If no routes found, provide detailed feedback
            if not route_options:
                error_message = f"No transit connections found between stations. "
                error_message += f"Tried {len(station_pairs)} station pairs but found no viable routes. "
                
                if route_request.year and route_request.year < 1989:
                    error_message += "This may be due to limited connections in the divided Berlin transport network. "
                    if any(station.political_side == 'west' for station, _ in station_pairs) and \
                       any(station.political_side == 'east' for _, station in station_pairs):
                        error_message += "Cross-sector travel between East and West Berlin was heavily restricted during this period."
                
                return RouteResponse(
                    request=route_request,
                    route_options=[],
                    geocoding_results=geocoding_results,
                    success=False,
                    error_message=error_message,
                    processing_time_seconds=time.time() - start_time
                )
            
            return RouteResponse(
                request=route_request,
                route_options=route_options,
                geocoding_results=geocoding_results,
                success=True,
                processing_time_seconds=time.time() - start_time
            )
            
        except Exception as e:
            logger.error(f"Route planning failed: {str(e)}")
            return RouteResponse(
                request=route_request,
                route_options=[],
                geocoding_results={},
                success=False,
                error_message=f"Route planning failed: {str(e)}",
                processing_time_seconds=time.time() - start_time
            )
    
    async def _geocode_addresses(self, route_request: RouteRequest) -> Dict[str, GeocodeResult]:
        """Geocode origin and destination addresses"""
        
        async with self.geocoding_service:
            results = await self.geocoding_service.geocode_multiple_addresses([
                route_request.origin_address,
                route_request.destination_address
            ])
            
            return {
                'origin': results[0],
                'destination': results[1]
            }
    
    async def _calculate_route_option(
        self,
        route_request: RouteRequest,
        geocoding_results: Dict[str, GeocodeResult],
        origin_station: StationMatch,
        dest_station: StationMatch
    ) -> Optional[RouteOption]:
        """Calculate a single route option"""
        
        # Step 1: Find path between stations
        transit_path = await self._find_transit_path(
            origin_station, dest_station, route_request.year
        )
        
        if not transit_path:
            return None
        
        # Step 2: Build route steps
        steps = []
        
        # Walking step from origin to station
        origin_geocode = geocoding_results['origin']
        walk_to_station = RouteStep(
            step_type='walk',
            description=f"Walk from {origin_geocode.display_name} to {origin_station.station_name}",
            from_location=route_request.origin_address,
            to_location=origin_station.station_name,
            distance_km=origin_station.distance_km,
            estimated_time_minutes=origin_station.distance_km * 12,  # 12 minutes per km walking
            transport_type=None,
            line_name=None,
            distance_meters=origin_station.distance_km * 1000  # Convert km to meters
        )
        steps.append(walk_to_station)
        
        # Transit steps
        for transit_step in transit_path['steps']:
            steps.append(RouteStep(
                step_type='transit',
                description=transit_step['description'],
                from_location=transit_step['from_station'],
                to_location=transit_step['to_station'],
                distance_km=transit_step.get('distance_km'),
                estimated_time_minutes=transit_step.get('travel_time_minutes'),
                transport_type=transit_step.get('transport_type'),
                line_name=transit_step.get('line_name'),
                distance_meters=transit_step.get('distance_meters')
            ))
        
        # Walking step from station to destination
        dest_geocode = geocoding_results['destination']
        walk_from_station = RouteStep(
            step_type='walk',
            description=f"Walk from {dest_station.station_name} to {dest_geocode.display_name}",
            from_location=dest_station.station_name,
            to_location=route_request.destination_address,
            distance_km=dest_station.distance_km,
            estimated_time_minutes=dest_station.distance_km * 12,  # 12 minutes per km walking
            transport_type=None,
            line_name=None,
            distance_meters=dest_station.distance_km * 1000  # Convert km to meters
        )
        steps.append(walk_from_station)
        
        # Step 3: Calculate totals
        total_walking_distance = origin_station.distance_km + dest_station.distance_km
        total_distance = total_walking_distance + transit_path['total_distance_km']
        total_time = (total_walking_distance * 12) + transit_path['total_time_minutes']
        
        # Step 4: Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            origin_station, dest_station, transit_path, total_walking_distance
        )
        
        return RouteOption(
            origin_address=route_request.origin_address,
            destination_address=route_request.destination_address,
            origin_coordinates=(origin_geocode.latitude, origin_geocode.longitude),
            destination_coordinates=(dest_geocode.latitude, dest_geocode.longitude),
            origin_station=origin_station,
            destination_station=dest_station,
            steps=steps,
            total_distance_km=total_distance,
            total_walking_distance_km=total_walking_distance,
            estimated_total_time_minutes=total_time,
            path_description=transit_path['description'],
            year=route_request.year,
            confidence_score=confidence_score
        )
    
    async def _find_transit_path(
        self,
        origin_station: StationMatch,
        dest_station: StationMatch,
        year_filter: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Find transit path between two stations"""
        
        # Build year filter
        year_clause = ""
        if year_filter:
            year_clause = f"""
            AND ALL(node IN nodes(path) WHERE 
                NOT EXISTS(node.year) OR 
                EXISTS((node)-[:IN_YEAR]->(:Year {{year: {year_filter}}}))
            )
            """
        
        # Try multiple path finding strategies
        
        # Strategy 1: Direct connections + walking connections
        mixed_query = f"""
        MATCH (origin:Station {{stop_id: '{origin_station.station_id}'}})
        MATCH (dest:Station {{stop_id: '{dest_station.station_id}'}})
        
        MATCH path = shortestPath((origin)-[:CONNECTS_TO|WALKING_CONNECTION*1..4]-(dest))
        WHERE origin <> dest {year_clause}
        
        WITH path, length(path) as path_length,
             [rel IN relationships(path) | type(rel)] as rel_types,
             reduce(walkTime = 0, rel IN relationships(path) | 
                walkTime + CASE WHEN type(rel) = 'WALKING_CONNECTION' 
                THEN COALESCE(rel.walking_time_minutes, 2.5) ELSE 0 END) as total_walk_time
        ORDER BY path_length, total_walk_time
        LIMIT 3
        
        RETURN 
            path,
            path_length,
            rel_types,
            total_walk_time,
            [node IN nodes(path) | {{
                name: COALESCE(node.name, node.line_id, 'unknown'),
                type: labels(node)[0],
                id: COALESCE(node.stop_id, node.line_id, id(node)),
                transport_type: node.type,
                latitude: node.latitude,
                longitude: node.longitude
            }}] as nodes,
            [rel IN relationships(path) | {{
                type: type(rel),
                properties: properties(rel)
            }}] as relationships
        """
        
        # If no direct path, try through shared lines
        line_query = f"""
        MATCH (origin:Station {{stop_id: '{origin_station.station_id}'}})
        MATCH (dest:Station {{stop_id: '{dest_station.station_id}'}})
        
        MATCH (origin)<-[:SERVES]-(line:Line)-[:SERVES]->(dest)
        WHERE origin <> dest {year_clause.replace('node', 'line') if year_clause else ''}
        
        RETURN 
            line.name as line_name,
            line.type as line_type,
            line.line_id as line_id,
            1 as path_length
        LIMIT 1
        """
        
        # Try mixed connections first (direct + walking)
        query = mixed_query
        
        try:
            result = await self.query_executor.execute_query_safely(query)
            
            if not result.success or not result.records:
                # Try the line-based query if direct connections failed
                result = await self.query_executor.execute_query_safely(line_query)
                
                if not result.success or not result.records:
                    return None
                    
                # Handle line-based result
                line_record = result.records[0]
                line_name = line_record['line_name']
                line_type = line_record['line_type']
                
                steps = [{
                    'description': f"Take {line_type} line {line_name} from {origin_station.station_name} to {dest_station.station_name}",
                    'from_station': origin_station.station_name,
                    'to_station': dest_station.station_name,
                    'transport_type': line_type,
                    'line_name': line_name,
                    'travel_time_minutes': self._estimate_travel_time_by_type(line_type)
                }]
                
                return {
                    'steps': steps,
                    'total_distance_km': 0.0,  # Unknown distance
                    'total_time_minutes': steps[0]['travel_time_minutes'],
                    'description': f"Direct {line_type} connection via {line_name}",
                    'path_length': 1
                }
            
            # Use the first (shortest) path from mixed connections
            path_record = result.records[0]
            nodes = path_record['nodes']
            relationships = path_record['relationships']
            rel_types = path_record.get('rel_types', [])
            total_walk_time = path_record.get('total_walk_time', 0)
            
            # Build transit steps with walking awareness
            steps = []
            total_distance = 0.0
            total_time = total_walk_time  # Start with walking time
            
            # Process each connection in the path
            for i in range(len(relationships)):
                current_node = nodes[i]
                next_node = nodes[i + 1]
                relationship = relationships[i]
                rel_type = relationship['type']
                
                if rel_type == 'WALKING_CONNECTION':
                    # Walking connection
                    distance_m = relationship['properties'].get('distance_meters', 0)
                    walk_time = relationship['properties'].get('walking_time_minutes', 2.5)
                    
                    step_description = f"Walk {distance_m:.0f}m from {current_node['name']} to {next_node['name']}"
                    
                    steps.append({
                        'description': step_description,
                        'from_station': current_node['name'],
                        'to_station': next_node['name'],
                        'transport_type': 'walking',
                        'travel_time_minutes': walk_time,
                        'distance_meters': distance_m
                    })
                    
                else:
                    # Transit connection
                    step_description = f"Take transit from {current_node['name']} to {next_node['name']}"
                    
                    # Estimate travel time based on transport type
                    travel_time = self._estimate_travel_time(current_node, next_node)
                    
                    steps.append({
                        'description': step_description,
                        'from_station': current_node['name'],
                        'to_station': next_node['name'],
                        'transport_type': current_node.get('transport_type', 'transit'),
                        'travel_time_minutes': travel_time
                    })
                    
                    total_time += travel_time
            
            # Generate description based on connection types
            has_walking = 'WALKING_CONNECTION' in rel_types
            connection_count = len(steps)
            
            if has_walking:
                description = f"Route with {connection_count} connections including walking transfers"
            else:
                description = f"Direct transit route with {connection_count} connections"
            
            return {
                'steps': steps,
                'total_distance_km': total_distance,
                'total_time_minutes': total_time,
                'description': description,
                'path_length': path_record['path_length'],
                'includes_walking': has_walking,
                'total_walking_time': total_walk_time
            }
            
        except Exception as e:
            logger.error(f"Error finding transit path: {str(e)}")
            return None
    
    def _estimate_travel_time(self, from_node: Dict, to_node: Dict) -> float:
        """Estimate travel time between two nodes"""
        
        # Simple heuristic based on transport type
        transport_type = from_node.get('transport_type', 'unknown')
        return self._estimate_travel_time_by_type(transport_type)
    
    def _estimate_travel_time_by_type(self, transport_type: str) -> float:
        """Estimate travel time based on transport type"""
        
        if transport_type in ['u-bahn', 's-bahn']:
            return 15.0  # 15 minutes for longer distance connections
        elif transport_type in ['tram']:
            return 12.0  # 12 minutes for tram connections
        elif transport_type in ['bus', 'autobus', 'omnibus']:
            return 20.0  # 20 minutes for bus connections
        else:
            return 15.0  # Default
    
    def _calculate_confidence_score(
        self,
        origin_station: StationMatch,
        dest_station: StationMatch,
        transit_path: Dict[str, Any],
        total_walking_distance: float
    ) -> float:
        """Calculate confidence score for a route option"""
        
        score = 1.0
        
        # Penalize longer walking distances
        if total_walking_distance > 0.5:
            score *= (0.5 / total_walking_distance)
        
        # Penalize longer transit paths
        path_length = transit_path.get('path_length', 1)
        if path_length > 2:
            score *= (2.0 / path_length)
        
        # Boost score for better transport types
        if origin_station.transport_type in ['u-bahn', 's-bahn']:
            score *= 1.2
        elif origin_station.transport_type in ['tram']:
            score *= 1.1
        
        # Ensure score is between 0 and 1
        return min(1.0, max(0.0, score))
    
    async def get_route_summary(self, route_option: RouteOption) -> str:
        """Generate a human-readable summary of a route option"""
        
        summary_parts = []
        
        # Origin information
        summary_parts.append(f"Starting from {route_option.origin_address}")
        
        # Walking to station
        summary_parts.append(f"Walk {route_option.origin_station.distance_km:.1f}km to {route_option.origin_station.station_name} ({route_option.origin_station.transport_type})")
        
        # Transit description
        if route_option.path_description:
            summary_parts.append(route_option.path_description)
        
        # Walking from station
        summary_parts.append(f"Walk {route_option.destination_station.distance_km:.1f}km from {route_option.destination_station.station_name} to {route_option.destination_address}")
        
        # Total summary
        summary_parts.append(f"Total: {route_option.total_distance_km:.1f}km, ~{route_option.estimated_total_time_minutes:.0f} minutes")
        
        return " → ".join(summary_parts)

# Global instance
_route_planning_service = None

def get_route_planning_service() -> RoutePlanningService:
    """Get the singleton route planning service instance"""
    global _route_planning_service
    if _route_planning_service is None:
        _route_planning_service = RoutePlanningService()
    return _route_planning_service 