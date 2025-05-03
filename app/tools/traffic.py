class TrafficTool:
    """Manages the state of the traffic jam tool."""
    def __init__(self, default_weight=50):
        self._selected_weight = default_weight

    def set_weight(self, weight, checked):
        """Sets the traffic weight if the corresponding radio button is checked."""
        if checked:
            self._selected_weight = weight
            # print(f"Traffic weight set to: {self._selected_weight}") # Optional: for debugging

    def get_weight(self):
        """Returns the currently selected traffic weight."""
        return self._selected_weight

    # You can add methods here later to apply the traffic jam effect
    # e.g., def apply_traffic(self, graph, line_segment):
    #           pass