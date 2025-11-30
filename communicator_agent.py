
# file: communicator_agent.py

import requests
import math

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

class CommunicatorAgent:
    """Fetch nearby pubs/cafes using OpenStreetMap Overpass API."""

    def haversine(self, lat1, lon1, lat2, lon2):
        """Calculate distance in km between two points."""
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat1)) *
             math.cos(math.radians(lat2)) *
             math.sin(dlon/2)**2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def build_query(self, lat, lon, radius, amenities):
        """Construct Overpass QL query for one or more amenities."""
        # If a single string is passed, make it a list
        if isinstance(amenities, str):
            amenities = [amenities]

        # Build query for each amenity
        amenity_filters = "".join([
            f'node["amenity"="{a}"](around:{radius},{lat},{lon});' for a in amenities
        ])

        return f"""
        [out:json][timeout:25];
        {amenity_filters}
        out;
        """

    def get_nearby_places(self, lat, lon, radius=10000, place_types=None):
        """
        Fetch nearby pubs or cafes and return a list with distances and descriptions.

        Args:
            lat (float): Latitude of the trail.
            lon (float): Longitude of the trail.
            radius (int): Search radius in meters.
            place_types (list or str): List of amenities (e.g., ["cafe","pub"]) or single string.
        Returns:
            list: Top 3 nearest places with name, lat, lon, distance_km, description.
        """
        if place_types is None:
            place_types = ["cafe", "pub"]

        # Convert coordinates to float
        try:
            lat = float(lat)
            lon = float(lon)
        except (ValueError, TypeError):
            print("DEBUG — Invalid trail coordinates:", lat, lon)
            return []

        #print(f"DEBUG — Sending query for {place_types} near trail at Lat: {lat}, Lng: {lon}")

        query = self.build_query(lat, lon, radius, place_types)

        try:
            response = requests.post(OVERPASS_URL, data=query, timeout=30)
            response.raise_for_status()
        except Exception as e:
            print("DEBUG — Overpass request error:", e)
            return []

        try:
            raw_json = response.json()
        except Exception as e:
            #print("DEBUG — Could not parse JSON:", e)
            return []

        elements = raw_json.get("elements", [])
        results = []

        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name", "Unknown")
            try:
                plat = float(el.get("lat", 0))
                plon = float(el.get("lon", 0))
            except (ValueError, TypeError):
                continue  # skip invalid coordinates

            distance = round(self.haversine(lat, lon, plat, plon), 2)
            results.append({
                "name": name,
                "lat": plat,
                "lon": plon,
                "distance_km": distance,
                "description": ", ".join(f"{k}: {v}" for k, v in tags.items())
            })

        # Sort by distance and return top 3
        results.sort(key=lambda x: x["distance_km"])
        return results[:3]
