import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QMessageBox
from map_viewer import MapViewer
from pathfinding import Pathfinding
import os
import math # Import math for distance calculation

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Offline Pathfinding App")
        self.setGeometry(100, 100, 800, 600)

        # Widget chính
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        map_file = os.path.join(os.path.dirname(__file__), "assets", "map.png")
        # Pass the point selection handler to MapViewer
        self.map_viewer = MapViewer(map_file, self._handle_point_selected)
        layout.addWidget(self.map_viewer)

        central_widget.setLayout(layout)
        db_file = os.path.join(os.path.dirname(__file__), "data", "graph.db")
        try:
            self.pathfinder = Pathfinding(db_file)
        except FileNotFoundError as e:
             QMessageBox.critical(self, "Error", str(e))
             sys.exit(1) # Exit if db not found
        except Exception as e: # Catch other potential errors during Pathfinding init
             QMessageBox.critical(self, "Error", f"Failed to initialize pathfinder: {e}")
             sys.exit(1)


        self.start_node = None
        self.end_node = None
        self.node_positions = {name: data['pos'] for name, data in self.pathfinder.graph.nodes(data=True)}


    def _find_nearest_node(self, x, y):
        """Finds the nearest graph node to the given coordinates."""
        nearest_node = None
        min_dist_sq = float('inf')

        for node_name, pos in self.node_positions.items():
            dist_sq = (pos[0] - x)**2 + (pos[1] - y)**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                nearest_node = node_name
        # Optional: Add a threshold to ensure the click is close enough
        threshold = 50**2 # Example: 50 pixels squared
        if min_dist_sq > threshold:
            return None
        return nearest_node

    def _handle_point_selected(self, point_type, x, y):
        """Handles the selection of a point on the map by finding the nearest node."""
        nearest_node = self._find_nearest_node(x, y)
        if not nearest_node:
            print(f"No node found near click at ({x:.2f}, {y:.2f})")
            # Optionally clear the point visually if too far
            # self.map_viewer.clear_point(point_type)
            return

        print(f"Point selected: {point_type} near node {nearest_node} at ({x:.2f}, {y:.2f})")

        if point_type == "start":
            self.start_node = nearest_node
            # Optionally redraw the point snapped to the node
            # node_x, node_y = self.node_positions[nearest_node]
            # self.map_viewer.draw_point_at_node(node_x, node_y, Qt.GlobalColor.green)
        elif point_type == "end":
            self.end_node = nearest_node
            # Optionally redraw the point snapped to the node
            # node_x, node_y = self.node_positions[nearest_node]
            # self.map_viewer.draw_point_at_node(node_x, node_y, Qt.GlobalColor.red)


        # If both start and end nodes are selected, find and draw the path
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
                # self.map_viewer.clear_path()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

