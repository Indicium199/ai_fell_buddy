import os

class RootAgent:
    """Orchestrates conversation, state, and multi-agent reasoning using Gemini."""

    def __init__(self, planner, data_agent, communicator, gemini_agent):
        self.planner = planner
        self.data_agent = data_agent
        self.communicator = communicator
        self.gemini = gemini_agent

        self.state = {
            "awaiting_input": "difficulty",
            "difficulty": None,
            "max_distance": None,
            "scenery": None,
            "route_type": None,
            "selected_trail": None
        }

    def handle_message(self, msg):
        msg_lower = msg.strip().lower()

        # --- Difficulty ---
        if self.state["awaiting_input"] == "difficulty":
            for level in ["very easy","easy","moderate","hard","very hard"]:
                if level in msg_lower:
                    self.state["difficulty"] = level
                    self.state["awaiting_input"] = "max_distance"
                    return "Max distance (km)?"
            return "Choose difficulty: Very Easy, Easy, Moderate, Hard, Very Hard"

        # --- Max distance ---
        if self.state["awaiting_input"] == "max_distance":
            try:
                self.state["max_distance"] = float(msg)
                self.state["awaiting_input"] = "scenery"
                return "Preferred scenery? (Lake, Forest, Panoramic, etc.)"
            except ValueError:
                return "Please enter a number."

        # --- Scenery ---
        if self.state["awaiting_input"] == "scenery":
            self.state["scenery"] = msg
            self.state["awaiting_input"] = "route_type"
            return "Preferred route type? (Loop, Out-and-back, Ridge)"

        # --- Route type ---
        if self.state["awaiting_input"] == "route_type":
            self.state["route_type"] = msg

            # Filter trails
            trails = self.planner.filter_trails(
                difficulty=self.state["difficulty"],
                max_distance=self.state["max_distance"],
                scenery=self.state["scenery"],
                route_type=self.state["route_type"]
            )

            if not trails:
                self.state["awaiting_input"] = None
                return "Sorry, I couldn’t find any trails matching your preferences."

            # Pick top trail
            selected = trails[0]
            self.state["selected_trail"] = selected
            self.state["awaiting_input"] = "confirm_selection"

            # Generate natural trail description via Gemini
            prompt = (
                f"You are a friendly hiking guide. "
                f"Write a cheerful, natural paragraph recommending this trail:\n\n"
                f"Name: {selected['Trail']}\n"
                f"Difficulty: {selected['Difficulty']}\n"
                f"Distance: {selected['Distance_km']} km\n"
                f"Route type: {selected.get('Route','N/A')}\n"
                f"Tags: {selected.get('Tags','')}\n\n"
                "Include the tags naturally and make it engaging."
            )
            description = self.gemini.ask_gemini(prompt)
            if not description:
                description = (
                    f"{selected['Trail']} is a {selected['Difficulty']} trail, "
                    f"{selected['Distance_km']} km long, with tags: {selected.get('Tags','')}"
                )

            return f"{description}\n\nWould you like the current weather for this trail?"

        # --- Confirm trail selection / Weather ---
        if self.state["awaiting_input"] == "confirm_selection":
            if msg_lower in ["yes", "y"]:
                trail = self.state["selected_trail"]
                lat = trail.get("Lat")
                lon = trail.get("Lng")

                # Get weather data
                weather = self.data_agent.get_weather(lat, lon)
                weather_desc = self.data_agent.map_weather_code(weather["weather_code"])

                # Gemini-friendly weather prompt
                weather_prompt = (
                    f"You are a friendly hiking assistant. "
                    f"Here is the current weather at {trail['Trail']}:\n"
                    f"Temperature: {weather['temperature']}°C\n"
                    f"Wind speed: {weather['windspeed']} km/h\n"
                    f"Condition: {weather_desc}\n\n"
                    "Write a short, cheerful message including packing advice."
                )
                friendly_weather = self.gemini.ask_gemini(weather_prompt)
                if not friendly_weather:
                    friendly_weather = (
                        f"Hey! 🌤️ The weather at {trail['Trail']} is {weather_desc}, "
                        f"with a temperature of {weather['temperature']}°C and winds at {weather['windspeed']} km/h."
                    )

                self.state["awaiting_input"] = "confirm_pubs_cafes"
                return f"{friendly_weather}\n\nWould you like me to find cafes or pubs nearby for a post-hike re-fuel?"

            else:
                self.state["awaiting_input"] = None
                return "Alright! Let me know if you want to plan a different trail."

        # --- Pubs/Cafes ---
        if self.state["awaiting_input"] == "confirm_pubs_cafes":
            trail = self.state["selected_trail"]
            lat = trail.get("Lat")
            lon = trail.get("Lng")

            if msg_lower in ["yes", "y", "pubs", "cafes", "cafe", "pub"]:
                # Determine requested place type(s)
                if msg_lower in ["pub", "pubs"]:
                    place_types = ["pub"]
                elif msg_lower in ["cafe", "cafes"]:
                    place_types = ["cafe"]
                else:
                    place_types = ["cafe", "pub"]

                #print(f"DEBUG — Sending query for {place_types} near trail: {trail['Trail']}")
                #print(f"DEBUG — Lat: {lat}, Lng: {lon}")

                places = self.communicator.get_nearby_places(lat, lon, radius=20000, place_types=place_types)
                if places:
                    formatted = []
                    for i, p in enumerate(places):
                        desc = p.get("description", "")
                        formatted.append(f"{i+1}. {p['name']} – {p.get('distance_km', '?')} km away – {desc}")
                    self.state["awaiting_input"] = None

                    # Natural language summary using Gemini
                    prompt = (
                        f"You are a friendly local guide. Recommend these places naturally to hikers:\n"
                        f"{chr(10).join(formatted)}\n\n"
                        "Write a cheerful paragraph introducing these places as post-hike options."
                    )
                    summary = self.gemini.ask_gemini(prompt)
                    if not summary:
                        summary = "Here are some nearby places:\n" + "\n".join(formatted)

                    return summary
                else:
                    self.state["awaiting_input"] = None
                    return "Sorry, no nearby pubs or cafes were found within 20 km."

            else:
                self.state["awaiting_input"] = None
                return "No problem! Enjoy your hike! 🌄"

        # --- Fallback ---
        return "I'm not sure how to respond. Please follow the prompts."
