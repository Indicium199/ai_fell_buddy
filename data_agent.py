import requests

class DataAgent:
    """Fetch weather data (using free APIs)."""

    def get_weather(self, lat, lng):
        # Example using Open-Meteo free API
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lng}&current_weather=true"
        try:
            r = requests.get(url, timeout=5)
            data = r.json().get("current_weather", {})
            return {
                "temperature": data.get("temperature", 0.0),
                "windspeed": data.get("windspeed", 0.0),
                "weather_code": data.get("weathercode", 0)
            }
        except Exception:
            return {"temperature": 0.0, "windspeed": 0.0, "weather_code": 0}

    def map_weather_code(self, code):
        # Simplified mapping
        mapping = {0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast"}
        return mapping.get(code, "Unknown")
