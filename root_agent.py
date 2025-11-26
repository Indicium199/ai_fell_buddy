import os

class RootAgent:
    """Orchestrates conversation, state, and multi-agent reasoning."""

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

    # ------------------------------
    # Generate natural language recommendation for multiple trails
    # ------------------------------
    def recommend_best_trail(self, trails, preferences):
        """Use Gemini to select and describe the best trail in natural language."""
        prompt = "You are a friendly hiking guide. Here are the user's preferences:\n"
        for k, v in preferences.items():
            prompt += f"- {k.capitalize()}: {v}\n"

        prompt += "\nHere are the available trails:\n"
        for t in trails:
            prompt += (
                f"{t['Trail']} — Difficulty: {t['Difficulty']}, Distance: {t['Distance_km']} km, "
                f"Tags: {t.get('Tags', '')}\n"
            )

        prompt += (
            "\nPlease recommend the single best trail for the user based on these preferences. "
            "Write 3–5 sentences in cheerful, natural language, explaining why it is the best choice "
            "and mentioning any interesting tags, views, or features. "
            "Do not just list the trail."
        )

        response = self.gemini.ask_gemini(prompt)
        if response:
            return response
        # Fallback
        return f"{trails[0]['Trail']} seems like a great choice!"

    # ------------------------------
    # Weather description using Gemini
    # ------------------------------
    def generate_weather_description(self, trail, weather):
        prompt = (
            f"You are a friendly hiking assistant. "
            f"Write a cheerful, natural language summary of the current weather for {trail['Trail']}.\n\n"
            f"Weather data:\n"
            f"Temperature: {weather['temperature']}°C\n"
            f"Wind speed: {weather['windspeed']} km/h\n"
            f"Condition code: {weather['weather_code']}\n"
        )
        response = self.gemini.ask_gemini(prompt)
        if response:
            return response
        return (
            f"The weather at {trail['Trail']} is {weather['temperature']}°C "
            f"with winds at {weather['windspeed']} km/h."
        )

    # ------------------------------
    # Conversation flow
    # ------------------------------
    def handle_message(self, msg):
        msg_lower = msg.strip().lower()

        # --- 1: Difficulty ---
        if self.state["awaiting_input"] == "difficulty":
            for level in ["very easy","easy","moderate","hard","very hard"]:
                if level in msg_lower:
                    self.state["difficulty"] = level
                    self.state["awaiting_input"] = "max_distance"
                    return "Max distance (km)?"
            return "Choose difficulty: Very Easy, Easy, Moderate, Hard, Very Hard"

        # --- 2: Max distance ---
        if self.state["awaiting_input"] == "max_distance":
            try:
                self.state["max_distance"] = float(msg)
                self.state["awaiting_input"] = "scenery"
                return "Preferred scenery? (Lake, Forest, Panoramic, etc.)"
            except ValueError:
                return "Please enter a number."

        # --- 3: Scenery ---
        if self.state["awaiting_input"] == "scenery":
            self.state["scenery"] = msg
            self.state["awaiting_input"] = "route_type"
            return "Preferred route type? (Loop, Out-and-back, Ridge)"

        # --- 4: Route type ---
        if self.state["awaiting_input"] == "route_type":
            self.state["route_type"] = msg
            self.state["awaiting_input"] = "trail_selection"

            trails = self.planner.filter_trails(
                difficulty=self.state["difficulty"],
                max_distance=self.state["max_distance"],
                scenery=self.state["scenery"],
                route_type=self.state["route_type"]
            )

            if not trails:
                return "Sorry, I couldn’t find any trails matching your preferences."

            preferences = {
                "difficulty": self.state["difficulty"],
                "max_distance": self.state["max_distance"],
                "scenery": self.state["scenery"],
                "route_type": self.state["route_type"]
            }

            # Gemini selects the best trail and writes a natural description
            recommendation = self.recommend_best_trail(trails, preferences)
            # Assume the first trail is the one Gemini recommends
            self.state["selected_trail"] = trails[0]

            self.state["awaiting_input"] = "confirm_weather"
            return f"{recommendation}\n\nWould you like the current weather for this trail?"

        # --- 5: Weather ---
        if self.state["awaiting_input"] == "confirm_weather":
            if msg_lower in ["yes", "y"]:
                trail = self.state["selected_trail"]
                lat = trail.get("Lat")
                lon = trail.get("Lng")

                weather = self.data_agent.get_weather(lat, lon)
                weather_desc = self.generate_weather_description(trail, weather)

                self.state["awaiting_input"] = "confirm_pubs_cafes"
                return f"{weather_desc}\n\nWould you like a list of the nearest pubs and cafes to {trail['Trail']}?"
            else:
                self.state["awaiting_input"] = None
                return "Alright! Let me know if you want to plan a different trail."

        # --- 6: Nearest pubs/cafes ---
        if self.state["awaiting_input"] == "confirm_pubs_cafes":
            trail = self.state["selected_trail"]
            lat = trail.get("Lat")
            lon = trail.get("Lng")

            if msg_lower in ["yes", "y"]:
                pubs_cafes = self.communicator.get_nearby_places(lat, lon)

                if pubs_cafes:
                    formatted_list = "\n".join([
                        f"{i+1}. {p['name']} – {p['distance']} km – {p['description']}"
                        for i, p in enumerate(pubs_cafes)
                    ])
                    self.state["awaiting_input"] = None
                    return f"Here are some great pubs and cafes near {trail['Trail']}:\n{formatted_list}"
                else:
                    self.state["awaiting_input"] = None
                    return "Sorry, no nearby pubs or cafes were found within 2 km."
            else:
                self.state["awaiting_input"] = None
                return "No problem! Enjoy your hike! 🌄"

        return "I'm not sure how to respond to that. Please follow the prompts."
