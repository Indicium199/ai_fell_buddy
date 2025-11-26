import os
from dotenv import load_dotenv

class RootAgent:
    """Orchestrates conversation, state, and multi-agent reasoning using Gemini."""

    def __init__(self, planner, data_agent, communicator, gemini_agent):
        load_dotenv(dotenv_path="./.env")
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
            "selected_trail": None,
            "awaiting_pubs_cafes": False
        }

    # ------------------------------
    # Main conversation handler
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

        # --- 4: Route type & trail recommendation ---
        if self.state["awaiting_input"] == "route_type":
            self.state["route_type"] = msg
            self.state["awaiting_input"] = "trail_selection"

            trails = self.planner.filter_trails(
                difficulty=self.state["difficulty"],
                max_distance=self.state["max_distance"],
                scenery=self.state["scenery"],
                route_type=self.state["route_type"]
            )

            # Build Gemini prompt
            prompt = "User preferences:\n"
            prompt += f"- Difficulty: {self.state['difficulty']}\n"
            prompt += f"- Max distance: {self.state['max_distance']} km\n"
            prompt += f"- Scenery: {self.state['scenery']}\n"
            prompt += f"- Route: {self.state['route_type']}\n\nFiltered trails:\n"
            for t in trails:
                prompt += f"{t['Trail']} — Difficulty: {t['Difficulty']}, Distance: {t['Distance_km']} km, Tags: {t.get('Tags','N/A')}\n"
            prompt += "\nWrite a friendly paragraph recommending the best trail."

            recommendation = self.gemini.ask_gemini(prompt)

            # Fallback if Gemini fails
            if not recommendation:
                if trails:
                    t = trails[0]
                    recommendation = (
                        f"I recommend {t['Trail']}, a {t['Difficulty']} trail, "
                        f"{t['Distance_km']} km long, with tags: {t.get('Tags','N/A')}."
                    )
                else:
                    recommendation = "Sorry, I couldn’t find any trails matching your preferences."

            # Save the first recommended trail
            if trails:
                self.state["selected_trail"] = trails[0]

            # Next step: weather
            self.state["awaiting_input"] = "confirm_weather"
            return recommendation + "\n\nWould you like the current weather for this trail?"

        # --- 5: Weather ---
        if self.state["awaiting_input"] == "confirm_weather":
            if msg_lower in ["yes","y"]:
                trail = self.state["selected_trail"]
                lat, lon = trail.get("Lat"), trail.get("Lng")

                weather = self.data_agent.get_weather(lat, lon)
                weather_desc = self.data_agent.map_weather_code(weather["weather_code"])

                summary = (
                    f"Temperature: {weather['temperature']}°C, "
                    f"Wind speed: {weather['windspeed']} km/h, "
                    f"Condition: {weather_desc}"
                )

                prompt = (
                    f"You are a friendly hiking assistant. "
                    f"Here is the current weather at {trail['Trail']}: {summary}. "
                    "Write a short, cheerful message to tell the user."
                )
                friendly_weather = self.gemini.ask_gemini(prompt)
                if not friendly_weather:
                    friendly_weather = (
                        f"Hey! 🌤️ The weather at {trail['Trail']} is {weather_desc}, "
                        f"{weather['temperature']}°C, winds {weather['windspeed']} km/h."
                    )

                # Ask about pubs/cafes next
                self.state["awaiting_input"] = "confirm_pubs_cafes"
                return friendly_weather + f"\n\nWould you like a list of the nearest pubs and cafes to {trail['Trail']}?"
            else:
                self.state["awaiting_input"] = None
                return "Alright! Let me know if you want to plan a different trail."

        # --- 6: Nearest pubs/cafes ---
        if self.state["awaiting_input"] == "confirm_pubs_cafes":
            trail = self.state["selected_trail"]
            lat, lon = trail.get("Lat"), trail.get("Lng")

            if msg_lower in ["yes","y"]:
                pubs_cafes = self.communicator.get_nearby_places(lat, lon)
                if pubs_cafes:
                    formatted = "\n".join([
                        f"{i+1}. {p['name']} — {p['distance']} km — {p['description']}"
                        for i, p in enumerate(pubs_cafes)
                    ])
                    self.state["awaiting_input"] = None
                    return f"Here are some nearby pubs and cafes:\n{formatted}"
                else:
                    self.state["awaiting_input"] = None
                    return "Sorry, no nearby pubs or cafes were found within 2 km."
            else:
                self.state["awaiting_input"] = None
                return "No problem! Enjoy your hike! 🌄"

        # --- Default fallback ---
        return "I'm not sure how to respond to that. Please follow the prompts."
