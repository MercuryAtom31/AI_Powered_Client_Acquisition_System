import os
import requests
import logging
from dotenv import load_dotenv
from typing import Dict, List, Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class GooglePlacesClient:
    def __init__(self):
        load_dotenv() # Load environment variables
        self.api_key = os.getenv('GOOGLE_PLACES_API_KEY')
        self.base_url = "https://maps.googleapis.com/maps/api/place/"
        
        if not self.api_key:
            logger.warning("GOOGLE_PLACES_API_KEY not found in .env file. Google Places search will not work.")
            
    def search_places(self, keyword: str, location: str, radius: int = 50000, page: int = 1) -> List[Dict]:
        """
        Search for places using the Google Places API (Nearby Search).
        
        Args:
            keyword (str): The type of business or keyword to search for.
            location (str): The city or location to search within.
            radius (int): Search radius in meters (default 50000m = 50km).
            page (int): Which page of results to fetch (1, 2, or 3). Default is 1.
            
        Returns:
            List of place dictionaries from the requested page.
        """
        if not self.api_key:
            return []
        if page not in [1, 2, 3]:
            raise ValueError("page must be 1, 2, or 3")
            
        # First, get the coordinates for the location (city)
        location_coords = self._get_location_coords(location)
        if not location_coords:
            logger.error(f"Could not get coordinates for location: {location}")
            return []
            
        endpoint = "nearbysearch/json"
        params = {
            'key': self.api_key,
            'keyword': keyword,
            'location': f"{location_coords['lat']},{location_coords['lng']}",
            'radius': radius,
            'type': 'point_of_interest' # Use a broad type
        }
        
        results = None
        next_page_token = None
        for current_page in range(1, page + 1):
            if next_page_token:
                params = {
                    'key': self.api_key,
                    'pagetoken': next_page_token
                }
            try:
                response = requests.get(urljoin(self.base_url, endpoint), params=params)
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                data = response.json()
                
                if data.get('status') == 'OK':
                    results = data.get('results', [])
                    next_page_token = data.get('next_page_token')
                    if current_page < page:
                        # Google API requires a short wait before next_page_token is valid
                        import time
                        time.sleep(2)
                else:
                    logger.error(f"Google Places Nearby Search API error: {data.get('status')}")
                    return []
            except requests.exceptions.RequestException as e:
                logger.error(f"Error calling Google Places Nearby Search API: {str(e)}")
                return []
        return results if results is not None else []

    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """
        Get details for a specific place using the Google Places API (Place Details).
        
        Args:
            place_id (str): The Place ID.
            
        Returns:
            A dictionary containing place details, or None if an error occurs.
        """
        if not self.api_key:
            return None
            
        endpoint = "details/json"
        params = {
            'key': self.api_key,
            'place_id': place_id,
            'fields': 'website,name,formatted_address,international_phone_number' # Specify fields to reduce cost
        }
        
        try:
            response = requests.get(urljoin(self.base_url, endpoint), params=params)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            results = response.json()
            
            if results.get('status') == 'OK':
                return results.get('result')
            else:
                logger.error(f"Google Places Details API error: {results.get('status')}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Google Places Details API: {str(e)}")
            return None


    def _get_location_coords(self, location: str) -> Optional[Dict]:
        if not self.api_key:
            return None

        # FIX: Use the Geocoding API base URL
        geocode_base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'key': self.api_key,
            'address': location
        }

        try:
            response = requests.get(geocode_base_url, params=params)
            response.raise_for_status()
            results = response.json()

            if results.get('status') == 'OK' and results.get('results'):
                return results['results'][0]['geometry']['location']
            else:
                logger.error(f"Geocoding API error for {location}: {results.get('status')}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Geocoding API: {str(e)}")
            return None
