# trail_reasoning.py

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

        # Optional LLM-generated summary
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

                # Call Gemini method if available
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

        Parameters:
            trails (list): list of filtered trail dicts
            explanation_data (dict): metadata about filtering steps, e.g.,
                {
                    "inputs": { ... },
                    "filters": { ... }
                }
        """
        if not trails:
            return None, None

        # Build comparison prompt for LLM
        prompt = (
            "You are an expert mountain guide AI. You will select the single best trail "
            "from the list based on the user's preferences.\n\n"
            "User Preferences:\n"
            f"{explanation_data.get('inputs')}\n\n"
            "Candidate Trails:\n"
        )

        for t in trails:
            prompt += (
                f"- Name: {t.get('Trail')}\n"
                f"  Difficulty: {t.get('Difficulty')}\n"
                f"  Distance: {t.get('Distance_km')} km\n"
                f"  Route: {t.get('Route')}\n"
                f"  Tags: {t.get('Tags')}\n\n"
            )

        prompt += (
            "Pick the BEST trail and explain your reasoning. "
            "Respond in JSON with the following fields:\n"
            '{ "best_trail": "Name", "reasoning": "Text" }'
        )

        best_name = trails[0]["Trail"]
        llm_reasoning_text = None

        if self.llm:
            try:
                if hasattr(self.llm, "ask_gemini"):
                    response = self.llm.ask_gemini(prompt)
                else:
                    response = self.llm.generate_text(prompt)

                result = json.loads(response)
                best_name = result.get("best_trail", best_name)
                llm_reasoning_text = result.get("reasoning", None)
            except Exception:
                # fallback to first trail
                best_name = trails[0]["Trail"]
                llm_reasoning_text = None

        # Find chosen trail
        selected = next((t for t in trails if t.get("Trail") == best_name), trails[0])

        # Build final reasoning block
        reason = self.build_explanation(
            inputs=explanation_data.get("inputs", {}),
            filtered_by=explanation_data.get("filters", {}),
            selected_trail_name=selected.get("Trail")
        )

        # Insert LLM reasoning if available
        if llm_reasoning_text:
            reason["llm_reasoning"] = llm_reasoning_text

        return selected, reason
