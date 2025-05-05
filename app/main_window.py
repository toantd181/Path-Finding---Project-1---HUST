import sys # Import sys
import os  # Import os
import numpy as np # Import numpy
from PyQt6.QtWidgets import (QApplication, QMainWindow, QHBoxLayout, QWidget,
                             QMessageBox, QGraphicsScene, QGraphicsRectItem,
                             QGraphicsPixmapItem, QGraphicsLineItem, QGraphicsSimpleTextItem) # Add graphics items used
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer # Added QTimer
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
            self.pathfinder = Pathfinding(db_file)
            print("Pathfinding engine initialized.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to initialize pathfinding: {e}")
            print(f"Error initializing Pathfinding: {e}")
            # Consider disabling features if pathfinder fails

        self.start_node = None
        self.end_node = None
        self.node_positions = {}
        if self.pathfinder:
            self.node_positions = self.pathfinder.get_node_positions()
            print(f"Loaded {len(self.node_positions)} node positions.")
            # Store original weights for resetting
            # Correctly unpack u, v, data when data=True
            self._original_weights = {(u, v): data['weight'] for u, v, data in self.pathfinder.graph.edges(data=True)}
            print(f"Stored original weights for {len(self._original_weights)} edges.")

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

        # Drawing results / Effect placement
        self.map_viewer.traffic_line_drawn.connect(self.handle_traffic_line)
        self.map_viewer.rain_area_defined.connect(self.handle_rain_area)
        self.map_viewer.block_way_drawn.connect(self.handle_block_way)
        # Connect new traffic light signals
        # self.map_viewer.traffic_light_line_drawn.connect(self.handle_traffic_light_finalized) # Old signal
        self.map_viewer.traffic_light_visuals_created.connect(self.handle_traffic_light_finalized) # New signal - This connection is now correct

        # Effect removal / changes
        self.map_viewer.effects_changed.connect(self._handle_effects_changed) # Connect effect removal


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
                instance, text_item = self._active_traffic_lights[icon_id]
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

    # --- Traffic Light Handling --- Modified Method ---
    def handle_traffic_light_finalized(self, icon_pos: QPointF, line_start: QPointF, line_end: QPointF,
                                       icon_item: QGraphicsPixmapItem, line_item: QGraphicsLineItem, text_item: QGraphicsSimpleTextItem):
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
        self._active_traffic_lights[icon_id] = (traffic_light_instance, text_item)
        print(f"Stored data and started timer for traffic light (icon id: {icon_id})")

        # Update the visual state immediately (e.g., tooltip, initial countdown, text color)
        self.map_viewer.update_traffic_light_visual_state(icon_item, text_item, traffic_light_instance.current_state) # Pass text_item
        self.map_viewer.update_traffic_light_countdown(text_item, traffic_light_instance.get_remaining_time())

        # --- Recalculate all effects and path ---
        self._recalculate_effects_and_path()


    def _traffic_light_state_updated(self):
        """Slot called when a TrafficLightInstance changes state."""
        sender_instance = self.sender()
        if not isinstance(sender_instance, TrafficLightInstance): return

        print(f"Traffic light state changed to: {sender_instance.current_state}. Recalculating...")

        # Find the corresponding visual icon and text item to update appearance/tooltip
        found_icon_item = None
        found_text_item = None
        for icon_id, (instance, text_item) in self._active_traffic_lights.items():
             if instance == sender_instance:
                 # Need to find the icon_item corresponding to this icon_id
                 # Iterate through MapViewer's visuals (tuple structure: icon, line, text, data)
                 for ic, _, tx, _ in self.map_viewer.traffic_light_visuals:
                     if id(ic) == icon_id:
                         found_icon_item = ic
                         # Use the text_item directly associated with the instance in our dict
                         found_text_item = text_item
                         break
                 break

        if found_icon_item and found_text_item:
             # Update tooltip AND text color
             self.map_viewer.update_traffic_light_visual_state(found_icon_item, found_text_item, sender_instance.current_state) # Pass text_item
             # Update countdown immediately on state change as well
             self.map_viewer.update_traffic_light_countdown(found_text_item, sender_instance.get_remaining_time())
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
        for instance, text_item in self._active_traffic_lights.values():
            if instance == sender_instance:
                found_text_item = text_item
                break

        if found_text_item:
            self.map_viewer.update_traffic_light_countdown(found_text_item, remaining_seconds)
        # else: # This might print too often if an instance is somehow detached
        #     print("Warning: Could not find text item for countdown update.")


    # --- Recalculation Logic ---
    def _recalculate_effects_and_path(self):
        """Resets weights and reapplies effects from all current visuals, including dynamic traffic lights."""
        print("Recalculating all effects...")
        if not self.pathfinder or not self._original_weights:
            print("  Skipping recalculation: Pathfinding not ready or original weights missing.")
            return

        # 1. Reset all weights to original values
        self.reset_graph_weights() # This now only resets weights, timers handled separately

        # --- Apply Static Effects First ---

        # 2. Reapply traffic jam effects
        print(f"Reapplying effects from {len(self.map_viewer.traffic_jam_lines)} traffic lines.")
        for line_item in self.map_viewer.traffic_jam_lines:
            item_data = line_item.data(EFFECT_DATA_KEY)
            if item_data and item_data.get("type") == "traffic":
                weight_increase = item_data.get("weight", 0)
                effect_start = item_data.get("start")
                effect_end = item_data.get("end")
                if effect_start and effect_end:
                    affected_count = 0
                    # Iterate over a copy of edges
                    for u, v in list(self.pathfinder.graph.edges()):
                        if not self.pathfinder.graph.has_edge(u,v): continue
                        try:
                            pos_u = QPointF(*self.node_positions[u])
                            pos_v = QPointF(*self.node_positions[v])
                            if _segments_intersect(effect_start, effect_end, pos_u, pos_v):
                                current_weight = self.pathfinder.graph[u][v].get('weight', 0)
                                if current_weight != np.inf:
                                    self.pathfinder.graph[u][v]['weight'] = max(0, current_weight + weight_increase) # Ensure non-negative
                                    affected_count += 1
                        except KeyError as e:
                            print(f"  Warning: Node position not found for {e} while reapplying traffic.")
                        except Exception as e:
                            print(f"  Error processing edge ({u}, {v}) for traffic reapplication: {e}")
                    if affected_count > 0: print(f"  Applied traffic weight +{weight_increase} to {affected_count} intersecting edges.")
                else:
                    print("  Warning: Missing data on traffic line item.")

        # 3. Reapply rain effects
        print(f"Reapplying effects from {len(self.map_viewer.rain_area_visuals)} rain areas.")
        for area_item in self.map_viewer.rain_area_visuals:
            item_data = area_item.data(EFFECT_DATA_KEY)
            if item_data and item_data.get("type") == "rain":
                weight_increase = item_data.get("weight", 0)
                area_rect = item_data.get("rect")
                if area_rect:
                    affected_count = 0
                    for u, v in list(self.pathfinder.graph.edges()):
                        if not self.pathfinder.graph.has_edge(u,v): continue
                        try:
                            pos_u = self.node_positions[u]
                            pos_v = self.node_positions[v]
                            mid_x = (pos_u[0] + pos_v[0]) / 2
                            mid_y = (pos_u[1] + pos_v[1]) / 2
                            edge_midpoint = QPointF(mid_x, mid_y)
                            if area_rect.contains(edge_midpoint):
                                current_weight = self.pathfinder.graph[u][v].get('weight', 0)
                                if current_weight != np.inf:
                                    self.pathfinder.graph[u][v]['weight'] = max(0, current_weight + weight_increase)
                                    affected_count += 1
                        except KeyError as e:
                             print(f"  Warning: Node position not found for {e} while reapplying rain.")
                        except Exception as e:
                             print(f"  Error processing edge ({u}, {v}) for rain reapplication: {e}")
                    if affected_count > 0: print(f"  Applied rain weight +{weight_increase} to {affected_count} edges in area.")
                else:
                    print("  Warning: Missing data on rain area item.")

        # 4. Reapply block way effects
        print(f"Reapplying effects from {len(self.map_viewer.block_way_visuals)} block way lines.")
        for block_item in self.map_viewer.block_way_visuals:
            item_data = block_item.data(EFFECT_DATA_KEY)
            if item_data and item_data.get("type") == "block_way":
                block_start = item_data.get("start")
                block_end = item_data.get("end")
                if block_start and block_end:
                    affected_count = 0
                    for u, v in list(self.pathfinder.graph.edges()):
                        if not self.pathfinder.graph.has_edge(u,v): continue
                        try:
                            pos_u = QPointF(*self.node_positions[u])
                            pos_v = QPointF(*self.node_positions[v])
                            if _segments_intersect(block_start, block_end, pos_u, pos_v):
                                self.pathfinder.graph[u][v]['weight'] = np.inf
                                affected_count += 1
                                # Block reverse edge too if it exists and graph is directed
                                # if self.pathfinder.graph.is_directed() and self.pathfinder.graph.has_edge(v, u):
                                #      self.pathfinder.graph[v][u]['weight'] = np.inf
                        except KeyError as e:
                             print(f"  Warning: Node position not found for {e} while reapplying block way.")
                        except Exception as e:
                             print(f"  Error processing edge ({u}, {v}) for block way reapplication: {e}")
                    if affected_count > 0: print(f"  Applied block (inf weight) to {affected_count} intersecting edges.")
                else:
                    print("  Warning: Missing data on block way item.")

        # --- Apply Dynamic Traffic Light Effects ---

        # 5. Reapply traffic light effects based on current state
        print(f"Reapplying effects from {len(self.map_viewer.traffic_light_visuals)} traffic lights.")
        # Iterate using the MapViewer's list as the source of truth for visuals
        # Tuple structure: (icon_item, line_item, text_item, data_dict)
        for icon_item, line_item, text_item, item_data in self.map_viewer.traffic_light_visuals:
            # Find the corresponding instance from our active dictionary using icon_id
            icon_id = id(icon_item)
            instance_tuple = self._active_traffic_lights.get(icon_id)

            if not instance_tuple:
                print(f"  Warning: No active instance found for traffic light icon id {icon_id}. Skipping.")
                continue

            instance, _ = instance_tuple # We only need the instance here
            # item_data is already retrieved from the loop

            if item_data and item_data.get("type") == "traffic_light":
                # instance = item_data.get("instance") # Already got instance from dict
                effect_start = item_data.get("line_start")
                effect_end = item_data.get("line_end")

                if instance and effect_start and effect_end:
                    # Get the CURRENT weight modifier from the instance's state
                    weight_modifier = instance.get_current_weight_modifier()
                    current_state_name = instance.current_state

                    affected_count = 0
                    for u, v in list(self.pathfinder.graph.edges()):
                        if not self.pathfinder.graph.has_edge(u,v): continue
                        try:
                            pos_u = QPointF(*self.node_positions[u])
                            pos_v = QPointF(*self.node_positions[v])
                            # Check intersection with the traffic light's effect line
                            if _segments_intersect(effect_start, effect_end, pos_u, pos_v):
                                current_weight = self.pathfinder.graph[u][v].get('weight', 0)
                                if current_weight != np.inf: # Don't modify blocked roads
                                    # Apply the modifier based on the light's current state
                                    self.pathfinder.graph[u][v]['weight'] = max(0, current_weight + weight_modifier)
                                    affected_count += 1
                        except KeyError as e:
                             print(f"  Warning: Node position not found for {e} while reapplying traffic light.")
                        except Exception as e:
                             print(f"  Error processing edge ({u}, {v}) for traffic light reapplication: {e}")
                    if affected_count > 0: print(f"  Applied traffic light ({current_state_name}) weight mod +{weight_modifier:.1f} to {affected_count} intersecting edges.")
                else:
                    print(f"  Warning: Missing data or instance on traffic light item (icon id: {icon_id}).")
            else:
                 print(f"  Warning: Item data missing or not type 'traffic_light' for icon id: {icon_id}.")


        # 6. Recalculate and draw path if possible
        if self.start_node and self.end_node:
             print("Recalculating path after effects update...")
             self._trigger_pathfinding()
        else:
             self.map_viewer.clear_path() # Clear path if no start/end

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
        # Iterate through a copy of values because stopping might trigger signals? (unlikely but safer)
        for instance, text_item in list(self._active_traffic_lights.values()):
            instance.stop()
        self._active_traffic_lights.clear() # Clear the active instances dictionary
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
        # If point_type is None, it means a click happened, find nearest node.
        # If point_type is "start" or "end", it might be a direct call (less likely now)
        if x == -1 and y == -1: # Special case indicating a point was cleared in MapViewer
             if self.start_node and not self.map_viewer._permanent_start_item:
                 self.start_node = None
                 self.sidebar.start_label.setText("Start: Not Selected")
                 print("Start point cleared.")
             if self.end_node and not self.map_viewer._permanent_end_item:
                 self.end_node = None
                 self.sidebar.end_label.setText("End: Not Selected")
                 print("End point cleared.")
             # Path is cleared in MapViewer's handler, recalculation not needed unless effects exist
             # self._recalculate_effects_and_path() # Recalc might be needed if effects depend on start/end later
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
                 self.sidebar.start_label.setText("Start: Not Selected")
                 self.map_viewer.clear_permanent_point("start")
                 print(f"Start node {nearest_node} deselected.")
            elif nearest_node == self.end_node: # Clicked on end node while start is empty
                 print("Cannot set start node to the same as end node.")
                 self.map_viewer.clear_temporary_point()
                 return
            else:
                 self.start_node = nearest_node
                 self.sidebar.start_label.setText(f"Start: Node {nearest_node}")
                 self.map_viewer.set_permanent_point("start", snapped_pos)
                 print(f"Start node set to {nearest_node} at ({snapped_pos.x():.1f}, {snapped_pos.y():.1f})")

        elif self.end_node is None or self.end_node == nearest_node:
             # Set or reset end point
             if self.end_node == nearest_node: # Clicked on existing end node
                 self.end_node = None
                 self.sidebar.end_label.setText("End: Not Selected")
                 self.map_viewer.clear_permanent_point("end")
                 print(f"End node {nearest_node} deselected.")
             # Cannot set end node to the same as start node (already checked by start_node == nearest_node above)
             # elif nearest_node == self.start_node: # Redundant check
             #     print("Cannot set end node to the same as start node.")
             #     self.map_viewer.clear_temporary_point()
             #     return
             else:
                 self.end_node = nearest_node
                 self.sidebar.end_label.setText(f"End: Node {nearest_node}")
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
                 self.sidebar.start_label.setText(f"Start: Node {nearest_node}")
                 self.map_viewer.set_permanent_point("start", snapped_pos)
                 print(f"Start node changed to {nearest_node} at ({snapped_pos.x():.1f}, {snapped_pos.y():.1f})")


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
        try:
            # Ensure weights are up-to-date before finding path
            # Note: _recalculate_effects_and_path already calls this if effects exist
            # If no effects were added/changed, weights should still be correct (original or last calculated)

            path, cost = self.pathfinder.find_shortest_path(self.start_node, self.end_node)

            if path:
                print(f"Path found: {path} with cost {cost:.2f}")
                self.map_viewer.draw_path(path, self.node_positions)
            else:
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

