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
from ..database.neo4j_client import Neo4jClient
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
        # Don't store query_executor - create fresh clients to avoid event loop conflicts
        
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
            
            if route_options:
                return RouteResponse(
                    request=route_request,
                    route_options=route_options,
                    geocoding_results=geocoding_results,
                    success=True,
                    processing_time_seconds=time.time() - start_time
                )
            else:
                # No viable routes found
                error_msg = f"No transit connections found between stations. Tried {len(station_pairs)} station pairs but found no viable routes"
                
                # Add historical context if cross-sector routing in divided Berlin
                if route_request.year and route_request.year <= 1989:
                    error_msg += ". This may be due to limited connections in the divided Berlin transport network"
                    
                    # Check if trying to route between East and West
                    origin_political = getattr(station_pairs[0][0], 'political_side', '') if station_pairs else ''
                    dest_political = getattr(station_pairs[0][1], 'political_side', '') if station_pairs else ''
                    
                    if origin_political and dest_political and origin_political != dest_political:
                        error_msg += ". Cross-sector travel between East and West Berlin was heavily restricted during this period"
                
                return RouteResponse(
                    request=route_request,
                    route_options=[],
                    geocoding_results=geocoding_results,
                    success=False,
                    error_message=error_msg,
                    processing_time_seconds=time.time() - start_time
                )
                
        except Exception as e:
            logger.error(f"Route planning error: {str(e)}")
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
        """Calculate a specific route option using given station pair"""
        
        # Step 1: Find transit path between stations
        transit_path = await self._find_transit_path(
            origin_station, dest_station, route_request.year
        )
        
        if not transit_path:
            return None
        
        # Step 2: Build route steps
        steps = []
        origin_geocode = geocoding_results['origin']
        
        # Walking step from origin to station
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
                distance_km=None,  # Will be calculated if needed
                estimated_time_minutes=transit_step['travel_time_minutes'],
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
        
        # Create fresh client for this request to avoid event loop conflicts
        client = Neo4jClient()
        query_executor = QueryExecutor(client)
        
        try:
            await client.connect()
            
            # Strategy 1: Try simple direct connection first (CONNECTS_TO only)
            simple_query = f"""
            MATCH (origin:Station {{stop_id: '{origin_station.station_id}'}})
            MATCH (dest:Station {{stop_id: '{dest_station.station_id}'}})
            
            MATCH path = shortestPath((origin)-[:CONNECTS_TO*1..3]-(dest))
            WHERE origin <> dest
            
            RETURN 
                path,
                length(path) as path_length,
                [node IN nodes(path) | {{
                    name: node.name,
                    transport_type: node.type,
                    stop_id: node.stop_id
                }}] as nodes
            LIMIT 1
            """
            
            result = await query_executor.execute_query_safely(simple_query)
            
            if result.success and result.records:
                # Process simple path
                path_record = result.records[0]
                nodes = path_record['nodes']
                path_length = path_record['path_length']
                
                if len(nodes) >= 2:
                    # Create transit step
                    from_node = nodes[0]
                    to_node = nodes[-1]
                    
                    steps = [{
                        'description': f"Take {from_node['transport_type']} from {from_node['name']} to {to_node['name']}",
                        'from_station': from_node['name'],
                        'to_station': to_node['name'],
                        'transport_type': from_node['transport_type'],
                        'travel_time_minutes': self._estimate_travel_time_by_type(from_node['transport_type']) * path_length
                    }]
                    
                    return {
                        'steps': steps,
                        'total_distance_km': 0.0,
                        'total_time_minutes': steps[0]['travel_time_minutes'],
                        'description': f"Direct {from_node['transport_type']} connection",
                        'path_length': path_length
                    }
            
            # Strategy 2: Try walking connections separately
            walking_query = f"""
            MATCH (origin:Station {{stop_id: '{origin_station.station_id}'}})
            MATCH (dest:Station {{stop_id: '{dest_station.station_id}'}})
            
            MATCH path = shortestPath((origin)-[:WALKING_CONNECTION]-(dest))
            WHERE origin <> dest
            
            RETURN 
                path,
                [node IN nodes(path) | {{
                    name: node.name,
                    transport_type: node.type,
                    stop_id: node.stop_id
                }}] as nodes,
                [rel IN relationships(path) | {{
                    distance_meters: rel.distance_meters,
                    walking_time_minutes: rel.walking_time_minutes
                }}] as walking_rels
            LIMIT 1
            """
            
            walking_result = await query_executor.execute_query_safely(walking_query)
            
            if walking_result.success and walking_result.records:
                # Process walking connection
                walk_record = walking_result.records[0]
                nodes = walk_record['nodes']
                walking_rels = walk_record['walking_rels']
                
                if len(nodes) >= 2 and walking_rels:
                    from_node = nodes[0]
                    to_node = nodes[1]
                    walk_rel = walking_rels[0]
                    
                    distance_m = walk_rel.get('distance_meters', 50)
                    walk_time = walk_rel.get('walking_time_minutes', 1.0)
                    
                    steps = [{
                        'description': f"Walk {distance_m:.0f}m from {from_node['name']} to {to_node['name']}",
                        'from_station': from_node['name'],
                        'to_station': to_node['name'],
                        'transport_type': 'walking',
                        'travel_time_minutes': walk_time,
                        'distance_meters': distance_m
                    }]
                    
                    return {
                        'steps': steps,
                        'total_distance_km': distance_m / 1000.0,
                        'total_time_minutes': walk_time,
                        'description': f"Walking connection ({distance_m:.0f}m)",
                        'path_length': 1
                    }
            
            # Strategy 3: Try shared line connection
            line_query = f"""
            MATCH (origin:Station {{stop_id: '{origin_station.station_id}'}})
            MATCH (dest:Station {{stop_id: '{dest_station.station_id}'}})
            
            MATCH (origin)<-[:SERVES]-(line:Line)-[:SERVES]->(dest)
            WHERE origin <> dest
            
            RETURN 
                line.name as line_name,
                line.type as line_type
            LIMIT 1
            """
            
            line_result = await query_executor.execute_query_safely(line_query)
            
            if line_result.success and line_result.records:
                # Handle line-based result
                line_record = line_result.records[0]
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
                    'total_distance_km': 0.0,
                    'total_time_minutes': steps[0]['travel_time_minutes'],
                    'description': f"Direct {line_type} connection via {line_name}",
                    'path_length': 1
                }
            
            # Strategy 4: Try multi-hop with walking (simplified)
            multihop_query = f"""
            MATCH (origin:Station {{stop_id: '{origin_station.station_id}'}})
            MATCH (dest:Station {{stop_id: '{dest_station.station_id}'}})
            
            MATCH (origin)-[:WALKING_CONNECTION]-(intermediate:Station)-[:CONNECTS_TO]-(dest)
            WHERE origin <> dest AND origin <> intermediate AND intermediate <> dest
            
            RETURN 
                intermediate.name as intermediate_name,
                intermediate.type as intermediate_type,
                intermediate.stop_id as intermediate_id
            LIMIT 1
            """
            
            multihop_result = await query_executor.execute_query_safely(multihop_query)
            
            if multihop_result.success and multihop_result.records:
                # Process multi-hop connection
                hop_record = multihop_result.records[0]
                intermediate_name = hop_record['intermediate_name']
                intermediate_type = hop_record['intermediate_type']
                
                steps = [
                    {
                        'description': f"Walk from {origin_station.station_name} to {intermediate_name}",
                        'from_station': origin_station.station_name,
                        'to_station': intermediate_name,
                        'transport_type': 'walking',
                        'travel_time_minutes': 2.0,
                        'distance_meters': 100
                    },
                    {
                        'description': f"Take {intermediate_type} from {intermediate_name} to {dest_station.station_name}",
                        'from_station': intermediate_name,
                        'to_station': dest_station.station_name,
                        'transport_type': intermediate_type,
                        'travel_time_minutes': self._estimate_travel_time_by_type(intermediate_type)
                    }
                ]
                
                total_time = sum(step['travel_time_minutes'] for step in steps)
                
                return {
                    'steps': steps,
                    'total_distance_km': 0.1,  # Estimate
                    'total_time_minutes': total_time,
                    'description': f"Route via {intermediate_name}",
                    'path_length': 2
                }
            
            # No path found
            return None
            
        finally:
            await client.close()
    
    def _estimate_travel_time(self, from_node: Dict, to_node: Dict) -> float:
        """Estimate travel time between two nodes"""
        # Simple estimation based on transport type
        transport_type = from_node.get('transport_type', 'unknown')
        return self._estimate_travel_time_by_type(transport_type)
    
    def _estimate_travel_time_by_type(self, transport_type: str) -> float:
        """Estimate travel time based on transport type"""
        time_estimates = {
            's-bahn': 3.0,     # 3 minutes between S-Bahn stations
            'u-bahn': 2.5,     # 2.5 minutes between U-Bahn stations
            'tram': 4.0,       # 4 minutes between tram stops
            'omnibus': 3.5,    # 3.5 minutes between bus stops
            'autobus': 3.5,    # Same as omnibus
        }
        return time_estimates.get(transport_type.lower(), 3.0)  # Default 3 minutes
    
    def _calculate_confidence_score(
        self,
        origin_station: StationMatch,
        dest_station: StationMatch,
        transit_path: Dict[str, Any],
        total_walking_distance: float
    ) -> float:
        """Calculate confidence score for a route option"""
        
        score = 1.0
        
        # Penalize long walking distances
        if total_walking_distance > 0.5:  # More than 500m total walking
            score *= 0.8
        elif total_walking_distance > 1.0:  # More than 1km total walking
            score *= 0.6
        
        # Penalize complex routes (many transfers)
        path_length = transit_path.get('path_length', 1)
        if path_length > 2:
            score *= 0.9 ** (path_length - 2)
        
        # Boost direct connections
        if path_length == 1:
            score *= 1.2
        
        # Consider station proximity to addresses
        avg_station_distance = (origin_station.distance_km + dest_station.distance_km) / 2
        if avg_station_distance < 0.2:  # Very close stations
            score *= 1.1
        elif avg_station_distance > 0.8:  # Distant stations
            score *= 0.8
        
        return min(score, 1.0)  # Cap at 1.0
    
    async def get_route_summary(self, route_option: RouteOption) -> str:
        """Generate a text summary of a route option"""
        
        steps_text = []
        for step in route_option.steps:
            if step.step_type == 'walk':
                steps_text.append(f"Walk {step.distance_km:.1f}km to {step.to_location}")
            else:
                steps_text.append(f"Take {step.transport_type} to {step.to_location}")
        
        summary = f"Route from {route_option.origin_address} to {route_option.destination_address}:\n"
        summary += "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps_text))
        summary += f"\n\nTotal: {route_option.total_distance_km:.1f}km, {route_option.estimated_total_time_minutes:.0f} minutes"
        summary += f"\nWalking: {route_option.total_walking_distance_km:.1f}km"
        summary += f"\nConfidence: {route_option.confidence_score:.2f}"
        
        return summary

def get_route_planning_service() -> RoutePlanningService:
    """Get the route planning service instance"""
    return RoutePlanningService() 