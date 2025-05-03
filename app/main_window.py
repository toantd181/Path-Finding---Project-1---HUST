import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget, QMessageBox
from .map_viewer import MapViewer
from .pathfinding import Pathfinding
from .sidebar import Sidebar # Import the new Sidebar class
import os
import math # Import math for distance calculation
# Import Qt for colors
from PyQt6.QtCore import Qt, QPointF # Make sure QPointF is imported

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
        # Connect the button's clicked signal to the pathfinding method
        self.sidebar.find_path_button.clicked.connect(self._trigger_pathfinding)

        # --- Map Viewer ---
        map_file = os.path.join(os.path.dirname(__file__), "assets", "map.png")
        self.map_viewer = MapViewer(map_file, self._handle_point_selected)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.map_viewer, 1)

        db_file = os.path.join(os.path.dirname(__file__), "data", "graph.db")
        try:
            self.pathfinder = Pathfinding(db_file)
        except FileNotFoundError as e:
             QMessageBox.critical(self, "Error", str(e))
             sys.exit(1)
        except Exception as e:
             QMessageBox.critical(self, "Error", f"Failed to initialize pathfinder: {e}")
             sys.exit(1)

        self.start_node = None
        self.end_node = None
        self.node_positions = {name: data['pos'] for name, data in self.pathfinder.graph.nodes(data=True)}

        # Connect the sidebar toggle signal to the map viewer's mode switch
        self.sidebar.traffic_tool_activated.connect(self.map_viewer.set_traffic_drawing_mode)

        # Connect the map viewer's drawn line signal to your handler function
        self.map_viewer.traffic_line_drawn.connect(self.handle_traffic_line) # Replace handle_traffic_line with your actual handler

    # Add the missing handler method
    def handle_traffic_line(self, start_point, end_point):
        """Handles the line drawn in traffic mode."""
        # Placeholder implementation: Print the coordinates for now
        print(f"Traffic line drawn from {start_point} to {end_point}")
        # TODO: Implement logic to find affected edges and update weights
        # 1. Find nearest nodes to start_point and end_point
        # 2. Identify edges between/near these nodes that intersect the drawn line
        # 3. Update the weight of these edges in self.pathfinder.graph
        # 4. Potentially redraw the map or clear existing paths if weights change significantly

    def _find_nearest_node(self, x, y):
        """Finds the nearest graph node to the given coordinates."""
        nearest_node = None
        min_dist_sq = float('inf')

        for node_name, pos in self.node_positions.items():
            dist_sq = (pos[0] - x)**2 + (pos[1] - y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest_node = node_name

        threshold = 50**2
        if min_dist_sq > threshold:
            return None
        return nearest_node

    def _handle_point_selected(self, point_type, x, y):
        """Handles the selection of a point on the map by finding the nearest node."""
        nearest_node = self._find_nearest_node(x, y)
        if not nearest_node:
            print(f"No node found near click at ({x:.2f}, {y:.2f})")
            # Optionally clear the temporary point if too far
            if point_type == "start" and self.map_viewer.start_point_item:
                 self.map_viewer.scene.removeItem(self.map_viewer.start_point_item)
                 self.map_viewer.start_point_item = None
            elif point_type == "end" and self.map_viewer.end_point_item:
                 self.map_viewer.scene.removeItem(self.map_viewer.end_point_item)
                 self.map_viewer.end_point_item = None
            return

        print(f"Point selected: {point_type} near node {nearest_node} at ({x:.2f}, {y:.2f})")
        node_x, node_y = self.node_positions[nearest_node] # Get node position

        if point_type == "start":
            self.start_node = nearest_node
            # Update sidebar label
            self.sidebar.start_label.setText(f"Start: {self.start_node}")
            # Remove the temporary point drawn on click
            if self.map_viewer.start_point_item:
                self.map_viewer.scene.removeItem(self.map_viewer.start_point_item)
            # Draw the point snapped to the node using the existing draw_point method
            self.map_viewer.start_point_item = self.map_viewer.draw_point(QPointF(node_x, node_y), Qt.GlobalColor.green)
        elif point_type == "end":
            self.end_node = nearest_node
            # Update sidebar label
            self.sidebar.end_label.setText(f"End: {self.end_node}")
            # Remove the temporary point drawn on click
            if self.map_viewer.end_point_item:
                self.map_viewer.scene.removeItem(self.map_viewer.end_point_item)
            # Draw the point snapped to the node using the existing draw_point method
            self.map_viewer.end_point_item = self.map_viewer.draw_point(QPointF(node_x, node_y), Qt.GlobalColor.red)


        # Remove automatic pathfinding trigger - it's now triggered by the button
        # if self.start_node and self.end_node:
        #     self._trigger_pathfinding()

    def _trigger_pathfinding(self):
        """Finds and draws the path if start and end nodes are set."""
        if self.start_node and self.end_node:
            print(f"Finding path from {self.start_node} to {self.end_node}")
            path = self.pathfinder.find_path(self.start_node, self.end_node)
            if path:
                print(f"Path found: {path}")
                self.map_viewer.draw_path(path, self.node_positions)
            else:
                print("No path could be found between the selected nodes.")
                QMessageBox.warning(self, "Pathfinding", f"No path found between {self.start_node} and {self.end_node}")
                # Optionally clear the visual path if one existed before
                self.map_viewer.clear_path() # Need clear_path method in MapViewer
        else:
             QMessageBox.information(self, "Pathfinding", "Please select both a start and an end point.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

