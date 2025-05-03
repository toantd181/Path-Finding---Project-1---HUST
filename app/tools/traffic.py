class TrafficTool:
    """Manages the state of the traffic jam tool."""
    def __init__(self, default_weight=50): # Default weight, e.g., for "Light"
        self._weight_increase = default_weight
        # Add other necessary initializations

    def set_weight(self, weight): # Remove the 'checked' parameter
        """Sets the weight increase value for traffic jams."""
        self._weight_increase = weight
        print(f"TrafficTool weight set to: {self._weight_increase}") # Debugging

    def get_weight(self):
        """Gets the current weight increase value."""
        return self._weight_increase

    # Add methods for handling drawing, identifying affected edges, etc.
    # ... other methods ...