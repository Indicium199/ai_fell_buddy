import csv

class PlannerAgent:
    """Filters trails from CSV based on user preferences."""

    def __init__(self, csv_file="trails.csv"):
        self.trails = []
        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                row["Distance_km"] = float(row["Distance_km"])
                row["Fell_Height_m"] = float(row["Fell_Height_m"])

                # Ensure missing fields exist
                if "Route" not in row:
                    row["Route"] = "N/A"
                if "Tags" not in row:
                    row["Tags"] = ""
                if "Region" not in row:
                    row["Region"] = ""

                self.trails.append(row)

    def filter_trails(self, difficulty=None, max_distance=None, scenery=None, route_type=None):
        filtered = self.trails

        # Filter by difficulty
        if difficulty:
            filtered = [
                t for t in filtered 
                if t["Difficulty"].lower() == difficulty.lower()
            ]

        # Filter by maximum distance
        if max_distance is not None:
            filtered = [
                t for t in filtered 
                if t["Distance_km"] <= max_distance
            ]

        # Filter by scenery (matching tags)
        if scenery:
            filtered = [
                t for t in filtered
                if scenery.lower() in t["Tags"].lower()
            ]

        # Filter by route type (matching the Route column)
        if route_type:
            filtered = [
                t for t in filtered
                if t["Route"].lower() == route_type.lower()
            ]

        # Return top 5 results
        return filtered[:5]
