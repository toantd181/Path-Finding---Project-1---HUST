from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import time
import math # Import math for ceiling function

class TrafficLightState:
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"

class TrafficLightInstance(QObject):
    """Manages the state and timing for a single traffic light instance."""
    state_changed = pyqtSignal() # Signal emitted when the state changes
    # Signal emitted periodically with the remaining time in the current state
    remaining_time_updated = pyqtSignal(int)

    def __init__(self, durations, initial_state=TrafficLightState.RED, parent=None):
        super().__init__(parent)
        self.durations = durations # {"red": sec, "yellow": sec, "green": sec}
        self.current_state = initial_state
        self.state_start_time = time.time()

        self._state_timer = QTimer(self)
        self._state_timer.setSingleShot(True) # Timer for state transition
        self._state_timer.timeout.connect(self._update_state)

        self._countdown_timer = QTimer(self) # Timer for updating countdown display
        self._countdown_timer.setInterval(500) # Update display twice per second
        self._countdown_timer.timeout.connect(self._emit_remaining_time)

        self._schedule_next_update()
        self._countdown_timer.start()
        self._emit_remaining_time() # Emit initial time immediately

    def get_current_weight_modifier(self):
        """Calculates the weight modifier based on the current state and duration."""
        duration = self.durations.get(self.current_state, 0)
        if self.current_state == TrafficLightState.RED:
            return 50 + duration * 2 # Example: Base penalty + scaled duration
        elif self.current_state == TrafficLightState.YELLOW:
            return 100 + duration * 10 # Example
        elif self.current_state == TrafficLightState.GREEN:
            return 10 + duration * 0.5 # Example: Small penalty even for green
        return 0

    def get_remaining_time(self):
        """Calculates the remaining time in the current state in seconds."""
        duration = self.durations.get(self.current_state, 0)
        elapsed = time.time() - self.state_start_time
        remaining = duration - elapsed
        return max(0, math.ceil(remaining)) # Return ceiling integer, minimum 0

    def _emit_remaining_time(self):
        """Emits the current remaining time."""
        self.remaining_time_updated.emit(self.get_remaining_time())

    def _schedule_next_update(self):
        """Starts the timer for the current state's duration."""
        duration_s = self.durations.get(self.current_state, 5) # Default 5s if missing
        duration_ms = int(duration_s * 1000)
        self._state_timer.start(duration_ms)
        self.state_start_time = time.time() # Reset start time when scheduled
        # print(f"Traffic Light: State {self.current_state}, Duration {duration_s}s")

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

        # state_start_time is reset in _schedule_next_update
        self._schedule_next_update()
        self._emit_remaining_time() # Emit new duration immediately after state change
        self.state_changed.emit() # Notify that the state (and thus weight) changed

    def stop(self):
        """Stops the timers."""
        self._state_timer.stop()
        self._countdown_timer.stop()

    def get_state_data(self):
        """Returns data needed for saving/recalculation."""
        return {
            "current_state": self.current_state,
            "durations": self.durations,
            "remaining_time": self.get_remaining_time() # Include remaining time
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