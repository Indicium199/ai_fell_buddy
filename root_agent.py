# root_agent.py
import re
from trail_reasoning import TrailReasoner

class RootAgent:
    """Orchestrates conversation, state, and multi-agent reasoning using Gemini."""

    SCENERY_SYNONYMS = {
        "scenic": ["panoramic", "lake", "forest", "view", "fell", "mountain", "scenic"],
        "water": ["lake", "river", "stream", "waterfall", "pond"],
        "mountain": ["fell", "peak", "ridge", "mountain"],
        "forest": ["woodland", "forest", "trees"],
        "lake": ["lake", "water", "pond"],
        "panoramic": ["panoramic", "view", "scenic"],
        "relaxing": ["peaceful", "quiet", "relaxing"]
    }

    def __init__(self, planner, data_agent, communicator, gemini_agent):
        self.planner = planner
        self.data_agent = data_agent
        self.communicator = communicator
        self.gemini = gemini_agent
        self.reasoner = TrailReasoner(gemini_agent)
        self.state = {
            "awaiting_input": "difficulty",
            "difficulty": None,
            "max_distance": None,
            "scenery": None,
            "route_type": None,
            "selected_trail": None,
            "selection_reason": None
        }

    def filter_trails_by_scenery(self, trails, scenery_input):
        """Filter trails using flexible matching with synonyms; optional input."""
        if not scenery_input:
            return trails
        input_keywords = re.findall(r'\w+', scenery_input.lower())
        keywords = []
        for kw in input_keywords:
            synonyms = self.SCENERY_SYNONYMS.get(kw, [kw])
            keywords.extend(synonyms)
        filtered = []
        for trail in trails:
            tags = trail.get("Tags") or []
            if isinstance(tags, str):
                tags = [tags]
            elif not isinstance(tags, list):
                tags = []
            description = trail.get("Description") or ""
            if isinstance(description, list):
                description = " ".join(str(d) for d in description)
            elif not isinstance(description, str):
                description = str(description)
            trail_text = " ".join(tags + [description]).lower()
            if any(k in trail_text for k in keywords):
                filtered.append(trail)
        return filtered if filtered else trails

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
                return "Preferred scenery? (Lake, Forest, Panoramic, etc. — optional)"
            except ValueError:
                return "Please enter a number."

        # --- Scenery ---
        if self.state["awaiting_input"] == "scenery":
            self.state["scenery"] = msg.strip() if msg.strip() else None
            self.state["awaiting_input"] = "route_type"
            return "Preferred route type? (Loop, Out-and-back, Ridge)"

        # --- Route type and trail selection ---
        if self.state["awaiting_input"] == "route_type":
            self.state["route_type"] = msg.strip()

            # --- Step 1: soft/hard filter ---
            trails = self.planner.filter_trails(
                difficulty=self.state["difficulty"],          # hard
                max_distance=self.state["max_distance"],     # soft
                route_type=self.state["route_type"],         # hard
                soft_distance=True
            )

            # --- Step 2: scenery filtering ---
            trails = self.filter_trails_by_scenery(trails, self.state["scenery"])

            if not trails:
                self.state["awaiting_input"] = None
                return "Sorry, I couldn’t find any trails matching your preferences."

            # --- Step 3: LLM-assisted selection ---
            explanation_data = {
                "inputs": {
                    "difficulty": self.state["difficulty"],
                    "max_distance": self.state["max_distance"],
                    "route_type": self.state["route_type"],
                    "scenery": self.state["scenery"]
                },
                "filters": {
                    "initial_trail_count": len(trails),
                    "after_scenery_count": len(trails)
                }
            }

            selected, reason = self.reasoner.select_trail_with_reason(trails, explanation_data)

            self.state["selected_trail"] = selected
            self.state["selection_reason"] = reason
            self.state["awaiting_input"] = "confirm_selection"

            # --- Step 4: Generate description ---
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

            return f"{description}\n\nReason for selection: {reason}\n\nWould you like the current weather for this trail?"

        # --- Confirm trail selection / Weather ---
        if self.state["awaiting_input"] == "confirm_selection":
            if msg_lower in ["yes", "y"]:
                trail = self.state["selected_trail"]
                lat, lon = trail.get("Lat"), trail.get("Lng")
                weather = self.data_agent.get_weather(lat, lon)
                weather_desc = self.data_agent.map_weather_code(weather["weather_code"])
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
            lat, lon = trail.get("Lat"), trail.get("Lng")
            if msg_lower in ["yes", "y", "pubs", "cafes", "cafe", "pub"]:
                if msg_lower in ["pub", "pubs"]:
                    place_types = ["pub"]
                elif msg_lower in ["cafe", "cafes"]:
                    place_types = ["cafe"]
                else:
                    place_types = ["cafe", "pub"]
                places = self.communicator.get_nearby_places(lat, lon, radius=20000, place_types=place_types)
                if places:
                    formatted = [f"{i+1}. {p['name']} – {p.get('distance_km','?')} km away – {p.get('description','')}" for i,p in enumerate(places)]
                    self.state["awaiting_input"] = None
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
