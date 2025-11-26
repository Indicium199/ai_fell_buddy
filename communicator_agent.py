import requests

class CommunicatorAgent:
    """Fetch nearby pubs/cafes using free OpenStreetMap / Geoapify API."""

    def get_nearby_places(self, lat, lng, place_type="cafe", radius=10000):
        url = f"https://api.geoapify.com/v2/places"
        params = {
            "categories": f"catering.{place_type}",
            "filter": f"circle:{lng},{lat},{radius}",
            "limit": 10,
            "apiKey": "YOUR_GEOAPIFY_API_KEY"
        }
        try:
            r = requests.get(url, params=params, timeout=5).json()
            results = []
            for f in r.get("features", []):
                prop = f.get("properties", {})
                distance = round(prop.get("distance", 0)/1000, 2)
                results.append({
                    "name": prop.get("name", "Unknown"),
                    "distance": distance,
                    "description": prop.get("address_line1", "")
                })
            return results
        except Exception:
            return []
