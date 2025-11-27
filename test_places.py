import requests
import json
import math

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def build_query(lat, lng, radius, amenity):
    return f"""
    [out:json];
    node["amenity"="{amenity}"](around:{radius},{lat},{lng});
    out;
    """

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance in km between two points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def fetch_places(lat, lng, radius=10000, amenity="cafe"):
    query = build_query(lat, lng, radius, amenity)

    print("\nSending query:\n")
    print(query)

    response = requests.post(OVERPASS_URL, data=query, timeout=10)

    print("\nHTTP status:", response.status_code)
    raw_json = response.json()
    print("\nRaw JSON:")
    print(json.dumps(raw_json, indent=2))

    elements = raw_json.get("elements", [])
    results = []

    for el in elements:
        name = el.get("tags", {}).get("name", "Unknown")
        plat = el.get("lat")
        plon = el.get("lon")

        distance = round(haversine(lat, lng, plat, plon), 2)

        results.append({
            "name": name,
            "lat": plat,
            "lon": plon,
            "distance_km": distance
        })

    return results


if __name__ == "__main__":
    # Example: This is your test coordinate (54.568, -3.155)
    LAT = 54.568
    LNG = -3.155
    RADIUS = 10000  # 10km

    # --- Test cafés ---
    print("\n====== TESTING CAFES ======")
    cafes = fetch_places(LAT, LNG, RADIUS, "cafe")
    print("\nFound cafes:")
    for c in cafes:
        print(f" - {c['name']} ({c['distance_km']} km away)")

    # --- Test pubs ---
    print("\n====== TESTING PUBS ======")
    pubs = fetch_places(LAT, LNG, RADIUS, "pub")
    print("\nFound pubs:")
    for p in pubs:
        print(f" - {p['name']} ({p['distance_km']} km away)")
