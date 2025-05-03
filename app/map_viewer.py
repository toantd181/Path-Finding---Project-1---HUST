import sys
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsLineItem
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import Qt, QPointF, pyqtSignal # Added QColor, pyqtSignal

class MapViewer(QGraphicsView):
    # Signal emitted when a traffic line is drawn, sending start and end points
    traffic_line_drawn = pyqtSignal(QPointF, QPointF)

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
        # self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Default drag mode set later
        self.scale_factor = 1.0
        self.on_point_selected = on_point_selected

        # --- Point and Path Items ---
        self.start_point_item = None
        self.end_point_item = None
        self.path_items = [] # Store path lines to clear them later

        # --- Traffic Jam Drawing State ---
        self._is_drawing_traffic = False
        self._traffic_line_start = None
        self._traffic_line_item = None # Temporary item while drawing
        self.traffic_jam_lines = [] # Store final traffic jam lines added

        # Set initial drag mode
        self.set_traffic_drawing_mode(False) # Start with normal interaction

    def set_traffic_drawing_mode(self, enabled: bool):
        """Activates or deactivates the traffic jam drawing mode."""
        self._is_drawing_traffic = enabled
        if self._is_drawing_traffic:
            self.setDragMode(QGraphicsView.DragMode.NoDrag) # Disable panning while drawing
            print("Traffic drawing mode ENABLED") # Debug
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Restore panning
            # Clean up any unfinished drawing line if mode is toggled off mid-draw
            if self._traffic_line_item:
                self.scene.removeItem(self._traffic_line_item)
                self._traffic_line_item = None
            self._traffic_line_start = None
            print("Traffic drawing mode DISABLED") # Debug

    def mousePressEvent(self, event):
        """Handles mouse press for point selection OR starting traffic line draw."""
        pos = self.mapToScene(event.pos())

        if self._is_drawing_traffic:
            if event.button() == Qt.MouseButton.LeftButton:
                self._traffic_line_start = pos
                # Create a temporary line item
                pen = QPen(QColor("orange"), 2, Qt.PenStyle.DashLine) # Style for drawing feedback
                self._traffic_line_item = QGraphicsLineItem(QPointF.x(self._traffic_line_start), QPointF.y(self._traffic_line_start),
                                                            QPointF.x(self._traffic_line_start), QPointF.y(self._traffic_line_start))
                self._traffic_line_item.setPen(pen)
                self.scene.addItem(self._traffic_line_item)
            # Prevent default behavior (like panning) when drawing
            # super().mousePressEvent(event) # Don't call super if drawing
        else:
            # --- Original Point Selection Logic ---
            if event.button() == Qt.MouseButton.LeftButton:
                if self.start_point_item:
                    self.scene.removeItem(self.start_point_item)
                self.start_point_item = self.draw_point(pos, Qt.GlobalColor.green)
                self.on_point_selected("start", pos.x(), pos.y())
            elif event.button() == Qt.MouseButton.RightButton:
                if self.end_point_item:
                    self.scene.removeItem(self.end_point_item)
                self.end_point_item = self.draw_point(pos, Qt.GlobalColor.red)
                self.on_point_selected("end", pos.x(), pos.y())
            # Allow default behavior (like starting a pan) if not drawing
            super().mousePressEvent(event)


    def mouseMoveEvent(self, event):
        """Handles mouse move for drawing traffic line OR panning."""
        if self._is_drawing_traffic and self._traffic_line_start and self._traffic_line_item:
            # Update the end point of the temporary line
            current_pos = self.mapToScene(event.pos())
            self._traffic_line_item.setLine(QPointF.x(self._traffic_line_start), QPointF.y(self._traffic_line_start),
                                            QPointF.x(current_pos), QPointF.y(current_pos))
            # super().mouseMoveEvent(event) # Don't call super if drawing
        else:
            # Allow default behavior (panning)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handles mouse release to finalize traffic line OR finish panning."""
        if self._is_drawing_traffic and self._traffic_line_start and event.button() == Qt.MouseButton.LeftButton:
            # Finalize the line
            end_pos = self.mapToScene(event.pos())

            # Remove the temporary dashed line
            if self._traffic_line_item:
                self.scene.removeItem(self._traffic_line_item)
                self._traffic_line_item = None

            # Draw the final traffic jam line (optional persistent visual)
            pen = QPen(QColor("orange"), 3) # Solid orange line for final
            final_line = QGraphicsLineItem(QPointF.x(self._traffic_line_start), QPointF.y(self._traffic_line_start),
                                           QPointF.x(end_pos), QPointF.y(end_pos))
            final_line.setPen(pen)
            self.scene.addItem(final_line)
            self.traffic_jam_lines.append(final_line) # Store it

            # Emit the signal with the line coordinates
            self.traffic_line_drawn.emit(self._traffic_line_start, end_pos)
            print(f"Traffic line drawn from {self._traffic_line_start} to {end_pos}") # Debug

            # Reset drawing state
            self._traffic_line_start = None
            # super().mouseReleaseEvent(event) # Don't call super if drawing
        else:
            # Allow default behavior
            super().mouseReleaseEvent(event)

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

    def clear_traffic_jams(self):
        """Removes all drawn traffic jam lines from the scene."""
        for item in self.traffic_jam_lines:
            self.scene.removeItem(item)
        self.traffic_jam_lines.clear()
        print("Cleared traffic jam visuals") # Debug

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
        # Only zoom if not currently drawing a traffic line
        if not (self._is_drawing_traffic and self._traffic_line_start):
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
        # else:
            # Optionally provide feedback that zoom is disabled while drawing
            # print("Zoom disabled while drawing traffic line.")




