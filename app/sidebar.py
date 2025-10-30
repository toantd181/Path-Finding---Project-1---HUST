import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame, QRadioButton,
                             QButtonGroup, QGroupBox, QPushButton, QComboBox,
                             QSpinBox, QHBoxLayout, QFormLayout, QLineEdit, QCompleter,
                             QListWidget, QCheckBox)
from PyQt6.QtCore import pyqtSignal, Qt, QStringListModel
from PyQt6.QtGui import QIcon
from .custom_widgets import FindPathButton
from .tools.traffic import TrafficTool
from .tools.block import BlockWayTool
from .tools.traffic_light_tool import TrafficLightTool, TrafficLightState

class Sidebar(QFrame):
    # Signals
    traffic_tool_activated = pyqtSignal(bool)
    block_way_tool_activated = pyqtSignal(bool)
    traffic_light_tool_activated = pyqtSignal(bool)

    # Location search signals
    location_selected_for_start = pyqtSignal(object)
    location_selected_for_end = pyqtSignal(object)
    use_map_start_clicked = pyqtSignal()
    use_map_end_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(270)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Instantiate Tools ---
        self.traffic_tool = TrafficTool()
        self.block_way_tool = BlockWayTool()
        self.traffic_light_tool = TrafficLightTool()
        
        self._traffic_tool_active = False
        self._block_way_tool_active = False
        self._traffic_light_tool_active = False

        # --- Title ---
        title_label = QLabel("Pathfinding Tools")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 5px;")
        layout.addWidget(title_label)

        # --- Location Search ---
        search_group_box = QGroupBox("Select Start & End")
        search_layout = QFormLayout()

        # From Location
        self.from_location_combo = QComboBox()
        self.from_location_combo.setEditable(True)
        self.from_location_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.from_location_combo.lineEdit().setPlaceholderText("Search start location...")
        self.from_location_completer_model = QStringListModel(self)
        self.from_location_completer = QCompleter(self.from_location_completer_model, self)
        self.from_location_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.from_location_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.from_location_combo.setCompleter(self.from_location_completer)
        self.from_location_combo.activated.connect(self._on_from_location_selected)

        self.use_map_start_button = QPushButton("Use Map")
        self.use_map_start_button.setMaximumWidth(80)
        self.use_map_start_button.clicked.connect(self._on_use_map_start_clicked)

        from_widgets_layout = QHBoxLayout()
        from_widgets_layout.addWidget(self.from_location_combo, 1)
        from_widgets_layout.addWidget(self.use_map_start_button)
        search_layout.addRow(QLabel("From:"), from_widgets_layout)

        # To Location
        self.to_location_combo = QComboBox()
        self.to_location_combo.setEditable(True)
        self.to_location_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.to_location_combo.lineEdit().setPlaceholderText("Search end location...")
        self.to_location_completer_model = QStringListModel(self)
        self.to_location_completer = QCompleter(self.to_location_completer_model, self)
        self.to_location_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.to_location_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.to_location_combo.setCompleter(self.to_location_completer)
        self.to_location_combo.activated.connect(self._on_to_location_selected)

        self.use_map_end_button = QPushButton("Use Map")
        self.use_map_end_button.setMaximumWidth(80)
        self.use_map_end_button.clicked.connect(self._on_use_map_end_clicked)

        to_widgets_layout = QHBoxLayout()
        to_widgets_layout.addWidget(self.to_location_combo, 1)
        to_widgets_layout.addWidget(self.use_map_end_button)
        search_layout.addRow(QLabel("To:"), to_widgets_layout)

        search_group_box.setLayout(search_layout)
        layout.addWidget(search_group_box)
        
        self.all_locations_data = []

        # --- Waypoints Section --- NEW
        waypoints_group = QGroupBox("Waypoints (Multi-Stop Route)")
        waypoints_layout = QVBoxLayout()
        
        self.optimize_route_checkbox = QCheckBox("🔄 Optimize Route Order (TSP)")
        self.optimize_route_checkbox.setToolTip(
            "Automatically reorder waypoints to find the shortest total path.\n"
            "This solves the Traveling Salesman Problem for your stops."
        )
        self.optimize_route_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                padding: 5px;
            }
            QCheckBox:checked {
                color: #4CAF50;
            }
        """)
        waypoints_layout.addWidget(self.optimize_route_checkbox)

        # Waypoint list
        self.waypoints_list = QListWidget()
        self.waypoints_list.setMaximumHeight(120)
        self.waypoints_list.setStyleSheet("""
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #ddd;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)
        waypoints_layout.addWidget(QLabel("Stop Order:"))
        waypoints_layout.addWidget(self.waypoints_list)
        
        # Waypoint buttons
        waypoint_buttons_layout = QHBoxLayout()
        
        self.add_waypoint_button = QPushButton("+ Add Stop")
        self.add_waypoint_button.setCheckable(True)
        self.add_waypoint_button.setStyleSheet("""
            QPushButton {
                padding: 6px;
            }
            QPushButton:checked {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                border: 2px solid #F57C00;
            }
        """)
        waypoint_buttons_layout.addWidget(self.add_waypoint_button)
        
        self.remove_waypoint_button = QPushButton("− Remove")
         #self.remove_waypoint_button.clicked.connect(self._remove_selected_waypoint)
        waypoint_buttons_layout.addWidget(self.remove_waypoint_button)
        
        self.clear_waypoints_button = QPushButton("Clear All")
        self.clear_waypoints_button.clicked.connect(self._clear_all_waypoints)
        waypoint_buttons_layout.addWidget(self.clear_waypoints_button)
        
        waypoints_layout.addLayout(waypoint_buttons_layout)
        
        # Reorder buttons
        reorder_layout = QHBoxLayout()
        self.move_up_button = QPushButton("↑ Up")
        self.move_up_button.clicked.connect(self._move_waypoint_up)
        reorder_layout.addWidget(self.move_up_button)
        
        self.move_down_button = QPushButton("↓ Down")
        self.move_down_button.clicked.connect(self._move_waypoint_down)
        reorder_layout.addWidget(self.move_down_button)
        
        waypoints_layout.addLayout(reorder_layout)
        
        waypoints_group.setLayout(waypoints_layout)
        layout.addWidget(waypoints_group)
        
        # Store waypoints data
        self.waypoints = []
        self.original_waypoint_order = []  # List of {node_id, name, pos}

        # Status labels with clear buttons
        start_container = QHBoxLayout()
        self.start_label = QLabel("Start: Not Selected")
        self.start_label.setStyleSheet("color: green; font-weight: bold;")
        self.clear_start_button = QPushButton("✕")
        self.clear_start_button.setMaximumWidth(30)
        self.clear_start_button.setToolTip("Clear start point")
        self.clear_start_button.setEnabled(False)
        start_container.addWidget(self.start_label, 1)
        start_container.addWidget(self.clear_start_button)
        layout.addLayout(start_container)

        end_container = QHBoxLayout()
        self.end_label = QLabel("End: Not Selected")
        self.end_label.setStyleSheet("color: blue; font-weight: bold;")
        self.clear_end_button = QPushButton("✕")
        self.clear_end_button.setMaximumWidth(30)
        self.clear_end_button.setToolTip("Clear end point")
        self.clear_end_button.setEnabled(False)
        end_container.addWidget(self.end_label, 1)
        end_container.addWidget(self.clear_end_button)
        layout.addLayout(end_container)

        # Selection mode buttons
        selection_group = QGroupBox("Click Map to Set:")
        selection_layout = QHBoxLayout()
        
        self.set_start_mode_button = QPushButton("Set Start")
        self.set_start_mode_button.setCheckable(True)
        self.set_start_mode_button.setStyleSheet("""
            QPushButton {
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: 2px solid #2E7D32;
            }
            QPushButton:hover:checked {
                background-color: #45a049;
            }
        """)
        
        self.set_end_mode_button = QPushButton("Set End")
        self.set_end_mode_button.setCheckable(True)
        self.set_end_mode_button.setStyleSheet("""
            QPushButton {
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:checked {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border: 2px solid #1565C0;
            }
            QPushButton:hover:checked {
                background-color: #1e88e5;
            }
        """)
        
        selection_layout.addWidget(self.set_start_mode_button)
        selection_layout.addWidget(self.set_end_mode_button)
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)

        # Find Path Button
        self.find_path_button = FindPathButton()
        layout.addWidget(self.find_path_button)

        # --- Traffic Jam Tool ---
        traffic_group_box = QGroupBox("Traffic Jam")
        traffic_layout = QVBoxLayout()

        self.traffic_jam_button = QPushButton(" Draw Traffic Zone")
        self.traffic_jam_button.setCheckable(True)
        self.traffic_jam_button.toggled.connect(self._toggle_traffic_tool)

        icon_path_traffic = os.path.join(os.path.dirname(__file__),'assets', 'icons', 'traffic-jam.png')
        icon_traffic = QIcon(icon_path_traffic)
        if not icon_traffic.isNull():
            self.traffic_jam_button.setIcon(icon_traffic)

        traffic_layout.addWidget(self.traffic_jam_button)

        intensity_label_traffic = QLabel("Intensity:")
        traffic_layout.addWidget(intensity_label_traffic)
        self.intensity_combo_traffic = QComboBox()
        self.intensity_combo_traffic.addItem("Light (+50)", userData=50)
        self.intensity_combo_traffic.addItem("Moderate (+100)", userData=100)
        self.intensity_combo_traffic.addItem("Heavy (+200)", userData=200)
        self.intensity_combo_traffic.currentIndexChanged.connect(self._update_traffic_weight_from_combo)
        traffic_layout.addWidget(self.intensity_combo_traffic)
        
        initial_traffic_weight = self.traffic_tool.get_weight()
        index_to_select_traffic = self.intensity_combo_traffic.findData(initial_traffic_weight)
        if index_to_select_traffic != -1:
            self.intensity_combo_traffic.setCurrentIndex(index_to_select_traffic)
        else:
            self.intensity_combo_traffic.setCurrentIndex(0)
            default_traffic_weight = self.intensity_combo_traffic.currentData()
            if default_traffic_weight is not None:
                self.traffic_tool.set_weight(default_traffic_weight)

        # Clear traffic button
        self.clear_traffic_jams_button = QPushButton("Clear All Traffic")
        self.clear_traffic_jams_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        traffic_layout.addWidget(self.clear_traffic_jams_button)

        traffic_group_box.setLayout(traffic_layout)
        layout.addWidget(traffic_group_box)

        # --- Block Way Tool ---
        block_way_group_box = QGroupBox("Block Way")
        block_way_layout = QVBoxLayout()

        self.block_way_button = QPushButton(" Draw Block")
        self.block_way_button.setCheckable(True)
        self.block_way_button.toggled.connect(self._toggle_block_way_tool)

        icon_path_block = os.path.join(os.path.dirname(__file__), 'assets', 'icons', 'block.png')
        icon_block = QIcon(icon_path_block)
        if not icon_block.isNull():
            self.block_way_button.setIcon(icon_block)

        block_way_layout.addWidget(self.block_way_button)
        
        # Clear blocks button
        self.clear_block_ways_button = QPushButton("Clear All Blocks")
        self.clear_block_ways_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        block_way_layout.addWidget(self.clear_block_ways_button)
        
        block_way_group_box.setLayout(block_way_layout)
        layout.addWidget(block_way_group_box)

        # --- Traffic Light Tool ---
        traffic_light_group_box = QGroupBox("Traffic Light")
        traffic_light_outer_layout = QVBoxLayout()

        self.traffic_light_button = QPushButton(" Place Traffic Light")
        self.traffic_light_button.setCheckable(True)
        self.traffic_light_button.toggled.connect(self._toggle_traffic_light_tool)

        icon_path_light = os.path.join(os.path.dirname(__file__),'assets', 'icons', 'traffic-light.png')
        icon_light = QIcon(icon_path_light)
        if not icon_light.isNull():
            self.traffic_light_button.setIcon(icon_light)
        traffic_light_outer_layout.addWidget(self.traffic_light_button)

        duration_layout = QFormLayout()
        duration_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.duration_spinbox_red = QSpinBox()
        self.duration_spinbox_red.setSuffix(" s")
        self.duration_spinbox_red.setRange(1, 300)
        self.duration_spinbox_red.setValue(self.traffic_light_tool.default_durations[TrafficLightState.RED])
        duration_layout.addRow("Red:", self.duration_spinbox_red)

        self.duration_spinbox_yellow = QSpinBox()
        self.duration_spinbox_yellow.setSuffix(" s")
        self.duration_spinbox_yellow.setRange(1, 60)
        self.duration_spinbox_yellow.setValue(self.traffic_light_tool.default_durations[TrafficLightState.YELLOW])
        duration_layout.addRow("Yellow:", self.duration_spinbox_yellow)

        self.duration_spinbox_green = QSpinBox()
        self.duration_spinbox_green.setSuffix(" s")
        self.duration_spinbox_green.setRange(1, 300)
        self.duration_spinbox_green.setValue(self.traffic_light_tool.default_durations[TrafficLightState.GREEN])
        duration_layout.addRow("Green:", self.duration_spinbox_green)

        traffic_light_outer_layout.addLayout(duration_layout)
        
        # Clear traffic lights button
        self.clear_traffic_lights_button = QPushButton("Clear All Lights")
        self.clear_traffic_lights_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        traffic_light_outer_layout.addWidget(self.clear_traffic_lights_button)

        traffic_light_group_box.setLayout(traffic_light_outer_layout)
        layout.addWidget(traffic_light_group_box)

        # --- Clear All Effects Button ---
        self.clear_all_effects_button = QPushButton("🗑️ Clear ALL Effects")
        self.clear_all_effects_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 10px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        layout.addWidget(self.clear_all_effects_button)

        layout.addStretch()

    def get_current_traffic_light_durations(self):
        """Retrieves the current duration values from the UI spin boxes."""
        return {
            TrafficLightState.RED: self.duration_spinbox_red.value(),
            TrafficLightState.YELLOW: self.duration_spinbox_yellow.value(),
            TrafficLightState.GREEN: self.duration_spinbox_green.value()
        }

    def _on_from_location_selected(self, index):
        if index >= 0 and index < self.from_location_combo.count():
            location_data = self.from_location_combo.itemData(index)
            if location_data:
                self.location_selected_for_start.emit(location_data)

    def _on_to_location_selected(self, index):
        if index >= 0 and index < self.to_location_combo.count():
            location_data = self.to_location_combo.itemData(index)
            if location_data:
                self.location_selected_for_end.emit(location_data)

    def _on_use_map_start_clicked(self):
        self.use_map_start_clicked.emit()

    def _on_use_map_end_clicked(self):
        self.use_map_end_clicked.emit()

    def populate_location_search(self, locations_data):
        """Populates the 'From' and 'To' QComboBoxes with searchable locations."""
        self.all_locations_data = locations_data 
        display_names = [loc['display_name'] for loc in locations_data]
        
        self.from_location_completer_model.setStringList(display_names)
        self.to_location_completer_model.setStringList(display_names)

        self.from_location_combo.blockSignals(True)
        self.to_location_combo.blockSignals(True)

        self.from_location_combo.clear()
        self.to_location_combo.clear()

        for loc_data in locations_data:
            self.from_location_combo.addItem(loc_data['display_name'], userData=loc_data)
            self.to_location_combo.addItem(loc_data['display_name'], userData=loc_data)
        
        self.from_location_combo.setCurrentIndex(-1)
        self.to_location_combo.setCurrentIndex(-1)

        self.from_location_combo.blockSignals(False)
        self.to_location_combo.blockSignals(False)

    def _uncheck_other_tools(self, sender):
        """Unchecks other tool buttons when one is activated."""
        buttons = [
            self.traffic_jam_button,
            self.block_way_button,
            self.traffic_light_button,
            self.set_start_mode_button,
            self.set_end_mode_button,
            self.add_waypoint_button
        ]
        for button in buttons:
            if button is not sender and button.isChecked():
                button.setChecked(False)

    def _remove_selected_waypoint(self):
        """Remove selected waypoint from list - returns the removed waypoint data"""
        current_row = self.waypoints_list.currentRow()
        if current_row >= 0 and current_row < len(self.waypoints):
            # Get the waypoint being removed
            removed = self.waypoints[current_row]
            
            # Remove from UI
            self.waypoints_list.takeItem(current_row)
            # Remove from current order
            self.waypoints.pop(current_row)
            
            # Also remove from original order by matching node_id
            self.original_waypoint_order = [
                wp for wp in self.original_waypoint_order 
                if wp['node_id'] != removed['node_id']
            ]
            
            # Update numbering in remaining items
            for i in range(self.waypoints_list.count()):
                wp = self.waypoints[i]
                item_text = f"{i + 1}. {wp['name']}"
                self.waypoints_list.item(i).setText(item_text)
            
            print(f"Sidebar: Removed waypoint at position {current_row}: {removed['node_id']}")
            return removed
        return None

    def _clear_all_waypoints(self):
        """Clear all waypoints"""
        self.waypoints_list.clear()
        cleared = self.waypoints.copy()
        self.waypoints.clear()
        self.original_waypoint_order.clear()  # Clear original order too
        print(f"All waypoints cleared: {len(cleared)} waypoints")
        return cleared

    def _move_waypoint_up(self):
        """Move selected waypoint up in the list"""
        current_row = self.waypoints_list.currentRow()
        if current_row > 0:
            item = self.waypoints_list.takeItem(current_row)
            self.waypoints_list.insertItem(current_row - 1, item)
            self.waypoints_list.setCurrentRow(current_row - 1)
            # Swap in data list
            self.waypoints[current_row], self.waypoints[current_row - 1] = \
                self.waypoints[current_row - 1], self.waypoints[current_row]

    def _move_waypoint_down(self):
        """Move selected waypoint down in the list"""
        current_row = self.waypoints_list.currentRow()
        if current_row >= 0 and current_row < self.waypoints_list.count() - 1:
            item = self.waypoints_list.takeItem(current_row)
            self.waypoints_list.insertItem(current_row + 1, item)
            self.waypoints_list.setCurrentRow(current_row + 1)
            # Swap in data list
            self.waypoints[current_row], self.waypoints[current_row + 1] = \
                self.waypoints[current_row + 1], self.waypoints[current_row]

    def add_waypoint_to_list(self, node_id, display_name, pos):
        """Add a waypoint to the list"""
        waypoint_data = {
            'node_id': node_id,
            'name': display_name,
            'pos': pos
        }
        self.waypoints.append(waypoint_data)
        self.original_waypoint_order.append(waypoint_data.copy())  # Save original order
        
        # Add to list widget with number
        item_text = f"{len(self.waypoints)}. {display_name}"
        self.waypoints_list.addItem(item_text)
        print(f"Added waypoint: {display_name}")

    def _toggle_traffic_tool(self, checked):
        self._traffic_tool_active = checked
        if checked:
            self._uncheck_other_tools(self.traffic_jam_button)
        self.traffic_tool_activated.emit(checked)
        print(f"Traffic Tool {'Activated' if checked else 'Deactivated'}")

    def _toggle_block_way_tool(self, checked):
        self._block_way_tool_active = checked
        if checked:
            self._uncheck_other_tools(self.block_way_button)
        self.block_way_tool_activated.emit(checked)
        print(f"Block Way Tool {'Activated' if checked else 'Deactivated'}")

    def _toggle_traffic_light_tool(self, checked):
        self._traffic_light_tool_active = checked
        if checked:
            self._uncheck_other_tools(self.traffic_light_button)
        self.traffic_light_tool_activated.emit(checked)
        print(f"Traffic Light Tool {'Activated' if checked else 'Deactivated'}")

    def _update_traffic_weight_from_combo(self, index):
        selected_weight = self.intensity_combo_traffic.currentData()
        if selected_weight is not None:
            self.traffic_tool.set_weight(selected_weight)
            print(f"Traffic intensity set to: {selected_weight}")