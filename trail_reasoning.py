import json

class TrailReasoner:
    """
    Builds structured explanations of how trail recommendations were made,
    and provides a method for selecting a trail with reasoning included.
    """

    def __init__(self, llm=None):
        """
        llm: expected to be a GeminiAgent (or similar) with ask_gemini(prompt)
        """
        self.llm = llm

    def build_explanation(self, inputs, filtered_by, selected_trail_name=None):
        """
        Creates a dictionary explaining why a trail (or list of trails)
        was selected.
        """
        explanation = {
            "user_inputs": inputs,
            "filters_applied": filtered_by,
            "llm_reasoning": None,
            "selected_trail_name": selected_trail_name
        }

        if self.llm:
            try:
                prompt = (
                    "You are an assistant generating a concise reasoning summary "
                    "for a trail recommendation system.\n\n"
                    "Explain briefly how the following inputs produced the "
                    "final trail selection:\n\n"
                    f"User Inputs:\n{inputs}\n\n"
                    f"Filters Applied:\n{filtered_by}\n\n"
                    f"Selected Trail: {selected_trail_name}\n\n"
                    "Provide a structured, short explanation."
                )

                if hasattr(self.llm, "ask_gemini"):
                    reasoning_text = self.llm.ask_gemini(prompt)
                else:
                    reasoning_text = self.llm.generate_text(prompt)

                explanation["llm_reasoning"] = reasoning_text
            except Exception:
                explanation["llm_reasoning"] = None

        return explanation

    def select_trail_with_reason(self, trails, explanation_data):
        """
        Selects the best trail from the filtered list using the LLM and
        produces a structured explanation dictionary.

        Soft/hard weighting:
        - Difficulty and route_type are hard filters (already filtered)
        - Distance and scenery are soft, communicated via _distance_diff and scenery count
        """
        if not trails:
            return None, None

        # Prepare soft weighting data
        for t in trails:
            t["_distance_diff"] = t.get("_distance_diff", 0.0)
            t["_scenery_count"] = len(t.get("Tags", "").split(","))

        prompt = (
            "You are an expert hiking guide AI. Select the BEST trail "
            "from the list based on user preferences.\n\n"
            f"User Preferences:\n{explanation_data.get('inputs')}\n\n"
            "Candidate Trails:\n"
        )

        for t in trails:
            prompt += (
                f"- Name: {t.get('Trail')}\n"
                f"  Difficulty: {t.get('Difficulty')}\n"
                f"  Distance: {t.get('Distance_km')} km\n"
                f"  Distance difference (trail-max): {t.get('_distance_diff')} km\n"
                f"  Route: {t.get('Route')}\n"
                f"  Tags: {t.get('Tags')}\n\n"
            )

        prompt += (
            "Pick the BEST trail considering distance (soft), scenery (soft), "
            "and route/difficulty (hard). Respond ONLY in JSON with fields:\n"
            '{"best_trail": "Name", "reasoning": "Text"}'
        )

        best_name = None
        llm_reasoning_text = None

        if self.llm:
            try:
                response = self.llm.ask_gemini(prompt)
                # Extract JSON safely
                start = response.find("{")
                end = response.rfind("}") + 1
                json_text = response[start:end]
                result = json.loads(json_text)
                best_name = result.get("best_trail")
                llm_reasoning_text = result.get("reasoning", "")
            except Exception:
                # fallback: pick trail with closest distance and most scenery matches
                trails.sort(key=lambda x: (x["_distance_diff"], -x["_scenery_count"]))
                best_name = trails[0]["Trail"]
                llm_reasoning_text = (
                    "Fallback selection based on closest distance and most scenery matches."
                )

        selected = next((t for t in trails if t.get("Trail") == best_name), trails[0])

        reason = self.build_explanation(
            inputs=explanation_data.get("inputs", {}),
            filtered_by=explanation_data.get("filters", {}),
            selected_trail_name=selected.get("Trail")
        )
        if llm_reasoning_text:
            reason["llm_reasoning"] = llm_reasoning_text

        return selected, reason
