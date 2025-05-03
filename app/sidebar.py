from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QRadioButton, QButtonGroup, QGroupBox, QPushButton # Added QPushButton
from PyQt6.QtCore import pyqtSignal # Added pyqtSignal
from .custom_widgets import FindPathButton
from .tools.traffic import TrafficTool # Import the tool logic

class Sidebar(QFrame):
    # Signal to indicate the traffic jam tool should be activated/deactivated
    traffic_tool_activated = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)

        # --- Instantiate Tools ---
        self.traffic_tool = TrafficTool() # Create an instance of the traffic tool
        self._traffic_tool_active = False # Track activation state

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
        traffic_group_box = QGroupBox("Traffic Jam") # Renamed GroupBox slightly
        traffic_layout = QVBoxLayout()

        # Button to activate drawing mode
        self.traffic_jam_button = QPushButton("Draw Traffic Jam")
        self.traffic_jam_button.setCheckable(True) # Make it a toggle button
        self.traffic_jam_button.toggled.connect(self._toggle_traffic_tool)
        traffic_layout.addWidget(self.traffic_jam_button)

        # Intensity Radio Buttons
        intensity_label = QLabel("Intensity:")
        traffic_layout.addWidget(intensity_label)

        self.traffic_button_group = QButtonGroup(self) # Group for exclusive selection

        self.light_traffic_rb = QRadioButton("Light (+50)")
        self.moderate_traffic_rb = QRadioButton("Moderate (+100)")
        self.heavy_traffic_rb = QRadioButton("Heavy (+200)")

        # Set default UI selection based on tool's default
        if self.traffic_tool.get_weight() == 50:
            self.light_traffic_rb.setChecked(True)
        elif self.traffic_tool.get_weight() == 100:
             self.moderate_traffic_rb.setChecked(True)
        elif self.traffic_tool.get_weight() == 200:
             self.heavy_traffic_rb.setChecked(True)
        else: # Default case if tool has unexpected default
             self.light_traffic_rb.setChecked(True)


        self.traffic_button_group.addButton(self.light_traffic_rb, 50) # ID corresponds to weight
        self.traffic_button_group.addButton(self.moderate_traffic_rb, 100)
        self.traffic_button_group.addButton(self.heavy_traffic_rb, 200)

        # Connect signal to the TrafficTool's set_weight method
        self.traffic_button_group.idToggled.connect(self.traffic_tool.set_weight)

        traffic_layout.addWidget(self.light_traffic_rb)
        traffic_layout.addWidget(self.moderate_traffic_rb)
        traffic_layout.addWidget(self.heavy_traffic_rb)

        traffic_group_box.setLayout(traffic_layout)
        layout.addWidget(traffic_group_box)


        # Add more widgets here if needed

        layout.addStretch() # Pushes content to the top

    def _toggle_traffic_tool(self, checked):
        """Handles the traffic jam button toggle."""
        self._traffic_tool_active = checked
        self.traffic_tool_activated.emit(checked) # Emit the signal
        # Optional: Visually indicate activation, e.g., change button text/style
        # self.traffic_jam_button.setText("Drawing Traffic..." if checked else "Draw Traffic Jam")
        print(f"Traffic tool {'activated' if checked else 'deactivated'}") # For debugging

    # Removed _update_traffic_weight and get_selected_traffic_weight
    # Access the weight via self.traffic_tool.get_weight() when needed elsewhere