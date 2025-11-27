import requests
import math

class CommunicatorAgent:
    """Fetch nearby pubs/cafes using OpenStreetMap Overpass API."""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

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

    def get_nearby_places(self, lat, lon, place_type="cafe", radius=20000, limit=3):
        """Fetch nearby places from Overpass API and return top N nearest."""
        query = f"""
        [out:json];
        node["amenity"="{place_type}"](around:{radius},{lat},{lon});
        out;
        """
        try:
            response = requests.post(self.OVERPASS_URL, data=query, timeout=10)
            response.raise_for_status()
            elements = response.json().get("elements", [])
        except Exception as e:
            print("DEBUG — Overpass error:", e)
            return []

        results = []
        for el in elements:
            tags = el.get("tags", {})
            plat = el.get("lat")
            plon = el.get("lon")
            distance = round(self.haversine(lat, lon, plat, plon), 2)
            results.append({
                "name": tags.get("name", "Unknown"),
                "distance": distance,
                "description": ", ".join([f"{k}: {v}" for k, v in tags.items() if k != "name"])
            })

        # Sort by distance and return top N
        results.sort(key=lambda x: x["distance"])
        return results[:limit]
