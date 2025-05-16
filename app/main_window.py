import sys # Import sys
import os  # Import os
import numpy as np # Import numpy
from PyQt6.QtWidgets import (QApplication, QMainWindow, QHBoxLayout, QWidget,
                             QMessageBox, QGraphicsScene, QGraphicsRectItem,
                             QGraphicsPixmapItem, QGraphicsLineItem, QGraphicsSimpleTextItem,
                             QGraphicsView) # Add QGraphicsView
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer, QLineF # Added QLineF
from PyQt6.QtGui import QColor, QBrush, QPen, QKeyEvent
from .map_viewer import MapViewer, EFFECT_DATA_KEY
from .pathfinding import Pathfinding
from .sidebar import Sidebar
from .tools.traffic_light_tool import TrafficLightInstance, TrafficLightState # Import traffic light specifics

# --- Geometry Helper Functions ---

def _on_segment(p: QPointF, q: QPointF, r: QPointF) -> bool:
    """Check if point q lies on segment pr"""
    return (q.x() <= max(p.x(), r.x()) and q.x() >= min(p.x(), r.x()) and
            q.y() <= max(p.y(), r.y()) and q.y() >= min(p.y(), r.y()))

def _orientation(p: QPointF, q: QPointF, r: QPointF) -> int:
    """Find orientation of ordered triplet (p, q, r).
    Returns:
        0 --> p, q and r are collinear
        1 --> Clockwise
        2 --> Counterclockwise
    """
    val = (q.y() - p.y()) * (r.x() - q.x()) - \
          (q.x() - p.x()) * (r.y() - q.y())
    if val == 0: return 0  # Collinear
    return 1 if val > 0 else 2  # Clockwise or Counterclockwise

def _segments_intersect(p1: QPointF, q1: QPointF, p2: QPointF, q2: QPointF) -> bool:
    """Check if line segment 'p1q1' and 'p2q2' intersect."""
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)

    # General case
    if o1 != o2 and o3 != o4:
        return True

    # Special Cases
    # p1, q1 and p2 are collinear and p2 lies on segment p1q1
    if o1 == 0 and _on_segment(p1, p2, q1): return True
    # p1, q1 and q2 are collinear and q2 lies on segment p1q1
    if o2 == 0 and _on_segment(p1, q2, q1): return True
    # p2, q2 and p1 are collinear and p1 lies on segment p2q2
    if o3 == 0 and _on_segment(p2, p1, q2): return True
    # p2, q2 and q1 are collinear and q1 lies on segment p2q2
    if o4 == 0 and _on_segment(p2, q1, q2): return True

    return False # Doesn't intersect

# --- New Geometry Helper: Distance from point to line segment ---
def point_segment_distance(p: QPointF, a: QPointF, b: QPointF) -> float:
    """Calculates the shortest distance from point p to line segment ab."""
    # Vector AB
    ab_x = b.x() - a.x()
    ab_y = b.y() - a.y()
    # Vector AP
    ap_x = p.x() - a.x()
    ap_y = p.y() - a.y()

    # Length squared of AB
    len_sq_ab = ab_x * ab_x + ab_y * ab_y
    if abs(len_sq_ab) < 1e-9: # A and B are essentially the same point
        return QLineF(p, a).length()

    # t = dot(AP, AB) / |AB|^2
    t = (ap_x * ab_x + ap_y * ab_y) / len_sq_ab

    if t < 0: # Closest point on line AB is A
        closest_point_on_line = a
    elif t > 1: # Closest point on line AB is B
        closest_point_on_line = b
    else: # Projection falls on the segment AB
        closest_point_on_line = QPointF(a.x() + t * ab_x, a.y() + t * ab_y)

    return QLineF(p, closest_point_on_line).length()
# --- End Geometry Helper Functions ---


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Offline Pathfinding App")
        self.setGeometry(100, 100, 1200, 700) # Adjusted size

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # --- Sidebar ---
        self.sidebar = Sidebar()
        self.sidebar.find_path_button.clicked.connect(self._trigger_pathfinding)

        # --- Scene and Map Viewer ---
        self.scene = QGraphicsScene(self)
        map_file = os.path.join(os.path.dirname(__file__), "assets", "map.png")
        self.map_viewer = MapViewer(map_file, self._handle_point_selected, self.scene)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.map_viewer, 1)

        # --- Pathfinding Initialization ---
        db_file = os.path.join(os.path.dirname(__file__), "data", "graph.db")
        self.pathfinder = None
        try:
            self.pathfinder = Pathfinding(db_file) # Pathfinding now stores db_path
            print("Pathfinding engine initialized.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize pathfinding: {e}")
            print(f"Error initializing Pathfinding: {e}")
            # Consider disabling features if pathfinder fails

        self.start_node = None
        self.end_node = None
        self.node_positions = {}
        self._effect_application_threshold = 15 # Default threshold in pixels, adjust as needed
        if self.pathfinder:
            # Extract node positions from the graph
            for node_id, data in self.pathfinder.graph.nodes(data=True):
                if 'pos' in data:
                    self.node_positions[node_id] = data['pos']
            print(f"Loaded {len(self.node_positions)} node positions.")
            # Store original weights for resetting
            # Correctly unpack u, v, data when data=True
            self._original_weights = {}
            if self.pathfinder.graph.number_of_edges() > 0: # Check if there are edges
                try:
                    self._original_weights = {(u, v): data['weight'] for u, v, data in self.pathfinder.graph.edges(data=True) if 'weight' in data}
                    print(f"Stored original weights for {len(self._original_weights)} edges.")
                except KeyError as e:
                    print(f"Warning: Missing 'weight' attribute for an edge: {e}. Original weights might be incomplete.")
            else:
                print("Graph has no edges, no original weights to store.")
            
            self._initialize_search_tool() # Call after pathfinder and node_positions are ready


        # --- Traffic Light Management ---
        # Store active TrafficLightInstance objects, keyed by icon item's memory address
        # Value is now a tuple: (instance, text_item)
        self._active_traffic_lights = {} # {icon_item_id: (TrafficLightInstance, QGraphicsSimpleTextItem)}

        # --- Connect Signals ---
        # Tools activation
        self.sidebar.traffic_tool_activated.connect(self.map_viewer.set_traffic_drawing_mode)
        self.sidebar.rain_tool_activated.connect(self.map_viewer.set_rain_drawing_mode)
        self.sidebar.block_way_tool_activated.connect(self.map_viewer.set_block_way_drawing_mode)
        self.sidebar.traffic_light_tool_activated.connect(self.map_viewer.set_traffic_light_placement_mode) # Connect new tool
        # self.sidebar.car_mode_tool_activated.connect(self.map_viewer.set_car_mode_drawing_mode) # Old connection
        self.sidebar.place_car_block_drawing_tool_activated.connect(self.map_viewer.set_car_mode_drawing_mode) # Connect new Car Mode drawing signal

        # Drawing results / Effect placement
        self.map_viewer.traffic_line_drawn.connect(self.handle_traffic_line)
        self.map_viewer.rain_area_defined.connect(self.handle_rain_area)
        self.map_viewer.block_way_drawn.connect(self.handle_block_way)
        # Connect new traffic light signals
        # self.map_viewer.traffic_light_line_drawn.connect(self.handle_traffic_light_finalized) # Old signal
        self.map_viewer.traffic_light_visuals_created.connect(self.handle_traffic_light_finalized) # New signal - This connection is now correct
        self.map_viewer.car_block_point_placed.connect(self.handle_car_block_point_placed) # Connect Car Mode click

        # Effect removal / changes
        self.map_viewer.effects_changed.connect(self._handle_effects_changed) # Connect effect removal

        # Connect search signals
        self.sidebar.location_selected_for_start.connect(self._handle_location_selected_for_start)
        self.sidebar.location_selected_for_end.connect(self._handle_location_selected_for_end)
        self.sidebar.use_map_start_clicked.connect(self._handle_use_map_start_clicked)
        self.sidebar.use_map_end_clicked.connect(self._handle_use_map_end_clicked)


    def _initialize_search_tool(self):
        if not self.pathfinder:
            print("Search tool not initialized: Pathfinding engine not available.")
            return
        
        locations_data = self.pathfinder.get_all_searchable_locations()
        if locations_data:
            self.sidebar.populate_location_search(locations_data)
            print(f"Search tool populated with {len(locations_data)} locations.")
        else:
            print("Search tool: No locations found to populate.")

    def _set_start_node_from_data(self, location_data):
        """Helper to set start node from location data (node or special place)."""
        node_id_to_set = None
        position_to_set = None # This will be a tuple (x,y)
        display_name_for_label = location_data['display_name'].split(' (')[0] # Get name before "(Node)" or "(Place)"

        if location_data['type'] == 'node':
            node_id_to_set = location_data['id'] # id is the node name
            if node_id_to_set in self.node_positions:
                position_to_set = self.node_positions[node_id_to_set]
            else:
                QMessageBox.warning(self, "Error", f"Node '{node_id_to_set}' from search not found in map data.")
                print(f"Error: Node {node_id_to_set} from search not in node_positions.")
                return False
        elif location_data['type'] == 'special_place':
            sp_x, sp_y = location_data['pos']
            # Find the nearest graph node to this special place's coordinates
            node_id_to_set = self._find_nearest_node(sp_x, sp_y)
            if node_id_to_set and node_id_to_set in self.node_positions:
                position_to_set = self.node_positions[node_id_to_set]
                # Label should show special place name, but indicate the snapped node
                display_name_for_label = f"{location_data['name']} (near Node {node_id_to_set})"
            else:
                QMessageBox.warning(self, "Error", f"Could not find a nearby map node for special place '{location_data['name']}'.")
                print(f"Error: Could not find nearest node for special place {location_data['name']} or its position.")
                return False
        else:
            print(f"Unknown location type: {location_data['type']}")
            return False

        if node_id_to_set and position_to_set:
            if node_id_to_set == self.end_node:
                QMessageBox.warning(self, "Selection Error", "Start location cannot be the same as the end location.")
                self.sidebar.from_location_combo.setCurrentIndex(-1) # Clear invalid selection
                self.sidebar.from_location_combo.lineEdit().setText("")
                return False

            self.start_node = node_id_to_set
            snapped_pos = QPointF(position_to_set[0], position_to_set[1])
            self.sidebar.start_label.setText(f"Start: {display_name_for_label}")
            self.map_viewer.set_permanent_point("start", snapped_pos)
            print(f"Start node set to {self.start_node} via search: {location_data['display_name']}")
            return True
        return False

    def _set_end_node_from_data(self, location_data):
        """Helper to set end node from location data."""
        node_id_to_set = None
        position_to_set = None
        display_name_for_label = location_data['display_name'].split(' (')[0]

        if location_data['type'] == 'node':
            node_id_to_set = location_data['id']
            if node_id_to_set in self.node_positions:
                position_to_set = self.node_positions[node_id_to_set]
            else:
                QMessageBox.warning(self, "Error", f"Node '{node_id_to_set}' from search not found in map data.")
                print(f"Error: Node {node_id_to_set} from search not in node_positions.")
                return False
        elif location_data['type'] == 'special_place':
            sp_x, sp_y = location_data['pos']
            node_id_to_set = self._find_nearest_node(sp_x, sp_y)
            if node_id_to_set and node_id_to_set in self.node_positions:
                position_to_set = self.node_positions[node_id_to_set]
                display_name_for_label = f"{location_data['name']} (near Node {node_id_to_set})"
            else:
                QMessageBox.warning(self, "Error", f"Could not find a nearby map node for special place '{location_data['name']}'.")
                print(f"Error: Could not find nearest node for special place {location_data['name']} or its position.")
                return False
        else:
            print(f"Unknown location type: {location_data['type']}")
            return False

        if node_id_to_set and position_to_set:
            if node_id_to_set == self.start_node:
                QMessageBox.warning(self, "Selection Error", "End location cannot be the same as the start location.")
                self.sidebar.to_location_combo.setCurrentIndex(-1) # Clear invalid selection
                self.sidebar.to_location_combo.lineEdit().setText("")
                return False

            self.end_node = node_id_to_set
            snapped_pos = QPointF(position_to_set[0], position_to_set[1])
            self.sidebar.end_label.setText(f"End: {display_name_for_label}")
            self.map_viewer.set_permanent_point("end", snapped_pos)
            print(f"End node set to {self.end_node} via search: {location_data['display_name']}")
            return True
        return False

    def _handle_location_selected_for_start(self, location_data):
        if self._set_start_node_from_data(location_data):
            if self.start_node and self.end_node:
                self._trigger_pathfinding()
            else:
                self.map_viewer.clear_path() # Clear path if only one point is set/changed

    def _handle_location_selected_for_end(self, location_data):
        if self._set_end_node_from_data(location_data):
            if self.start_node and self.end_node:
                self._trigger_pathfinding()
            else:
                self.map_viewer.clear_path()

    def _handle_use_map_start_clicked(self):
        if self.start_node and self.start_node in self.node_positions:
            self.sidebar.start_label.setText(f"Start: Node {self.start_node} (Map)")
            # Update the combo box to show this, but don't select an item from its list
            self.sidebar.from_location_combo.lineEdit().setText(f"Node {self.start_node} (Map Selection)")
            self.sidebar.from_location_combo.setCurrentIndex(-1) # Ensure no item is actually selected in dropdown
            print(f"Used current map start point: Node {self.start_node}")
        else:
            QMessageBox.information(self, "Info", "No start point selected on the map to use.")
            self.sidebar.start_label.setText("Start: Not Selected")
            self.sidebar.from_location_combo.lineEdit().setText("")
            self.sidebar.from_location_combo.setCurrentIndex(-1)

    def _handle_use_map_end_clicked(self):
        if self.end_node and self.end_node in self.node_positions:
            self.sidebar.end_label.setText(f"End: Node {self.end_node} (Map)")
            self.sidebar.to_location_combo.lineEdit().setText(f"Node {self.end_node} (Map Selection)")
            self.sidebar.to_location_combo.setCurrentIndex(-1)
            print(f"Used current map end point: Node {self.end_node}")
        else:
            QMessageBox.information(self, "Info", "No end point selected on the map to use.")
            self.sidebar.end_label.setText("End: Not Selected")
            self.sidebar.to_location_combo.lineEdit().setText("")
            self.sidebar.to_location_combo.setCurrentIndex(-1)

    def _update_combo_text_for_map_selection(self, point_type_str, node_id):
        """Updates the corresponding QComboBox text when a point is selected/deselected on the map."""
        combo = None
        label_widget = None
        label_prefix = ""

        if point_type_str == "start":
            combo = self.sidebar.from_location_combo
            label_widget = self.sidebar.start_label
            label_prefix = "Start: "
        elif point_type_str == "end":
            combo = self.sidebar.to_location_combo
            label_widget = self.sidebar.end_label
            label_prefix = "End: "
        
        if combo:
            if node_id is None: # Point cleared
                combo.setCurrentIndex(-1)
                combo.lineEdit().setText("")
                if label_widget: label_widget.setText(f"{label_prefix}Not Selected")
            else:
                # Try to find if this node_id matches an existing item in the combo's model
                found_idx = -1
                item_display_text = f"Node {node_id} (Map Selection)" # Default text
                for i in range(combo.count()): # Iterate through items in ComboBox
                    item_data = combo.itemData(i)
                    # Check if the item_data corresponds to the selected node_id
                    if item_data and item_data.get('type') == 'node' and item_data.get('id') == node_id:
                        found_idx = i
                        item_display_text = item_data.get('display_name', item_display_text)
                        break
                    # If node_id was derived from a special place, we can't easily reverse map to its display_name here
                    # So, we'll just show "Node X (Map Selection)" or the direct node name if found.
                
                if found_idx != -1:
                    combo.setCurrentIndex(found_idx) # This will also update the lineEdit text
                    if label_widget: label_widget.setText(f"{label_prefix}{item_display_text.split(' (')[0]}")
                else: # If not found as a pre-populated item (e.g. pure node click)
                    combo.lineEdit().setText(item_display_text)
                    combo.setCurrentIndex(-1) # Ensure no dropdown item is selected if text is custom
                    if label_widget: label_widget.setText(f"{label_prefix}Node {node_id} (Map)")


    def _handle_effects_changed(self):
        """Handles the signal emitted when an effect visual is removed."""
        print("Effect removed, checking for stopped timers and recalculating...")

        # Check if any removed items were associated with active traffic lights
        # Get current icon IDs from the stored visuals in MapViewer
        # The tuple now contains (icon, line, text, data)
        active_icon_ids = {id(visual[0]) for visual in self.map_viewer.traffic_light_visuals}
        lights_to_remove = []

        # Iterate over a copy of the keys since we might modify the dictionary
        for icon_id in list(self._active_traffic_lights.keys()):
            if icon_id not in active_icon_ids:
                # Correctly unpack all four items, using _ for unused ones here
                instance, text_item, _, _ = self._active_traffic_lights[icon_id]
                print(f"Stopping timer for removed traffic light (icon id: {icon_id})")
                instance.stop()
                # No need to manually remove text_item, MapViewer handles visual removal
                lights_to_remove.append(icon_id)

        for icon_id in lights_to_remove:
            if icon_id in self._active_traffic_lights: # Check if still exists before deleting
                 del self._active_traffic_lights[icon_id]

        # Recalculate everything after removal
        self._recalculate_effects_and_path()

    def handle_traffic_line(self, start_point, end_point):
        """Handles the line drawn in traffic mode: Stores data on the visual item."""
        if not self.pathfinder: return

        traffic_weight_increase = self.sidebar.traffic_tool.get_weight()
        print(f"Traffic line drawn. Applying weight +{traffic_weight_increase}")

        # Find the corresponding visual item (the last one added)
        if self.map_viewer.traffic_jam_lines:
            last_line_item = self.map_viewer.traffic_jam_lines[-1]
            traffic_data = {
                "type": "traffic",
                "weight": traffic_weight_increase,
                "start": start_point,
                "end": end_point
            }
            last_line_item.setData(EFFECT_DATA_KEY, traffic_data)
            print(f"Stored data on traffic line item: {traffic_data}")
        else:
            print("Warning: Could not find traffic line item to store data on.")

        # --- Recalculate all effects and path ---
        self._recalculate_effects_and_path()


    def handle_rain_area(self, area_rect: QRectF):
        """Handles the rectangle drawn for rain: Stores data on the visual item."""
        if not self.pathfinder: return

        rain_intensity_name = self.sidebar.rain_tool.get_intensity_name()
        rain_weight_increase = self.sidebar.rain_tool.get_weight_increase() # Get weight based on name
        print(f"Rain area defined. Applying intensity '{rain_intensity_name}' (weight +{rain_weight_increase})")

        # Find the corresponding visual item
        if self.map_viewer.rain_area_visuals:
            last_area_item = self.map_viewer.rain_area_visuals[-1]
            rain_data = {
                "type": "rain",
                "intensity": rain_intensity_name, # Store name
                "weight": rain_weight_increase,   # Store calculated weight
                "rect": area_rect
            }
            last_area_item.setData(EFFECT_DATA_KEY, rain_data)
            print(f"Stored data on rain area item: {rain_data}")
        else:
            print("Warning: Could not find rain area item to store data on.")

        # --- Recalculate all effects and path ---
        self._recalculate_effects_and_path()


    def handle_block_way(self, start_point, end_point):
        """Handles the line drawn in block way mode: Stores data."""
        if not self.pathfinder: return

        print(f"Block way line drawn from {start_point} to {end_point}")

        # Find the corresponding visual item
        if self.map_viewer.block_way_visuals:
            last_block_item = self.map_viewer.block_way_visuals[-1]
            block_data = {
                "type": "block_way",
                "start": start_point,
                "end": end_point
            }
            last_block_item.setData(EFFECT_DATA_KEY, block_data)
            print(f"Stored data on block way item: {block_data}")
        else:
            print("Warning: Could not find block way item to store data on.")

        # --- Recalculate all effects and path ---
        self._recalculate_effects_and_path()

    # --- Car Mode Handling --- New Method ---
    def handle_car_block_point_placed(self, click_pos: QPointF):
        """Handles a click intended to block the nearest edge for car mode."""
        if not self.pathfinder or not self.node_positions:
            print("Pathfinder or node positions not available for car block.")
            return

        min_dist = float('inf')
        nearest_edge_nodes = None
        nearest_edge_midpoint = None

        for u, v, data in self.pathfinder.graph.edges(data=True):
            try:
                pos_u = QPointF(*self.node_positions[u])
                pos_v = QPointF(*self.node_positions[v])

                dist = point_segment_distance(click_pos, pos_u, pos_v)

                if dist < min_dist:
                    min_dist = dist
                    nearest_edge_nodes = (u, v)
                    nearest_edge_midpoint = QPointF((pos_u.x() + pos_v.x()) / 2, (pos_u.y() + pos_v.y()) / 2)

            except KeyError:
                # Should not happen if graph and node_positions are consistent
                print(f"Warning: Node position missing for edge ({u}-{v}) during car block check.")
                continue

        if nearest_edge_nodes and nearest_edge_midpoint:
            u, v = nearest_edge_nodes
            print(f"Car block placed. Nearest edge: {u}-{v} (distance: {min_dist:.2f}). Blocking it.")

            # Create visual marker at the midpoint of the blocked edge
            marker_tooltip = f"Edge {u}-{v}"
            marker_item = self.map_viewer.draw_car_block_marker(nearest_edge_midpoint, marker_tooltip)

            car_block_data = {
                "type": "car_block",
                "click_pos": click_pos, # Store original click for reference if needed
                "blocked_edge_nodes": nearest_edge_nodes,
                "edge_midpoint": nearest_edge_midpoint # For potential re-drawing or identification
            }
            marker_item.setData(EFFECT_DATA_KEY, car_block_data)
            print(f"Stored data on car block marker: {car_block_data}")

            # Actual graph modification happens in _recalculate_effects_and_path
            self._recalculate_effects_and_path()
        else:
            print("Could not find a nearest edge to block for car mode.")
            # Optionally, uncheck the button if no edge found, or let user try again
            # self.sidebar.car_mode_button.setChecked(False)


    # --- Traffic Light Handling --- Modified Method ---
    def handle_traffic_light_finalized(self, icon_pos, line_start, line_end, icon_item, line_item, text_item):
        """Handles the finalized placement of a traffic light (icon + line + text)."""
        if not self.pathfinder: return

        # Get durations from the sidebar UI
        durations = self.sidebar.get_current_traffic_light_durations()
        print(f"Traffic light finalized at {icon_pos} with durations: {durations}")

        # Visual items are now passed directly from the signal

        # Create the state manager instance for this light
        traffic_light_instance = TrafficLightInstance(durations)
        traffic_light_instance.state_changed.connect(self._traffic_light_state_updated) # Connect state change
        # Connect the new countdown signal
        traffic_light_instance.remaining_time_updated.connect(self._update_traffic_light_countdown_display)

        # Store data on the visual items for reference and recalculation
        # Note: MapViewer already stored basic data, we add the instance here
        # Retrieve existing data and update it
        existing_data = icon_item.data(EFFECT_DATA_KEY) or {} # Get data MapViewer stored
        traffic_light_data = {
            **existing_data, # Keep existing keys like type, positions
            "durations": durations,
            "instance": traffic_light_instance, # Store the instance itself
            "text_item": text_item # Keep reference to text item
        }
        # Update data stored on items
        icon_item.setData(EFFECT_DATA_KEY, traffic_light_data)
        line_item.setData(EFFECT_DATA_KEY, traffic_light_data)
        text_item.setData(EFFECT_DATA_KEY, traffic_light_data)

        # Update the data stored in MapViewer's list as well
        for i, (ic, ln, tx, data) in enumerate(self.map_viewer.traffic_light_visuals):
             if ic == icon_item:
                 self.map_viewer.traffic_light_visuals[i] = (ic, ln, tx, traffic_light_data)
                 break

        # Store the active instance and text_item, keyed by icon item's ID
        icon_id = id(icon_item)
        self._active_traffic_lights[icon_id] = (traffic_light_instance, text_item, icon_item, line_item)
        print(f"Stored data and started timer for traffic light (icon id: {icon_id})")

        # Update the visual state immediately (e.g., tooltip, initial countdown, text color)
        self.map_viewer.update_traffic_light_visual_state(icon_item, text_item, traffic_light_instance.current_state) # Pass text_item
        self.map_viewer.update_traffic_light_countdown(text_item, traffic_light_instance.get_remaining_time())

        # --- Recalculate all effects and path ---
        self._recalculate_effects_and_path()


    def _traffic_light_state_updated(self):
        print(f"DEBUG: MainWindow._traffic_light_state_updated called by: {self.sender()}") # DEBUG
        traffic_light_instance = self.sender()
        if traffic_light_instance and isinstance(traffic_light_instance, TrafficLightInstance):
            print(f"DEBUG: MainWindow: Signal from TrafficLightInstance. New state: {traffic_light_instance.current_state}") # DEBUG

            # Find the corresponding visual icon and text item to update appearance/tooltip
            found_icon_item = None
            found_text_item = None
            # The value in _active_traffic_lights is (instance, text_item, icon_item, line_item)
            # Unpack all four items. Use _ for items not immediately needed if any.
            for _icon_id, (instance_from_dict, text_item_from_dict, icon_item_from_dict, _line_item_from_dict) in self._active_traffic_lights.items():
                 if instance_from_dict == traffic_light_instance:
                     found_icon_item = icon_item_from_dict
                     found_text_item = text_item_from_dict
                     break
            # The previous inner loop searching self.map_viewer.traffic_light_visuals to find
            # icon_item using icon_id is no longer necessary as icon_item_from_dict is directly available.

            if found_icon_item and found_text_item:
                 # Update tooltip AND text color
                 self.map_viewer.update_traffic_light_visual_state(found_icon_item, found_text_item, traffic_light_instance.current_state) # Pass text_item
                 # Update countdown immediately on state change as well
                 self.map_viewer.update_traffic_light_countdown(found_text_item, traffic_light_instance.get_remaining_time())
            else:
                 print("Warning: Could not find visual item for updated traffic light instance.")


        # Recalculate paths since weights have changed
        self._recalculate_effects_and_path()

    def _update_traffic_light_countdown_display(self, remaining_seconds: int):
        """Slot called when a TrafficLightInstance emits remaining time."""
        sender_instance = self.sender()
        if not isinstance(sender_instance, TrafficLightInstance): return

        # Find the text item associated with this instance
        found_text_item = None
        # Unpack all four items, using _ for items not directly used in this loop's logic
        for instance, text_item, _, _ in self._active_traffic_lights.values():
            if instance == sender_instance:
                found_text_item = text_item
                break

        if found_text_item:
            self.map_viewer.update_traffic_light_countdown(found_text_item, remaining_seconds)
        # else: # This might print too often if an instance is somehow detached
        #     print("Warning: Could not find text item for countdown update.")


    # --- Recalculation Logic ---
    def _recalculate_effects_and_path(self):
        if not self.pathfinder or not self.pathfinder.graph: # Ensure graph exists
            print("DEBUG: MainWindow: Pathfinder or graph not available for recalculation.")
            return

        print("DEBUG: MainWindow: Entering _recalculate_effects_and_path.")
        self.reset_graph_weights() # CRITICAL: Ensure this is called first

        # --- Define a specific edge to trace for debugging ---
        debug_edge_u = None # "node_A" # Set to an actual node name to trace
        debug_edge_v = None # "node_B" # Set to an actual node name to trace

        if debug_edge_u and debug_edge_v and self.pathfinder.graph.has_edge(debug_edge_u, debug_edge_v):
            print(f"DEBUG TRACE ({debug_edge_u}-{debug_edge_v}): Weight AFTER reset_graph_weights: {self.pathfinder.graph[debug_edge_u][debug_edge_v].get('weight')}")
        elif debug_edge_u and debug_edge_v:
            print(f"DEBUG TRACE: Edge ({debug_edge_u}-{debug_edge_v}) not found in graph for tracing after reset.")


        # --- Apply Traffic Jam Effects ---
        for line_item in self.map_viewer.traffic_jam_lines:
            data = line_item.data(EFFECT_DATA_KEY)
            if data and data.get("type") == "traffic":
                p1 = data["start"]
                p2 = data["end"]
                weight_increase = data["weight"]
                affected_edges = self.pathfinder.find_edges_near_line(p1, p2, self._effect_application_threshold)
                for u, v in affected_edges:
                    self.pathfinder.modify_edge_weight(u, v, add_weight=weight_increase)
                    if debug_edge_u and debug_edge_v and (u,v) == (debug_edge_u, debug_edge_v):
                        print(f"DEBUG TRACE ({debug_edge_u}-{debug_edge_v}): Weight AFTER traffic jam: {self.pathfinder.graph[u][v].get('weight')}")

        # --- Apply Rain Area Effects ---
        for rect_item in self.map_viewer.rain_area_visuals:
            data = rect_item.data(EFFECT_DATA_KEY)
            if data and data.get("type") == "rain":
                rect = data["rect"]
                weight_increase = data["weight"]
                affected_edges = []
                for u_edge, v_edge in self.pathfinder.graph.edges():
                    pos_u_tuple = self.node_positions.get(u_edge)
                    pos_v_tuple = self.node_positions.get(v_edge)
                    if pos_u_tuple and pos_v_tuple:
                        edge_mid_x = (pos_u_tuple[0] + pos_v_tuple[0]) / 2
                        edge_mid_y = (pos_u_tuple[1] + pos_v_tuple[1]) / 2
                        if rect.contains(QPointF(edge_mid_x, edge_mid_y)):
                            affected_edges.append((u_edge, v_edge))
                for u, v in affected_edges:
                    self.pathfinder.modify_edge_weight(u, v, add_weight=weight_increase)
                    if debug_edge_u and debug_edge_v and (u,v) == (debug_edge_u, debug_edge_v):
                        print(f"DEBUG TRACE ({debug_edge_u}-{debug_edge_v}): Weight AFTER rain: {self.pathfinder.graph[u][v].get('weight')}")

        # --- Apply Block Way Effects ---
        for line_item in self.map_viewer.block_way_visuals:
            data = line_item.data(EFFECT_DATA_KEY)
            if data and data.get("type") == "block_way":
                p1 = data["start"]
                p2 = data["end"]
                affected_edges = self.pathfinder.find_edges_near_line(p1, p2, self._effect_application_threshold)
                for u, v in affected_edges:
                    self.pathfinder.modify_edge_weight(u, v, set_weight=float('inf'))
                    if debug_edge_u and debug_edge_v and (u,v) == (debug_edge_u, debug_edge_v):
                        print(f"DEBUG TRACE ({debug_edge_u}-{debug_edge_v}): Weight AFTER block_way: {self.pathfinder.graph[u][v].get('weight')}")
        
        # --- Apply Car Block Effects ---
        for marker_item in self.map_viewer.car_block_visuals:
            data = marker_item.data(EFFECT_DATA_KEY)
            if data and data.get("type") == "car_block":
                u, v = data["blocked_edge_nodes"]
                self.pathfinder.modify_edge_weight(u, v, set_weight=float('inf'))
                if debug_edge_u and debug_edge_v and (u,v) == (debug_edge_u, debug_edge_v):
                     print(f"DEBUG TRACE ({debug_edge_u}-{debug_edge_v}): Weight AFTER car_block: {self.pathfinder.graph[u][v].get('weight')}")


        # --- Apply Traffic Light Effects ---
        print(f"DEBUG: MainWindow: Processing {len(self._active_traffic_lights)} active traffic lights for recalculation.")
        for icon_id, (traffic_light_instance, text_item, icon_item, line_item) in self._active_traffic_lights.items():
            if not traffic_light_instance:
                continue

            current_tl_state = traffic_light_instance.current_state
            weight_modifier = traffic_light_instance.get_current_weight_modifier()

            # Get the effect line from the QGraphicsLineItem associated with this traffic light
            effect_qlinef = line_item.line()
            p1 = effect_qlinef.p1()
            p2 = effect_qlinef.p2()
            
            affected_edges_for_tl = self.pathfinder.find_edges_near_line(p1, p2, threshold=self._effect_application_threshold)

            if debug_edge_u and debug_edge_v and (debug_edge_u, debug_edge_v) in affected_edges_for_tl:
                print(f"DEBUG TRACE ({debug_edge_u}-{debug_edge_v}): Traffic light {icon_id} (State: {current_tl_state}) is affecting this edge.")
                print(f"DEBUG TRACE ({debug_edge_u}-{debug_edge_v}): Weight BEFORE this TL mod: {self.pathfinder.graph[debug_edge_u][debug_edge_v].get('weight')}")
                print(f"DEBUG TRACE ({debug_edge_u}-{debug_edge_v}): TL Modifier to ADD: {weight_modifier}")

            for u_edge, v_edge in affected_edges_for_tl:
                if self.pathfinder.graph.has_edge(u_edge,v_edge):
                    self.pathfinder.modify_edge_weight(u_edge, v_edge, add_weight=weight_modifier)

            if debug_edge_u and debug_edge_v and (debug_edge_u, debug_edge_v) in affected_edges_for_tl:
                 print(f"DEBUG TRACE ({debug_edge_u}-{debug_edge_v}): Weight AFTER this TL mod: {self.pathfinder.graph[debug_edge_u][debug_edge_v].get('weight')}")


        # --- Recalculate path if start and end points are set ---
        if self.start_node and self.end_node:
            print(f"DEBUG: MainWindow: Start ({self.start_node}) and End ({self.end_node}) nodes are set. Calling _trigger_pathfinding after all effects.")
            self._trigger_pathfinding()
        else:
            print("DEBUG: MainWindow: Start or End node not set. Pathfinding not triggered after recalculation.")
            self.map_viewer.clear_path()
        print("DEBUG: MainWindow: Exiting _recalculate_effects_and_path.")

    def reset_graph_weights(self):
        """Resets graph edge weights to their original values."""
        print("Resetting graph weights to original values...")
        if not self.pathfinder or not self._original_weights:
            print("  Cannot reset weights: Pathfinding not ready or original weights missing.")
            return

        for (u, v), original_weight in self._original_weights.items():
            if self.pathfinder.graph.has_edge(u, v):
                self.pathfinder.graph[u][v]['weight'] = original_weight
            # else: # Edge might have been removed (e.g., by map update later?)
            #     print(f"  Warning: Original edge ({u},{v}) not found during weight reset.")
        print(f"  Weights reset for {len(self._original_weights)} edges.")
        # Note: This does NOT stop traffic light timers. That happens on removal or full clear.

    def stop_all_traffic_light_timers(self):
        """Stops all active traffic light timers."""
        print("Stopping all traffic light timers...")
        for data_tuple in list(self._active_traffic_lights.values()):
            tl_instance = data_tuple[0] # The first element is the TrafficLightInstance
            if tl_instance: 
                tl_instance.stop()
        self._active_traffic_lights.clear() 
        print("All traffic light timers stopped and instances cleared.")


    def keyPressEvent(self, event: QKeyEvent):
        """Handle key presses, e.g., Escape to cancel drawing."""
        if event.key() == Qt.Key.Key_Escape:
            print("Escape pressed - Cancelling current drawing action.")
            # Deactivate any active drawing tool by unchecking its button
            if self.sidebar._traffic_tool_active:
                self.sidebar.traffic_jam_button.setChecked(False)
            elif self.sidebar._rain_tool_active:
                self.sidebar.rain_area_button.setChecked(False)
            elif self.sidebar._block_way_tool_active:
                self.sidebar.block_way_button.setChecked(False)
            elif self.sidebar._traffic_light_tool_active or self.map_viewer._is_drawing_traffic_light_line:
                 # If placing icon OR drawing line for traffic light
                 self.sidebar.traffic_light_button.setChecked(False) # This triggers the toggle(false) signal
                 # Explicitly clean up map viewer state as well
                 self.map_viewer.set_traffic_light_placement_mode(False)
            elif self.sidebar._place_car_block_drawing_active: # Check new state for drawing
                self.sidebar.place_car_block_button.setChecked(False) # Uncheck the place button
                # The map_viewer.set_car_mode_drawing_mode(False) should be called by the button's toggle signal


            # Clean up any temporary visuals in MapViewer
            self.map_viewer._cleanup_temp_drawing()
            # Restore default cursor and drag mode if not already done by set_*_mode(False)
            self.map_viewer.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.map_viewer.setCursor(Qt.CursorShape.ArrowCursor)

        else:
            super().keyPressEvent(event) # Pass other keys to the base class


    # --- Point Selection and Pathfinding Logic ---
    def _find_nearest_node(self, x, y):
        """Finds the nearest graph node to a given scene coordinate."""
        if not self.node_positions: return None
        min_dist_sq = float('inf')
        nearest_node = None
        for node_id, pos in self.node_positions.items():
            dist_sq = (pos[0] - x)**2 + (pos[1] - y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest_node = node_id
        # Add a threshold check if needed (e.g., don't snap if click is too far)
        # threshold_sq = 50**2 # Example: 50 pixels squared
        # if min_dist_sq > threshold_sq:
        #     return None
        return nearest_node

    def _handle_point_selected(self, point_type, x, y):
        """Handles clicks on the map for selecting start/end points."""
        # Store previous start/end to see if they changed for combo box updates
        prev_start_node = self.start_node
        prev_end_node = self.end_node

        if x == -1 and y == -1: # Special case indicating a point was cleared in MapViewer
             # This typically means a point was cleared programmatically or by specific action
             # not covered by clicking on the marker itself (which is handled below)
             if self.start_node is None and prev_start_node is not None: # Start point became None
                 self._update_combo_text_for_map_selection("start", None)
             if self.end_node is None and prev_end_node is not None: # End point became None
                 self._update_combo_text_for_map_selection("end", None)
             # Path clearing is handled by the caller or subsequent logic
             return


        nearest_node = self._find_nearest_node(x, y)
        if nearest_node is None:
            print("No nearby node found.")
            self.map_viewer.clear_temporary_point() # Clear visual feedback if no node
            return

        node_pos = self.node_positions[nearest_node]
        snapped_pos = QPointF(node_pos[0], node_pos[1])

        # Decide whether to set start or end point
        if self.start_node is None or self.start_node == nearest_node:
            # Set or reset start point
            if self.start_node == nearest_node: # Clicked on existing start node
                 self.start_node = None
                 # self.sidebar.start_label.setText("Start: Not Selected") # Updated by _update_combo_text
                 self.map_viewer.clear_permanent_point("start")
                 print(f"Start node {nearest_node} deselected.")
            elif nearest_node == self.end_node: # Clicked on end node while start is empty
                 print("Cannot set start node to the same as end node.")
                 self.map_viewer.clear_temporary_point()
                 return
            else:
                 self.start_node = nearest_node
                 # self.sidebar.start_label.setText(f"Start: Node {nearest_node}") # Updated by _update_combo_text
                 self.map_viewer.set_permanent_point("start", snapped_pos)
                 print(f"Start node set to {nearest_node} at ({snapped_pos.x():.1f}, {snapped_pos.y():.1f})")

        elif self.end_node is None or self.end_node == nearest_node:
             # Set or reset end point
             if self.end_node == nearest_node: # Clicked on existing end node
                 self.end_node = None
                 # self.sidebar.end_label.setText("End: Not Selected") # Updated by _update_combo_text
                 self.map_viewer.clear_permanent_point("end")
                 print(f"End node {nearest_node} deselected.")
             else: # Cannot set end node to the same as start node (already checked by start_node == nearest_node above)
                 self.end_node = nearest_node
                 # self.sidebar.end_label.setText(f"End: Node {nearest_node}") # Updated by _update_combo_text
                 self.map_viewer.set_permanent_point("end", snapped_pos)
                 print(f"End node set to {nearest_node} at ({snapped_pos.x():.1f}, {snapped_pos.y():.1f})")
        else:
            # Both start and end are set, maybe allow changing start? Or require clearing first?
            # Current logic: If both set, clicking selects a new start node.
             if nearest_node == self.end_node:
                 print("Cannot set start node to the same as end node.")
                 self.map_viewer.clear_temporary_point()
                 return
             else: # Set new start node
                 self.start_node = nearest_node
                 # self.sidebar.start_label.setText(f"Start: Node {nearest_node}") # Updated by _update_combo_text
                 self.map_viewer.set_permanent_point("start", snapped_pos)
                 print(f"Start node changed to {nearest_node} at ({snapped_pos.x():.1f}, {snapped_pos.y():.1f})")

        # Update combo box text and labels if nodes changed
        if self.start_node != prev_start_node:
            self._update_combo_text_for_map_selection("start", self.start_node)
        if self.end_node != prev_end_node:
            self._update_combo_text_for_map_selection("end", self.end_node)

        # Clear the temporary click marker now that we've handled the selection
        self.map_viewer.clear_temporary_point()

        # Trigger pathfinding if both points are now selected
        if self.start_node is not None and self.end_node is not None:
            self._trigger_pathfinding()
        else:
            self.map_viewer.clear_path() # Clear path if one point was deselected


    def _trigger_pathfinding(self):
        """Initiates pathfinding between the selected start and end nodes."""
        if self.start_node is None or self.end_node is None:
            QMessageBox.warning(self, "Pathfinding", "Please select both start and end points.")
            self.map_viewer.clear_path()
            return

        if not self.pathfinder:
            QMessageBox.critical(self, "Error", "Pathfinding engine not available.")
            return

        print(f"Finding path from {self.start_node} to {self.end_node}...")
        print(f"DEBUG: MainWindow: In _trigger_pathfinding from {self.start_node} to {self.end_node}.") # DEBUG
        try:
            # path_nodes, total_cost = self.pathfinder.find_path(self.start_node, self.end_node) # Old problematic line
            path_nodes = self.pathfinder.find_path(self.start_node, self.end_node) # Corrected line

            if path_nodes:
                # The 'total_cost' variable from the unpacking is no longer available here.
                # The cost is calculated below.
                # print(f"DEBUG: MainWindow: Path found: {path_nodes}, Cost: {total_cost}. Drawing path.") # DEBUG # Old debug print
                
                # Calculate path cost if path is found
                cost = 0.0 # Initialize cost as float
                if self.pathfinder.graph and len(path_nodes) > 1: # path_nodes is already confirmed to be truthy
                    for i in range(len(path_nodes) - 1):
                        u, v = path_nodes[i], path_nodes[i+1]
                        if self.pathfinder.graph.has_edge(u, v):
                            cost += self.pathfinder.graph[u][v].get('weight', 0)
                        else:
                            # This case should ideally not happen if path is valid
                            print(f"Warning: Edge {u}-{v} not found in graph while calculating cost.")
                            cost = float('inf') # Indicate an issue with the path or graph
                            break
                # If path_nodes has 0 or 1 node (e.g. start=end), cost remains 0.0, which is correct.
                
                print(f"DEBUG: MainWindow: Path found: {path_nodes}, Calculated Cost: {cost:.2f}. Drawing path.") # Updated debug print using calculated cost
                
                print(f"Path found: {path_nodes} with cost {cost:.2f}")
                self.map_viewer.draw_path(path_nodes, self.node_positions)
            else:
                print("DEBUG: MainWindow: Path not found by pathfinder in _trigger_pathfinding.") # DEBUG
                print("No path found.")
                QMessageBox.information(self, "Pathfinding", f"No path found between node {self.start_node} and {self.end_node}.")
                self.map_viewer.clear_path()
        except Exception as e:
            print(f"Error during pathfinding: {e}")
            QMessageBox.critical(self, "Pathfinding Error", f"An error occurred: {e}")
            self.map_viewer.clear_path()

    def closeEvent(self, event):
        """Ensure timers are stopped when the window closes."""
        print("Main window closing, stopping timers...")
        self.stop_all_traffic_light_timers()
        super().closeEvent(event)


if __name__ == "__main__":
    # Make sure QApplication is created before MainWindow
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

