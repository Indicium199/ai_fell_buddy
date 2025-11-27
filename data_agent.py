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
        mapping = {
            0: "Clear", 
            1: "Mainly clear", 
            2: "Partly cloudy", 
            3: "Overcast",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
            }
        return mapping.get(code, "Unknown")
