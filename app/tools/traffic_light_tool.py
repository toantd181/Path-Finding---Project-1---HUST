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
        """
        Calculates the weight modifier based on the current state and its remaining time.
        The penalty is proportional to the remaining time, scaled by a state-specific rate.
        """
        # Define penalty rates (penalty units per second of remaining time).
        # These rates determine the penalty's sensitivity to remaining time for each state.
        # Example rates (can be tuned):
        # - If a typical red light (e.g., 30s) should have a max penalty around 100, rate = 100/30 = 3.33
        # - If a typical yellow light (e.g., 5s) should have a max penalty around 50, rate = 50/5 = 10.0
        # - If a typical green light (e.g., 25s) should have a max penalty around 1, rate = 1/25 = 0.04
        penalty_rate = 0.0
        if self.current_state == TrafficLightState.RED:
            penalty_rate = 3.33  # Penalty units per second of red light remaining
        elif self.current_state == TrafficLightState.YELLOW:
            penalty_rate = 10.0  # Penalty units per second of yellow light remaining
        elif self.current_state == TrafficLightState.GREEN:
            # Green light usually has a very low penalty or could even be a bonus (negative rate).
            # For a small penalty that decreases with time:
            penalty_rate = 0.04  # Penalty units per second of green light remaining
        else:
            # Default penalty for unknown state (should ideally not happen)
            return 150.0

        remaining_time_s = self.get_remaining_time() # Integer, >= 0

        # If remaining_time_s is 0 (e.g., state ended or duration is 0/invalid in get_remaining_time),
        # the penalty will correctly be 0.
        
        modified_penalty = penalty_rate * remaining_time_s
        
        return modified_penalty

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
        old_state = self.current_state # For debugging
        if self.current_state == TrafficLightState.RED:
            self.current_state = TrafficLightState.GREEN
        elif self.current_state == TrafficLightState.GREEN:
            self.current_state = TrafficLightState.YELLOW
        elif self.current_state == TrafficLightState.YELLOW:
            self.current_state = TrafficLightState.RED
        else: # Should not happen
            self.current_state = TrafficLightState.RED

        print(f"DEBUG: TrafficLightInstance ID {id(self)}: State changed from {old_state} to {self.current_state}. Emitting state_changed.") # DEBUG

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