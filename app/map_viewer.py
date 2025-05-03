import sys
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsLineItem # Added QGraphicsEllipseItem, QGraphicsLineItem
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush
from PyQt6.QtCore import Qt, QPointF # Added QPointF

class MapViewer(QGraphicsView):
    def __init__(self, image_path, on_point_selected):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
             print(f"Error: Could not load map image from {image_path}")
             # Handle error appropriately, maybe show a default image or exit
        self.map_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.map_item)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.scale_factor = 1.0
        self.on_point_selected = on_point_selected
        # Store references to the graphics items for points and path
        self.start_point_item = None
        self.end_point_item = None
        self.path_items = [] # Store path lines to clear them later

    def mousePressEvent(self, event):
        """Handles user clicks to select start/end points."""
        pos = self.mapToScene(event.pos())

        if event.button() == Qt.MouseButton.LeftButton:
            # Remove previous start point if it exists
            if self.start_point_item:
                self.scene.removeItem(self.start_point_item)
                self.start_point_item = None
            # Draw new start point and store the item
            self.start_point_item = self.draw_point(pos, Qt.GlobalColor.green)
            self.on_point_selected("start", pos.x(), pos.y())

        elif event.button() == Qt.MouseButton.RightButton:
            # Remove previous end point if it exists
            if self.end_point_item:
                self.scene.removeItem(self.end_point_item)
                self.end_point_item = None
            # Draw new end point and store the item
            self.end_point_item = self.draw_point(pos, Qt.GlobalColor.red)
            self.on_point_selected("end", pos.x(), pos.y())

    def draw_point(self, pos: QPointF, color):
        """Draws a point on the map and returns the QGraphicsEllipseItem."""
        pen = QPen(color)
        brush = QBrush(color)
        radius = 5
        # Create and add the ellipse item
        ellipse = QGraphicsEllipseItem(pos.x() - radius, pos.y() - radius, 2 * radius, 2 * radius)
        ellipse.setPen(pen)
        ellipse.setBrush(brush)
        self.scene.addItem(ellipse)
        return ellipse # Return the item so we can store a reference

    def clear_path(self):
        """Removes the currently drawn path from the scene."""
        for item in self.path_items:
            self.scene.removeItem(item)
        self.path_items.clear() # Clear the list

    def draw_path(self, path, node_positions):
        """Draws the calculated path on the map."""
        self.clear_path() # Clear any existing path first

        if not path or len(path) < 2:
            return # Nothing to draw

        pen = QPen(Qt.GlobalColor.blue, 3) # Use a QPen object
        pen.setCapStyle(Qt.PenCapStyle.RoundCap) # Nicer line ends

        for i in range(len(path) - 1):
            try:
                # Get coordinates from node_positions dictionary
                start_pos = node_positions[path[i]]
                end_pos = node_positions[path[i+1]]

                # Ensure positions are tuples/lists of numbers
                if not (isinstance(start_pos, (tuple, list)) and len(start_pos) == 2 and
                        isinstance(end_pos, (tuple, list)) and len(end_pos) == 2):
                     print(f"Warning: Invalid position data for path segment {path[i]} -> {path[i+1]}")
                     continue

                x1, y1 = start_pos
                x2, y2 = end_pos

                # Create and add the line item
                line = QGraphicsLineItem(x1, y1, x2, y2)
                line.setPen(pen)
                self.scene.addItem(line)
                self.path_items.append(line) # Store reference to the line item

            except KeyError as e:
                print(f"Warning: Node {e} not found in node_positions while drawing path.")
            except Exception as e:
                print(f"Error drawing path segment: {e}")


    def wheelEvent(self, event):
        """Handles mouse wheel events for zooming."""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor
        # Save the scene pos
        old_pos = self.mapToScene(event.position().toPoint())
        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
        self.scale(zoom_factor, zoom_factor)
        self.scale_factor *= zoom_factor
        # Get the new position
        new_pos = self.mapToScene(event.position().toPoint())
        # Move scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())




