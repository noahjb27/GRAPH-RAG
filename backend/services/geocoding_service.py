"""
Geocoding service for converting addresses to coordinates
Uses OpenStreetMap's Nominatim API for free geocoding
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from urllib.parse import quote

logger = logging.getLogger(__name__)

@dataclass
class GeocodeResult:
    """Result of geocoding an address"""
    address: str
    latitude: float
    longitude: float
    display_name: str
    confidence: float
    found: bool = True
    error_message: Optional[str] = None

class GeocodingService:
    """Service for geocoding addresses using OpenStreetMap Nominatim API"""
    
    def __init__(self, user_agent: str = "BerlinTransportBot/1.0"):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.user_agent = user_agent
        self.session = None
        
        # Focus on Berlin area for better results
        self.berlin_bounds = {
            'viewbox': '13.088,52.338,13.761,52.675',  # Berlin bounding box
            'bounded': 1
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def geocode_address(self, address: str) -> GeocodeResult:
        """
        Geocode a single address to coordinates
        
        Args:
            address: Address to geocode
            
        Returns:
            GeocodeResult with coordinates and metadata
        """
        if not address or address.strip() == "":
            return GeocodeResult(
                address=address,
                latitude=0.0,
                longitude=0.0,
                display_name="",
                confidence=0.0,
                found=False,
                error_message="Empty address provided"
            )
        
        # Enhance address with Berlin context if not already included
        enhanced_address = self._enhance_address_for_berlin(address)
        
        params = {
            'q': enhanced_address,
            'format': 'json',
            'limit': 1,
            'addressdetails': 1,
            'extratags': 1,
            **self.berlin_bounds
        }
        
        headers = {
            'User-Agent': self.user_agent
        }
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(
                self.base_url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    results = await response.json()
                    
                    if results and len(results) > 0:
                        result = results[0]
                        
                        return GeocodeResult(
                            address=address,
                            latitude=float(result['lat']),
                            longitude=float(result['lon']),
                            display_name=result.get('display_name', ''),
                            confidence=float(result.get('importance', 0.5)),
                            found=True
                        )
                    else:
                        return GeocodeResult(
                            address=address,
                            latitude=0.0,
                            longitude=0.0,
                            display_name="",
                            confidence=0.0,
                            found=False,
                            error_message="No results found for address"
                        )
                else:
                    return GeocodeResult(
                        address=address,
                        latitude=0.0,
                        longitude=0.0,
                        display_name="",
                        confidence=0.0,
                        found=False,
                        error_message=f"Geocoding API returned status {response.status}"
                    )
                    
        except asyncio.TimeoutError:
            return GeocodeResult(
                address=address,
                latitude=0.0,
                longitude=0.0,
                display_name="",
                confidence=0.0,
                found=False,
                error_message="Geocoding request timed out"
            )
        except Exception as e:
            logger.error(f"Geocoding error for address '{address}': {str(e)}")
            return GeocodeResult(
                address=address,
                latitude=0.0,
                longitude=0.0,
                display_name="",
                confidence=0.0,
                found=False,
                error_message=f"Geocoding failed: {str(e)}"
            )
    
    async def geocode_multiple_addresses(self, addresses: List[str]) -> List[GeocodeResult]:
        """
        Geocode multiple addresses concurrently
        
        Args:
            addresses: List of addresses to geocode
            
        Returns:
            List of GeocodeResult objects
        """
        # Add rate limiting - max 3 concurrent requests
        semaphore = asyncio.Semaphore(3)
        
        async def _geocode_with_semaphore(address: str) -> GeocodeResult:
            async with semaphore:
                # Add small delay to respect rate limits
                await asyncio.sleep(0.1)
                return await self.geocode_address(address)
        
        tasks = [_geocode_with_semaphore(addr) for addr in addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        geocode_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                geocode_results.append(GeocodeResult(
                    address=addresses[i],
                    latitude=0.0,
                    longitude=0.0,
                    display_name="",
                    confidence=0.0,
                    found=False,
                    error_message=f"Exception during geocoding: {str(result)}"
                ))
            else:
                geocode_results.append(result)
        
        return geocode_results
    
    def _enhance_address_for_berlin(self, address: str) -> str:
        """
        Enhance address with Berlin context for better geocoding results
        
        Args:
            address: Original address
            
        Returns:
            Enhanced address with Berlin context
        """
        address = address.strip()
        
        # If already contains Berlin, return as is
        if any(keyword in address.lower() for keyword in ['berlin', 'deutschland', 'germany']):
            return address
        
        # Add Berlin, Germany context
        return f"{address}, Berlin, Germany"
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        Reverse geocode coordinates to address
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Address string or None if not found
        """
        reverse_url = "https://nominatim.openstreetmap.org/reverse"
        
        params = {
            'lat': latitude,
            'lon': longitude,
            'format': 'json',
            'addressdetails': 1
        }
        
        headers = {
            'User-Agent': self.user_agent
        }
        
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
                
            async with self.session.get(
                reverse_url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result.get('display_name')
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Reverse geocoding error for {latitude}, {longitude}: {str(e)}")
            return None

# Global instance
_geocoding_service = None

def get_geocoding_service() -> GeocodingService:
    """Get the singleton geocoding service instance"""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service 