import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, QRadioButton,
                             QButtonGroup, QGroupBox, QPushButton, QComboBox,
                             QSpinBox, QHBoxLayout, QFormLayout, QLineEdit, QCompleter) # Added QLineEdit, QCompleter
from PyQt6.QtCore import pyqtSignal, Qt, QStringListModel # Added Qt, QStringListModel
from PyQt6.QtGui import QIcon # Added QIcon
from .custom_widgets import FindPathButton
from .tools.traffic import TrafficTool
from .tools.rain import RainTool
from .tools.block import BlockWayTool
from .tools.traffic_light_tool import TrafficLightTool, TrafficLightState # Import new tool
# from .tools.car_mode_tool import CarModeTool # Import the new CarModeTool # No longer needed if tool is simple

class Sidebar(QFrame):
    # Signal to indicate the traffic jam tool should be activated/deactivated
    traffic_tool_activated = pyqtSignal(bool)
    # Signal for rain tool activation
    rain_tool_activated = pyqtSignal(bool)
    # Signal for block way tool activation
    block_way_tool_activated = pyqtSignal(bool) # New signal
    # Signal for traffic light tool activation (placement mode)
    traffic_light_tool_activated = pyqtSignal(bool) # New signal
    # Signal for car mode state activation
    car_mode_state_activated = pyqtSignal(bool) # Renamed signal for Car Mode state
    # Signal for place car block point drawing tool activation
    place_car_block_drawing_tool_activated = pyqtSignal(bool) # New signal for placing block points

    # Signals for location search
    location_selected_for_start = pyqtSignal(object) # Emits the full location data object
    location_selected_for_end = pyqtSignal(object)   # Emits the full location data object
    use_map_start_clicked = pyqtSignal()
    use_map_end_clicked = pyqtSignal()


    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(250) # Increased width slightly for new inputs

        layout = QVBoxLayout(self)

        # --- Instantiate Tools ---
        self.traffic_tool = TrafficTool() # Create an instance of the traffic tool
        self.rain_tool = RainTool()       # Create an instance of the rain tool
        self.block_way_tool = BlockWayTool() # Create an instance of the block way tool
        self.traffic_light_tool = TrafficLightTool() # Instantiate the new tool
        # self.car_mode_tool = CarModeTool() # CarModeTool instance might not be needed if logic is simple
        self._traffic_tool_active = False # Track activation state
        self._rain_tool_active = False    # Track rain tool activation state
        self._block_way_tool_active = False # Track block way tool activation state
        self._traffic_light_tool_active = False # Track activation state
        self._car_mode_state_active = False # Track Car Mode state
        self._place_car_block_drawing_active = False # Track Car Mode drawing activation state

        # --- Sidebar Contents ---
        title_label = QLabel("Tools")
        layout.addWidget(title_label)

        # --- Location Search ---
        search_group_box = QGroupBox("Location Search")
        search_layout = QFormLayout()

        self.from_location_combo = QComboBox()
        self.from_location_combo.setEditable(True)
        self.from_location_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.from_location_combo.lineEdit().setPlaceholderText("Type or select 'From' location")
        self.from_location_completer_model = QStringListModel(self)
        self.from_location_completer = QCompleter(self.from_location_completer_model, self)
        self.from_location_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.from_location_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.from_location_combo.setCompleter(self.from_location_completer)
        # Connect activated signal (when user selects an item from dropdown or hits Enter)
        self.from_location_combo.activated.connect(self._on_from_location_selected)


        self.use_map_start_button = QPushButton("Use Map Start")
        self.use_map_start_button.clicked.connect(self._on_use_map_start_clicked)

        from_widgets_layout = QHBoxLayout()
        from_widgets_layout.addWidget(self.from_location_combo, 1)
        from_widgets_layout.addWidget(self.use_map_start_button)
        search_layout.addRow(QLabel("From:"), from_widgets_layout)

        self.to_location_combo = QComboBox()
        self.to_location_combo.setEditable(True)
        self.to_location_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.to_location_combo.lineEdit().setPlaceholderText("Type or select 'To' location")
        self.to_location_completer_model = QStringListModel(self) # Separate model for 'To'
        self.to_location_completer = QCompleter(self.to_location_completer_model, self)
        self.to_location_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.to_location_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.to_location_combo.setCompleter(self.to_location_completer)
        self.to_location_combo.activated.connect(self._on_to_location_selected)

        self.use_map_end_button = QPushButton("Use Map End")
        self.use_map_end_button.clicked.connect(self._on_use_map_end_clicked)

        to_widgets_layout = QHBoxLayout()
        to_widgets_layout.addWidget(self.to_location_combo, 1)
        to_widgets_layout.addWidget(self.use_map_end_button)
        search_layout.addRow(QLabel("To:"), to_widgets_layout)

        search_group_box.setLayout(search_layout)
        layout.addWidget(search_group_box)
        
        self.all_locations_data = [] # To store the full data for locations for easy lookup

        # Add Start and End point labels (moved after search for better flow)
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


        # --- Block Way Tool --- New Section ---
        block_way_group_box = QGroupBox("Block Way")
        block_way_layout = QVBoxLayout()

        self.block_way_button = QPushButton(" Draw Block")
        self.block_way_button.setCheckable(True)
        self.block_way_button.toggled.connect(self._toggle_block_way_tool)

        # --- Add Block Way Icon (Optional) ---
        # Create or find an icon like 'block.png' or 'stop.png'
        icon_path_block = os.path.join(os.path.dirname(__file__), 'assets', 'icons', 'block.png') # Assuming block.png exists
        icon_block = QIcon(icon_path_block)
        if not icon_block.isNull():
            self.block_way_button.setIcon(icon_block)
        else:
            print(f"Warning: Could not load block way icon: {icon_path_block}")
        # --- End Add Icon ---

        block_way_layout.addWidget(self.block_way_button)
        block_way_group_box.setLayout(block_way_layout)
        layout.addWidget(block_way_group_box)
        # --- End Block Way Tool ---

        # --- Traffic Light Tool --- New Section ---
        traffic_light_group_box = QGroupBox("Traffic Light")
        traffic_light_outer_layout = QVBoxLayout() # Use QVBoxLayout for the group

        # Button to activate placement mode
        self.traffic_light_button = QPushButton(" Place Traffic Light")
        self.traffic_light_button.setCheckable(True)
        self.traffic_light_button.toggled.connect(self._toggle_traffic_light_tool)

        # --- Add Traffic Light Icon ---
        icon_path_light = os.path.join(os.path.dirname(__file__),'assets', 'icons', 'traffic-light.png')
        icon_light = QIcon(icon_path_light)
        if not icon_light.isNull():
            self.traffic_light_button.setIcon(icon_light)
        else:
            print(f"Warning: Could not load icon: {icon_path_light}")
        traffic_light_outer_layout.addWidget(self.traffic_light_button)

        # Duration Inputs using QFormLayout for better alignment
        duration_layout = QFormLayout()
        duration_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow) # Allow fields to expand

        self.duration_spinbox_red = QSpinBox()
        self.duration_spinbox_red.setSuffix(" s")
        self.duration_spinbox_red.setRange(1, 300) # 1 second to 5 minutes
        self.duration_spinbox_red.setValue(self.traffic_light_tool.default_durations[TrafficLightState.RED])
        duration_layout.addRow("Red Duration:", self.duration_spinbox_red)

        self.duration_spinbox_yellow = QSpinBox()
        self.duration_spinbox_yellow.setSuffix(" s")
        self.duration_spinbox_yellow.setRange(1, 60) # 1 second to 1 minute
        self.duration_spinbox_yellow.setValue(self.traffic_light_tool.default_durations[TrafficLightState.YELLOW])
        duration_layout.addRow("Yellow Duration:", self.duration_spinbox_yellow)

        self.duration_spinbox_green = QSpinBox()
        self.duration_spinbox_green.setSuffix(" s")
        self.duration_spinbox_green.setRange(1, 300) # 1 second to 5 minutes
        self.duration_spinbox_green.setValue(self.traffic_light_tool.default_durations[TrafficLightState.GREEN])
        duration_layout.addRow("Green Duration:", self.duration_spinbox_green)

        # Add the duration form layout to the main group layout
        traffic_light_outer_layout.addLayout(duration_layout)

        traffic_light_group_box.setLayout(traffic_light_outer_layout)
        layout.addWidget(traffic_light_group_box)
        # --- End Traffic Light Tool ---

        # --- Car Mode Tool --- New Section ---
        car_mode_group_box = QGroupBox("Car Mode (Block Edge)")
        car_mode_layout = QVBoxLayout()

        self.toggle_car_mode_button = QPushButton("Enable Car Mode") # Renamed
        self.toggle_car_mode_button.setCheckable(True)
        self.toggle_car_mode_button.toggled.connect(self._toggle_car_mode_state) # Renamed handler

        # --- Add Car Mode Icon (Optional) ---
        # Create or find an icon like 'car-block.png' or 'no-entry.png'
        icon_path_car_block = os.path.join(os.path.dirname(__file__), 'assets', 'icons', 'car-block.png') # Assuming car-block.png exists
        icon_car_block = QIcon(icon_path_car_block)
        if not icon_car_block.isNull():
            self.toggle_car_mode_button.setIcon(icon_car_block) # Apply to toggle button
        else:
            print(f"Warning: Could not load car mode icon: {icon_path_car_block}")
        # --- End Add Icon ---
        car_mode_layout.addWidget(self.toggle_car_mode_button)

        self.place_car_block_button = QPushButton(" Place Car Block Point")
        self.place_car_block_button.setCheckable(True)
        self.place_car_block_button.setEnabled(False) # Initially disabled
        self.place_car_block_button.toggled.connect(self._toggle_place_car_block_drawing_tool)
        if not icon_car_block.isNull(): # Reuse icon
            self.place_car_block_button.setIcon(icon_car_block)
        car_mode_layout.addWidget(self.place_car_block_button)

        # Add other controls for car mode if needed in the future
        car_mode_group_box.setLayout(car_mode_layout)
        layout.addWidget(car_mode_group_box)
        # --- End Car Mode Tool ---

        layout.addStretch() # Pushes content to the top

    # --- Add this method ---
    def get_current_traffic_light_durations(self):
        """Retrieves the current duration values from the UI spin boxes."""
        return {
            TrafficLightState.RED: self.duration_spinbox_red.value(),
            TrafficLightState.YELLOW: self.duration_spinbox_yellow.value(),
            TrafficLightState.GREEN: self.duration_spinbox_green.value()
        }
    # --- End of added method ---

    def _on_from_location_selected(self, index):
        # This signal is emitted when an item is chosen from the completer list or typed and enter pressed
        if index >= 0 and index < self.from_location_combo.count():
            location_data = self.from_location_combo.itemData(index)
            if location_data: # Make sure data is valid
                self.location_selected_for_start.emit(location_data)

    def _on_to_location_selected(self, index):
        if index >= 0 and index < self.to_location_combo.count():
            location_data = self.to_location_combo.itemData(index)
            if location_data:
                self.location_selected_for_end.emit(location_data)

    def _on_use_map_start_clicked(self):
        self.use_map_start_clicked.emit()
        # Optionally clear the combo box text, MainWindow will update it if start_node exists
        # self.from_location_combo.lineEdit().setText("") 
        # self.from_location_combo.setCurrentIndex(-1)


    def _on_use_map_end_clicked(self):
        self.use_map_end_clicked.emit()
        # self.to_location_combo.lineEdit().setText("")
        # self.to_location_combo.setCurrentIndex(-1)

    def populate_location_search(self, locations_data):
        """
        Populates the 'From' and 'To' QComboBoxes with searchable locations.
        locations_data is a list of dicts from Pathfinding.get_all_searchable_locations().
        """
        self.all_locations_data = locations_data 
        
        display_names = [loc['display_name'] for loc in locations_data]
        
        self.from_location_completer_model.setStringList(display_names)
        self.to_location_completer_model.setStringList(display_names)

        # Populate ComboBoxes with display names and store full data object
        self.from_location_combo.blockSignals(True)
        self.to_location_combo.blockSignals(True)

        self.from_location_combo.clear()
        self.to_location_combo.clear()

        for loc_data in locations_data:
            self.from_location_combo.addItem(loc_data['display_name'], userData=loc_data)
            self.to_location_combo.addItem(loc_data['display_name'], userData=loc_data)
        
        self.from_location_combo.setCurrentIndex(-1) # No initial selection
        self.to_location_combo.setCurrentIndex(-1)

        self.from_location_combo.blockSignals(False)
        self.to_location_combo.blockSignals(False)

    def _uncheck_other_tools(self, sender):
        """Unchecks other tool buttons when one is activated."""
        buttons = [
            self.traffic_jam_button,
            self.rain_area_button,
            self.block_way_button,
            self.traffic_light_button, # Include new button
            self.place_car_block_button # Include Place Car Block button
        ]
        for button in buttons:
            if button is not sender and button.isChecked():
                button.setChecked(False) # This will trigger their toggled(false) signal

    def _toggle_traffic_tool(self, checked):
        self._traffic_tool_active = checked
        if checked:
            self._uncheck_other_tools(self.traffic_jam_button)
        self.traffic_tool_activated.emit(checked)
        print(f"Traffic Tool {'Activated' if checked else 'Deactivated'}")

    def _toggle_rain_tool(self, checked):
        self._rain_tool_active = checked
        if checked:
            self._uncheck_other_tools(self.rain_area_button)
        self.rain_tool_activated.emit(checked)
        print(f"Rain Tool {'Activated' if checked else 'Deactivated'}")

    def _toggle_block_way_tool(self, checked):
        self._block_way_tool_active = checked
        if checked:
            self._uncheck_other_tools(self.block_way_button)
        self.block_way_tool_activated.emit(checked)
        print(f"Block Way Tool {'Activated' if checked else 'Deactivated'}")

    def _toggle_traffic_light_tool(self, checked):
        """Handles activation/deactivation of the traffic light placement tool."""
        self._traffic_light_tool_active = checked
        if checked:
            self._uncheck_other_tools(self.traffic_light_button)
        # This signal tells MapViewer to enter the mode for placing the icon
        self.traffic_light_tool_activated.emit(checked)
        print(f"Traffic Light Tool {'Activated' if checked else 'Deactivated'}")

    def _toggle_car_mode_state(self, checked):
        """Handles activation/deactivation of the car mode state."""
        self._car_mode_state_active = checked
        self.place_car_block_button.setEnabled(checked)
        if not checked:
            # If car mode is turned off, also deactivate placing block points
            if self.place_car_block_button.isChecked():
                self.place_car_block_button.setChecked(False)
        # self._uncheck_other_tools(self.toggle_car_mode_button) # Toggle button should not uncheck drawing tools
        self.car_mode_state_activated.emit(checked) # Emit state change
        print(f"Car Mode State {'Enabled' if checked else 'Disabled'}")

    def _toggle_place_car_block_drawing_tool(self, checked):
        """Handles activation/deactivation of the car block point placement tool."""
        self._place_car_block_drawing_active = checked
        if checked:
            self._uncheck_other_tools(self.place_car_block_button)
        self.place_car_block_drawing_tool_activated.emit(checked)
        print(f"Place Car Block Point Tool {'Activated' if checked else 'Deactivated'}")

    def _update_traffic_weight_from_combo(self, index):
        selected_weight = self.intensity_combo_traffic.currentData()
        if selected_weight is not None:
            self.traffic_tool.set_weight(selected_weight)
            print(f"Traffic intensity set to: {selected_weight}")
            # No need to recalculate here, it happens when line is drawn/effects

    def _update_rain_intensity_from_combo(self, index):
        """Updates the rain tool's intensity based on the combo box selection."""
        selected_intensity_name = self.intensity_combo_rain.currentData()
        if selected_intensity_name is not None:
            self.rain_tool.set_intensity(selected_intensity_name)
            print(f"Rain intensity set to: {selected_intensity_name}")