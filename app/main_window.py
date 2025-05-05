import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QHBoxLayout, QWidget,
                             QMessageBox, QGraphicsScene, QGraphicsRectItem) # Added QGraphicsRectItem
from PyQt6.QtCore import Qt, QPointF, QRectF # QKeyEvent moved to QtGui
from PyQt6.QtGui import QColor, QBrush, QPen, QKeyEvent # Added QKeyEvent here
from .map_viewer import MapViewer, EFFECT_DATA_KEY # Import MapViewer and the data key
from .pathfinding import Pathfinding
from .sidebar import Sidebar
import os
import math

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Offline Pathfinding App")
        self.setGeometry(100, 100, 1000, 600)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # --- Sidebar ---
        self.sidebar = Sidebar()
        self.sidebar.find_path_button.clicked.connect(self._trigger_pathfinding)

        # --- Scene and Map Viewer ---
        self.scene = QGraphicsScene(self) # Create scene here
        map_file = os.path.join(os.path.dirname(__file__), "assets", "map.png")
        # Pass the scene to MapViewer
        self.map_viewer = MapViewer(map_file, self._handle_point_selected, self.scene)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.map_viewer, 1) # Give map viewer more space

        # --- Pathfinding Initialization ---
        db_file = os.path.join(os.path.dirname(__file__), "data", "graph.db")
        try:
            self.pathfinder = Pathfinding(db_file)
            self._original_edge_weights = {
                (u, v): data['weight']
                for u, v, data in self.pathfinder.graph.edges(data=True)
            }
            # Store reverse edges too if graph is undirected and weights might differ
            # Or ensure Pathfinding handles undirected nature internally
        except Exception as e:
             QMessageBox.critical(self, "Error", f"Failed to initialize pathfinder: {e}")
             # Consider exiting or disabling pathfinding features
             # sys.exit(1) # Maybe too drastic?
             self.pathfinder = None # Disable pathfinding
             self._original_edge_weights = {}

        self.start_node = None
        self.end_node = None
        self.node_positions = {}
        if self.pathfinder: # Only get positions if pathfinder loaded
             self.node_positions = {
                 name: data['pos']
                 for name, data in self.pathfinder.graph.nodes(data=True)
             }

        # --- Graphics Items (managed by MapViewer, but MainWindow coordinates effects) ---
        # self._rain_overlay_item = None # Now managed within MapViewer's list

        # --- Connect Signals ---
        # Tools
        self.sidebar.traffic_tool_activated.connect(self.map_viewer.set_traffic_drawing_mode)
        self.sidebar.rain_tool_activated.connect(self.map_viewer.set_rain_drawing_mode)
        # Drawing results
        self.map_viewer.traffic_line_drawn.connect(self.handle_traffic_line)
        self.map_viewer.rain_area_defined.connect(self.handle_rain_area)
        # Effect removal
        self.map_viewer.effects_changed.connect(self._recalculate_effects_and_path) # Connect new signal


    def handle_traffic_line(self, start_point, end_point):
        """Handles the line drawn in traffic mode: Applies weights and stores data."""
        if not self.pathfinder: return

        traffic_weight_increase = self.sidebar.traffic_tool.get_weight()
        print(f"Applying traffic weight increase: {traffic_weight_increase} for line {start_point} to {end_point}")

        # --- Find affected edges (Placeholder - needs proper geometry check) ---
        # This simple midpoint check is inaccurate for lines.
        # A real implementation needs line-segment intersection checks.
        affected_edges_count = 0
        for u, v, data in self.pathfinder.graph.edges(data=True):
             # Placeholder: Apply if midpoint is near the drawn line (very rough)
             # A proper check involves line segment intersection geometry
             # For now, we just apply based on the signal being received
             pass # Apply logic moved to _recalculate_effects_and_path

        # --- Store data on the corresponding visual item ---
        # Find the last added traffic line item in MapViewer
        if self.map_viewer.traffic_jam_lines:
            last_line_item = self.map_viewer.traffic_jam_lines[-1]
            line_data = {
                "type": "traffic",
                "weight": traffic_weight_increase,
                "start": start_point, # Store geometry for recalculation
                "end": end_point
            }
            last_line_item.setData(EFFECT_DATA_KEY, line_data)
            print(f"Stored data on traffic line item: {line_data}")
        else:
            print("Warning: Could not find traffic line item to store data on.")

        # --- Recalculate all effects and path ---
        self._recalculate_effects_and_path()


    def handle_rain_area(self, area_rect: QRectF):
        """Handles the rectangle drawn for rain: Applies weights and stores data."""
        if not self.pathfinder: return

        rain_weight_increase = self.sidebar.rain_tool.get_weight_increase()
        print(f"Applying rain weight increase: {rain_weight_increase} for area {area_rect}")

        # Apply weight changes (logic moved to _recalculate_effects_and_path)

        # --- Store data on the corresponding visual item ---
        if self.map_viewer.rain_area_visuals:
            last_rain_item = self.map_viewer.rain_area_visuals[-1]
            area_data = {
                "type": "rain",
                "weight": rain_weight_increase,
                "rect": area_rect # Store geometry for recalculation
            }
            last_rain_item.setData(EFFECT_DATA_KEY, area_data)
            print(f"Stored data on rain area item: {area_data}")
        else:
             print("Warning: Could not find rain area item to store data on.")

        # Store area data in the tool (optional, maybe not needed if stored on item)
        # self.sidebar.rain_tool.set_area(area_rect) # If tool needs to know the last area

        # --- Recalculate all effects and path ---
        self._recalculate_effects_and_path()


    def _recalculate_effects_and_path(self):
        """Resets weights and reapplies effects from all current visuals."""
        print("Recalculating all effects...")
        if not self.pathfinder: return

        # 1. Reset all weights to original values
        self.reset_graph_weights() # Resets the graph weights in self.pathfinder

        # 2. Reapply traffic effects from remaining visuals
        print(f"Reapplying effects from {len(self.map_viewer.traffic_jam_lines)} traffic lines.")
        for line_item in self.map_viewer.traffic_jam_lines:
            item_data = line_item.data(EFFECT_DATA_KEY)
            if item_data and item_data.get("type") == "traffic":
                weight_increase = item_data.get("weight", 0)
                start_point = item_data.get("start") # QPointF
                end_point = item_data.get("end")     # QPointF
                if start_point and end_point:
                    # --- Apply weight increase to edges intersecting the line ---
                    # Placeholder: Needs actual geometric intersection logic
                    # This example applies to *all* edges for demonstration
                    affected_count = 0
                    for u, v in self.pathfinder.graph.edges():
                         # --- Replace with actual intersection check ---
                         # if line_intersects_edge(start_point, end_point, u, v, self.node_positions):
                         # For now, apply to all edges as a placeholder
                         current_weight = self.pathfinder.graph[u][v]['weight']
                         self.pathfinder.graph[u][v]['weight'] = current_weight + weight_increase
                         affected_count +=1
                    print(f"  (Placeholder) Applied traffic weight +{weight_increase} to {affected_count} edges for one line.")
                else:
                    print("  Warning: Missing data on traffic line item.")


        # 3. Reapply rain effects from remaining visuals
        print(f"Reapplying effects from {len(self.map_viewer.rain_area_visuals)} rain areas.")
        for area_item in self.map_viewer.rain_area_visuals:
            item_data = area_item.data(EFFECT_DATA_KEY)
            if item_data and item_data.get("type") == "rain":
                weight_increase = item_data.get("weight", 0)
                area_rect = item_data.get("rect") # QRectF
                if area_rect:
                    affected_count = 0
                    for u, v in self.pathfinder.graph.edges():
                        try:
                            pos_u = self.node_positions[u]
                            pos_v = self.node_positions[v]
                            mid_x = (pos_u[0] + pos_v[0]) / 2
                            mid_y = (pos_u[1] + pos_v[1]) / 2
                            edge_midpoint = QPointF(mid_x, mid_y)

                            if area_rect.contains(edge_midpoint):
                                current_weight = self.pathfinder.graph[u][v]['weight']
                                self.pathfinder.graph[u][v]['weight'] = current_weight + weight_increase
                                affected_count += 1
                        except KeyError as e:
                             print(f"  Warning: Node position not found for {e} while reapplying rain.")
                        except Exception as e:
                             print(f"  Error processing edge ({u}, {v}) for rain reapplication: {e}")
                    print(f"  Applied rain weight +{weight_increase} to {affected_count} edges for area {area_rect.topLeft()}.")
                else:
                    print("  Warning: Missing data on rain area item.")

        # 4. Recalculate and draw path if possible
        if self.start_node and self.end_node:
             print("Recalculating path after effects update...")
             self._trigger_pathfinding()
        else:
             self.map_viewer.clear_path() # Clear path if no start/end


    def reset_graph_weights(self):
        """Resets all edge weights to their original values. Does NOT clear visuals."""
        if not self.pathfinder or not self._original_edge_weights:
             print("Cannot reset weights: Pathfinder or original weights missing.")
             return

        print("Resetting graph weights to original values...")
        affected_count = 0
        for (u, v), original_weight in self._original_edge_weights.items():
            if self.pathfinder.graph.has_edge(u, v):
                if self.pathfinder.graph[u][v]['weight'] != original_weight:
                    self.pathfinder.graph[u][v]['weight'] = original_weight
                    affected_count += 1
            # Handle reverse edge if graph is treated as undirected here
            # elif self.pathfinder.graph.has_edge(v, u) and (v,u) not in self._original_edge_weights:
            #     if self.pathfinder.graph[v][u]['weight'] != original_weight:
            #        self.pathfinder.graph[v][u]['weight'] = original_weight
            #        affected_count += 1

        print(f"Reset weights for {affected_count} edges.")
        # DO NOT clear visual overlays here - that's handled separately

        # Clear the stored area in the tool (if it represents the 'last' area)
        # This might be confusing now, consider removing tool state storage
        # if hasattr(self.sidebar, 'rain_tool'):
        #     self.sidebar.rain_tool.clear_area()


    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events for the main window."""
        # --- Clear All Rain Effects (Visuals and Weights) ---
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace: # Changed Qt.Key.Delete and Qt.Key.Backspace
            print("Delete/Backspace key pressed - Clearing ALL effects")

            # 1. Clear Visuals
            self.map_viewer.clear_rain_areas()
            self.map_viewer.clear_traffic_jams()

            # 2. Reset Weights and Recalculate Path
            self._recalculate_effects_and_path() # This resets weights and reapplies remaining (none)

            event.accept()
            return

        # --- Add other key bindings here if needed ---
        # Example: Reset all effects with 'R' (same as Delete/Backspace now)
        # if event.key() == Qt.Key.R:
        #     print("R key pressed - Resetting all graph weights and effects")
        #     self.map_viewer.clear_rain_areas()
        #     self.map_viewer.clear_traffic_jams()
        #     self._recalculate_effects_and_path()
        #     event.accept()
        #     return

        # Call base class implementation if the key wasn't handled here
        super().keyPressEvent(event)


    # --- Point Selection and Pathfinding Logic ---
    # (_find_nearest_node, _handle_point_selected, _trigger_pathfinding)
    # Need to ensure _handle_point_selected uses MapViewer's new point methods

    def _find_nearest_node(self, x, y):
        """Finds the nearest graph node to the given coordinates."""
        if not self.pathfinder: return None
        nearest_node = None
        min_dist_sq = float('inf')

        for node_name, pos in self.node_positions.items():
            dist_sq = (pos[0] - x)**2 + (pos[1] - y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest_node = node_name

        threshold_pixels = 50 # Max distance in pixels to snap to a node
        if min_dist_sq > threshold_pixels**2:
            return None # No node close enough
        return nearest_node

    def _handle_point_selected(self, point_type, x, y):
        """Handles the selection signal from MapViewer, finds node, updates state."""
        nearest_node = self._find_nearest_node(x, y)

        if not nearest_node:
            print(f"No node found near click at ({x:.2f}, {y:.2f})")
            # Tell MapViewer to clear the temporary point feedback
            self.map_viewer.clear_temporary_point(point_type)
            # Reset the node if one was previously selected for this type
            if point_type == "start":
                self.start_node = None
                self.sidebar.start_label.setText("Start: Not Selected")
                # Optionally clear the permanent marker if user clicks far away
                # if self.map_viewer._permanent_start_item:
                #    self.scene.removeItem(self.map_viewer._permanent_start_item)
                #    self.map_viewer._permanent_start_item = None
            elif point_type == "end":
                self.end_node = None
                self.sidebar.end_label.setText("End: Not Selected")
                # Optionally clear the permanent marker
                # if self.map_viewer._permanent_end_item:
                #    self.scene.removeItem(self.map_viewer._permanent_end_item)
                #    self.map_viewer._permanent_end_item = None
            self.map_viewer.clear_path() # Clear path if selection fails
            return

        print(f"Point selected: {point_type} snapped to node {nearest_node}")
        node_x, node_y = self.node_positions[nearest_node] # Get node's graph position

        if point_type == "start":
            self.start_node = nearest_node
            self.sidebar.start_label.setText(f"Start: {self.start_node}")
            # Tell MapViewer to finalize the start point at the node's position
            self.map_viewer.set_permanent_point("start", QPointF(node_x, node_y))
        elif point_type == "end":
            self.end_node = nearest_node
            self.sidebar.end_label.setText(f"End: {self.end_node}")
            # Tell MapViewer to finalize the end point at the node's position
            self.map_viewer.set_permanent_point("end", QPointF(node_x, node_y))

        # Trigger pathfinding only via button now
        # if self.start_node and self.end_node:
        #     self._trigger_pathfinding()


    def _trigger_pathfinding(self):
        """Finds and draws the path if start and end nodes are set."""
        if not self.pathfinder:
             QMessageBox.warning(self, "Error", "Pathfinder not initialized.")
             return
        if self.start_node and self.end_node:
            print(f"Finding path from {self.start_node} to {self.end_node}")
            # Pass the *current* graph state to find_path
            path = self.pathfinder.find_path(self.start_node, self.end_node)
            if path:
                print(f"Path found: {path}")
                # Pass current node positions
                self.map_viewer.draw_path(path, self.node_positions)
            else:
                print("No path could be found between the selected nodes.")
                QMessageBox.warning(self, "Pathfinding", f"No path found between {self.start_node} and {self.end_node}")
                self.map_viewer.clear_path() # Clear previous path if new search fails
        else:
             QMessageBox.information(self, "Pathfinding", "Please select both a start and an end point.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

