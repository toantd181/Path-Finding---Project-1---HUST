from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import time

class TrafficLightState:
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"

class TrafficLightInstance(QObject):
    """Manages the state and timing for a single traffic light instance."""
    state_changed = pyqtSignal() # Signal emitted when the state changes

    def __init__(self, durations, initial_state=TrafficLightState.RED, parent=None):
        super().__init__(parent)
        self.durations = durations # {"red": sec, "yellow": sec, "green": sec}
        self.current_state = initial_state
        self.state_start_time = time.time()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_state)
        self._schedule_next_update()

    def get_current_weight_modifier(self):
        """Calculates the weight modifier based on the current state and duration."""
        duration = self.durations.get(self.current_state, 0)
        if self.current_state == TrafficLightState.RED:
            # Let's use a factor instead of absolute duration for weight increase
            # Higher duration means higher penalty, but maybe not linear?
            # Using a base penalty scaled slightly by duration for simplicity now.
            # Original request: duration * 2. Let's try a base + scaled duration.
            return 50 + duration * 2 # Example: Base penalty + scaled duration
        elif self.current_state == TrafficLightState.YELLOW:
            # Original request: duration * 10
            return 100 + duration * 10 # Example
        elif self.current_state == TrafficLightState.GREEN:
            # Original request: duration * 0.5
            return 10 + duration * 0.5 # Example: Small penalty even for green
        return 0

    def _schedule_next_update(self):
        """Starts the timer for the current state's duration."""
        duration_ms = int(self.durations.get(self.current_state, 5) * 1000) # Default 5s if missing
        self._timer.start(duration_ms)
        # print(f"Traffic Light: State {self.current_state}, Duration {duration_ms/1000}s")

    def _update_state(self):
        """Transitions to the next state and restarts the timer."""
        if self.current_state == TrafficLightState.RED:
            self.current_state = TrafficLightState.GREEN
        elif self.current_state == TrafficLightState.GREEN:
            self.current_state = TrafficLightState.YELLOW
        elif self.current_state == TrafficLightState.YELLOW:
            self.current_state = TrafficLightState.RED
        else: # Should not happen
            self.current_state = TrafficLightState.RED

        self.state_start_time = time.time()
        self._schedule_next_update()
        self.state_changed.emit() # Notify that the state (and thus weight) changed

    def stop(self):
        """Stops the timer."""
        self._timer.stop()

    def get_state_data(self):
        """Returns data needed for saving/recalculation."""
        return {
            "current_state": self.current_state,
            "durations": self.durations,
            # We might not need state_start_time if we always recalculate based on current state
        }

class TrafficLightTool:
    """Holds default settings for the traffic light tool in the sidebar."""
    def __init__(self):
        # Default durations in seconds
        self.default_durations = {
            TrafficLightState.RED: 30,
            TrafficLightState.YELLOW: 5,
            TrafficLightState.GREEN: 25
        }

    def get_default_durations(self):
        return self.default_durations.copy()

    # Methods to potentially update defaults from UI could be added later