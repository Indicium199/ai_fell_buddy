# trail_reasoner.py

class TrailReasoner:
    """
    Builds structured explanations of how trail recommendations were made,
    and provides a method for selecting a trail with reasoning included.
    """

    def __init__(self, llm=None):
        # llm should support llm.generate_text(prompt)
        self.llm = llm

    def build_explanation(self, inputs, filtered_by):
        """
        Creates a dictionary explaining why a trail (or list of trails)
        was selected.
        """

        explanation = {
            "user_inputs": inputs,
            "filters_applied": filtered_by,
            "llm_reasoning": None
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
                    "Provide a structured, short explanation."
                )

                reasoning_text = self.llm.generate_text(prompt)
                explanation["llm_reasoning"] = reasoning_text

            except Exception:
                explanation["llm_reasoning"] = None

        return explanation

    def select_trail_with_reason(self, trails, explanation_data):
        """
        Selects the top trail from the filtered list and produces
        a structured explanation dictionary.

        Parameters:
            trails (list): list of filtered trail dicts
            explanation_data (dict): metadata about filtering steps
        """

        if not trails:
            return None, None

        selected = trails[0]  # your system chooses the first match

        # Build the reasoning object
        reason = self.build_explanation(
            inputs=explanation_data.get("inputs", {}),
            filtered_by=explanation_data.get("filters", {})
        )

        return selected, reason
