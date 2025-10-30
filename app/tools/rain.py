class RainTool:
    """Manages the state and settings for the rain simulation tool."""
    def __init__(self, default_intensity='Drizzle', default_weight=50):
        self._intensity = default_intensity
        self._weight_increase = default_weight
        self.rain_intensities = {
            "Drizzle": 50,
            "Light Rain": 100,
            "Heavy Rain": 250,
            "Downpour": 350
        }

    def set_intensity(self, intensity_name: str):
        """Sets the rain intensity and corresponding weight increase."""
        if intensity_name in self.rain_intensities:
            self._intensity = intensity_name
            self._weight_increase = self.rain_intensities[intensity_name]
            print(f"RainTool intensity set to: {self._intensity}, weight increase: {self._weight_increase}") # Debugging
        else:
            print(f"Warning: Unknown rain intensity '{intensity_name}'")

    def get_weight_increase(self) -> int:
        """Gets the current weight increase value based on intensity."""
        return self._weight_increase

    def get_intensity_name(self) -> str:
        """Gets the current intensity name."""
        return self._intensity

    def get_available_intensities(self) -> list:
        """Returns a list of available intensity names."""
        return list(self.rain_intensities.keys())

    # Potential future methods:
    # - apply_effect(graph, area)
    # - remove_effect(graph, area_id) # Need a way to track affected areas/edges