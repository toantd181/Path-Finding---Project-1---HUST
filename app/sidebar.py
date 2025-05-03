from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QRadioButton, QButtonGroup, QGroupBox, QPushButton, QComboBox
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QIcon # Import QIcon
from .custom_widgets import FindPathButton
from .tools.traffic import TrafficTool
from .tools.rain import RainTool # Import the new RainTool
import os

class Sidebar(QFrame):
    # Signal to indicate the traffic jam tool should be activated/deactivated
    traffic_tool_activated = pyqtSignal(bool)
    # Signal for rain tool activation
    rain_tool_activated = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)

        # --- Instantiate Tools ---
        self.traffic_tool = TrafficTool() # Create an instance of the traffic tool
        self.rain_tool = RainTool()       # Create an instance of the rain tool
        self._traffic_tool_active = False # Track activation state
        self._rain_tool_active = False    # Track rain tool activation state

        # --- Sidebar Contents ---
        title_label = QLabel("Tools")
        layout.addWidget(title_label)

        # Add Start and End point labels
        self.start_label = QLabel("Start: Not Selected")
        layout.addWidget(self.start_label)

        self.end_label = QLabel("End: Not Selected")
        layout.addWidget(self.end_label)

        # Find Path Button - Use the custom widget
        self.find_path_button = FindPathButton() # Instantiate the custom button
        layout.addWidget(self.find_path_button)

        # --- Traffic Jam Tool ---
        traffic_group_box = QGroupBox("Traffic Jam")
        traffic_layout = QVBoxLayout()

        # Button to activate drawing mode
        self.traffic_jam_button = QPushButton(" Draw Traffic") # Renamed slightly
        self.traffic_jam_button.setCheckable(True) # Make it a toggle button
        self.traffic_jam_button.toggled.connect(self._toggle_traffic_tool)

        # --- Add Traffic Icon ---
        icon_path_traffic = os.path.join(os.path.dirname(__file__),'assets', 'icons', 'traffic-jam.png')
        icon_traffic = QIcon(icon_path_traffic) # Load icon from file
        if not icon_traffic.isNull():
            self.traffic_jam_button.setIcon(icon_traffic)
        else:
            print(f"Warning: Could not load traffic icon: {icon_path_traffic}")
        # --- End Add Icon ---

        traffic_layout.addWidget(self.traffic_jam_button)

        # Intensity ComboBox for Traffic
        intensity_label_traffic = QLabel("Intensity:")
        traffic_layout.addWidget(intensity_label_traffic)
        self.intensity_combo_traffic = QComboBox()
        self.intensity_combo_traffic.addItem("Light (+50)", userData=50)
        self.intensity_combo_traffic.addItem("Moderate (+100)", userData=100)
        self.intensity_combo_traffic.addItem("Heavy (+200)", userData=200)
        self.intensity_combo_traffic.currentIndexChanged.connect(self._update_traffic_weight_from_combo)
        traffic_layout.addWidget(self.intensity_combo_traffic)
        # Set default traffic intensity
        initial_traffic_weight = self.traffic_tool.get_weight()
        index_to_select_traffic = self.intensity_combo_traffic.findData(initial_traffic_weight)
        if index_to_select_traffic != -1:
            self.intensity_combo_traffic.setCurrentIndex(index_to_select_traffic)
        else:
            self.intensity_combo_traffic.setCurrentIndex(0)
            default_traffic_weight = self.intensity_combo_traffic.currentData()
            if default_traffic_weight is not None:
                self.traffic_tool.set_weight(default_traffic_weight)

        traffic_group_box.setLayout(traffic_layout)
        layout.addWidget(traffic_group_box)

        # --- Rain Simulation Tool ---
        rain_group_box = QGroupBox("Rain Simulation")
        rain_layout = QVBoxLayout()

        # Button to activate rain area drawing mode
        self.rain_area_button = QPushButton(" Draw Rain Area")
        self.rain_area_button.setCheckable(True)
        self.rain_area_button.toggled.connect(self._toggle_rain_tool)

        # --- Add Rain Icon ---
        # You'll need a rain icon, e.g., 'rain.png' in assets/icons
        icon_path_rain = os.path.join(os.path.dirname(__file__),'assets', 'icons', 'rain.png') # Assuming you have rain.png
        icon_rain = QIcon(icon_path_rain)
        if not icon_rain.isNull():
            self.rain_area_button.setIcon(icon_rain)
        else:
             print(f"Warning: Could not load rain icon: {icon_path_rain}")
        # --- End Add Icon ---

        rain_layout.addWidget(self.rain_area_button)

        # Intensity ComboBox for Rain
        intensity_label_rain = QLabel("Intensity:")
        rain_layout.addWidget(intensity_label_rain)
        self.intensity_combo_rain = QComboBox()
        # Populate from RainTool
        for intensity_name, weight in self.rain_tool.rain_intensities.items():
             display_text = f"{intensity_name} (+{weight})"
             self.intensity_combo_rain.addItem(display_text, userData=intensity_name) # Store name as data

        self.intensity_combo_rain.currentIndexChanged.connect(self._update_rain_intensity_from_combo)
        rain_layout.addWidget(self.intensity_combo_rain)

        # Set default rain intensity
        initial_rain_intensity = self.rain_tool.get_intensity_name()
        index_to_select_rain = self.intensity_combo_rain.findData(initial_rain_intensity)
        if index_to_select_rain != -1:
            self.intensity_combo_rain.setCurrentIndex(index_to_select_rain)
        else:
            self.intensity_combo_rain.setCurrentIndex(0) # Default to first item
            # Update tool to match default UI if necessary
            default_rain_intensity = self.intensity_combo_rain.currentData()
            if default_rain_intensity is not None:
                self.rain_tool.set_intensity(default_rain_intensity)


        rain_group_box.setLayout(rain_layout)
        layout.addWidget(rain_group_box)


        # Add more widgets here if needed

        layout.addStretch() # Pushes content to the top

    def _toggle_traffic_tool(self, checked):
        """Handles the traffic jam button toggle."""
        if checked:
            # Deactivate rain tool if activating traffic tool
            if self._rain_tool_active:
                self.rain_area_button.setChecked(False) # This will trigger _toggle_rain_tool(False)
        self._traffic_tool_active = checked
        self.traffic_tool_activated.emit(checked) # Emit the signal
        print(f"Traffic tool {'activated' if checked else 'deactivated'}") # For debugging

    def _toggle_rain_tool(self, checked):
        """Handles the rain area button toggle."""
        if checked:
             # Deactivate traffic tool if activating rain tool
            if self._traffic_tool_active:
                self.traffic_jam_button.setChecked(False) # This will trigger _toggle_traffic_tool(False)
        self._rain_tool_active = checked
        self.rain_tool_activated.emit(checked) # Emit the signal for rain tool
        print(f"Rain tool {'activated' if checked else 'deactivated'}") # For debugging


    def _update_traffic_weight_from_combo(self, index):
        """Updates the traffic tool's weight based on ComboBox selection."""
        selected_weight = self.intensity_combo_traffic.itemData(index)
        if selected_weight is not None:
            self.traffic_tool.set_weight(selected_weight)
            print(f"Traffic weight set to: {selected_weight}") # For debugging

    def _update_rain_intensity_from_combo(self, index):
        """Updates the rain tool's intensity based on ComboBox selection."""
        selected_intensity_name = self.intensity_combo_rain.itemData(index)
        if selected_intensity_name is not None:
            self.rain_tool.set_intensity(selected_intensity_name)
            # Debugging print is inside rain_tool.set_intensity