import os

class RootAgent:
    """Orchestrates conversation, state, and multi-agent reasoning using Gemini."""

    def __init__(self, planner, data_agent, communicator, gemini_agent):
        self.planner = planner
        self.data_agent = data_agent
        self.communicator = communicator
        self.gemini = gemini_agent

        # Conversation state
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

        # --- Step 1: Difficulty ---
        if self.state["awaiting_input"] == "difficulty":
            for level in ["very easy","easy","moderate","hard","very hard"]:
                if level in msg_lower:
                    self.state["difficulty"] = level
                    self.state["awaiting_input"] = "max_distance"
                    return "Max distance (km)?"
            return "Choose difficulty: Very Easy, Easy, Moderate, Hard, Very Hard"

        # --- Step 2: Max distance ---
        if self.state["awaiting_input"] == "max_distance":
            try:
                self.state["max_distance"] = float(msg)
                self.state["awaiting_input"] = "scenery"
                return "Preferred scenery? (Lake, Forest, Panoramic, etc.)"
            except ValueError:
                return "Please enter a number."

        # --- Step 3: Scenery ---
        if self.state["awaiting_input"] == "scenery":
            self.state["scenery"] = msg
            self.state["awaiting_input"] = "route_type"
            return "Preferred route type? (Loop, Out-and-back, Ridge)"

        # --- Step 4: Route type & select trail ---
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

            # Select top trail
            selected = trails[0]
            self.state["selected_trail"] = selected
            self.state["awaiting_input"] = "confirm_selection"

            # Generate natural trail description
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

        # --- Step 5: Weather ---
        if self.state["awaiting_input"] == "confirm_selection":
            if msg_lower in ["yes", "y"]:
                trail = self.state["selected_trail"]
                lat = float(trail.get("Lat"))
                lon = float(trail.get("Lng"))

                # Get weather
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

        # --- Step 6: Cafes / Pubs ---
        if self.state["awaiting_input"] == "confirm_pubs_cafes":
            trail = self.state["selected_trail"]
            lat = float(trail.get("Lat"))
            lon = float(trail.get("Lng"))

            if msg_lower in ["cafe","cafes"]:
                places = self.communicator.get_nearby_places(lat, lon, place_type="cafe")
            elif msg_lower in ["pub","pubs"]:
                places = self.communicator.get_nearby_places(lat, lon, place_type="pub")
            else:
                self.state["awaiting_input"] = None
                return "No problem! Enjoy your hike! 🌄"

            if places:
                # Only show top 3 places
                formatted = "\n".join([
                    f"{i+1}. {p['name']} – {p['distance']} km – {p['description']}"
                    for i, p in enumerate(places[:3])
                ])
                self.state["awaiting_input"] = None
                return f"Here are some nearby {msg_lower}:\n{formatted}"
            else:
                self.state["awaiting_input"] = None
                return f"Sorry, no nearby {msg_lower} were found within the radius."

        # --- Fallback ---
        return "I'm not sure how to respond. Please follow the prompts."
