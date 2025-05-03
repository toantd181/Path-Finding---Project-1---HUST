import sys
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsRectItem # Added QGraphicsRectItem
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal # Added QColor, QRectF, pyqtSignal

class MapViewer(QGraphicsView):
    # Signal emitted when a traffic line is drawn, sending start and end points
    traffic_line_drawn = pyqtSignal(QPointF, QPointF)
    # Signal emitted when a rain area rectangle is defined
    rain_area_defined = pyqtSignal(QRectF)

    def __init__(self, image_path, on_point_selected):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
             print(f"Error: Could not load map image from {image_path}")
        self.map_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.map_item)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
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

        # --- Rain Area Drawing State ---
        self._is_drawing_rain_area = False
        self._rain_area_start = None
        self._rain_area_rect_item = None # Temporary rectangle item
        self.rain_area_visuals = [] # Store final rain area visuals

        # Set initial drag mode
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Start with normal interaction

    def set_traffic_drawing_mode(self, enabled: bool):
        """Activates or deactivates the traffic jam drawing mode."""
        self._is_drawing_traffic = enabled
        if self._is_drawing_traffic:
            self.setDragMode(QGraphicsView.DragMode.NoDrag) # Disable panning
            self._is_drawing_rain_area = False # Ensure rain drawing is off
            print("Traffic drawing mode ENABLED")
        else:
            # Only restore panning if rain mode is also off
            if not self._is_drawing_rain_area:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            # Clean up unfinished traffic line
            if self._traffic_line_item:
                self.scene.removeItem(self._traffic_line_item)
                self._traffic_line_item = None
            self._traffic_line_start = None
            print("Traffic drawing mode DISABLED")

    def set_rain_drawing_mode(self, enabled: bool):
        """Activates or deactivates the rain area drawing mode."""
        self._is_drawing_rain_area = enabled
        if self._is_drawing_rain_area:
            self.setDragMode(QGraphicsView.DragMode.NoDrag) # Disable panning
            self._is_drawing_traffic = False # Ensure traffic drawing is off
            print("Rain area drawing mode ENABLED")
        else:
            # Only restore panning if traffic mode is also off
            if not self._is_drawing_traffic:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            # Clean up unfinished rain rectangle
            if self._rain_area_rect_item:
                self.scene.removeItem(self._rain_area_rect_item)
                self._rain_area_rect_item = None
            self._rain_area_start = None
            print("Rain area drawing mode DISABLED")


    def mousePressEvent(self, event):
        """Handles mouse press for point selection OR starting traffic/rain draw."""
        pos = self.mapToScene(event.pos())

        if self._is_drawing_traffic:
            if event.button() == Qt.MouseButton.LeftButton:
                self._traffic_line_start = pos
                pen = QPen(QColor("orange"), 2, Qt.PenStyle.DashLine)
                self._traffic_line_item = QGraphicsLineItem(QPointF.x(self._traffic_line_start), QPointF.y(self._traffic_line_start),
                                                            QPointF.x(self._traffic_line_start), QPointF.y(self._traffic_line_start))
                self._traffic_line_item.setPen(pen)
                self.scene.addItem(self._traffic_line_item)
            # Prevent default behavior
        elif self._is_drawing_rain_area:
             if event.button() == Qt.MouseButton.LeftButton:
                 self._rain_area_start = pos
                 # Create temporary rectangle item (initially zero size)
                 pen = QPen(QColor(0, 150, 255, 150), 2, Qt.PenStyle.DashLine) # Semi-transparent blue dash
                 brush = QBrush(QColor(0, 150, 255, 50)) # Very transparent blue fill
                 self._rain_area_rect_item = QGraphicsRectItem(QRectF(self._rain_area_start, self._rain_area_start))
                 self._rain_area_rect_item.setPen(pen)
                 self._rain_area_rect_item.setBrush(brush)
                 self.scene.addItem(self._rain_area_rect_item)
             # Prevent default behavior
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
        """Handles mouse move for drawing traffic line, rain area OR panning."""
        current_pos = self.mapToScene(event.pos())

        if self._is_drawing_traffic and self._traffic_line_start and self._traffic_line_item:
            # Update the end point of the temporary line
            self._traffic_line_item.setLine(QPointF.x(self._traffic_line_start), QPointF.y(self._traffic_line_start),
                                            QPointF.x(current_pos), QPointF.y(current_pos))
        elif self._is_drawing_rain_area and self._rain_area_start and self._rain_area_rect_item:
             # Update the rectangle dimensions
             rect = QRectF(self._rain_area_start, current_pos).normalized() # Ensure positive width/height
             self._rain_area_rect_item.setRect(rect)
        else:
            # Allow default behavior (panning)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handles mouse release to finalize traffic line, rain area OR finish panning."""
        end_pos = self.mapToScene(event.pos())

        if self._is_drawing_traffic and self._traffic_line_start and event.button() == Qt.MouseButton.LeftButton:
            # Finalize the traffic line
            if self._traffic_line_item:
                self.scene.removeItem(self._traffic_line_item)
                self._traffic_line_item = None
            pen = QPen(QColor("orange"), 3)
            final_line = QGraphicsLineItem(QPointF.x(self._traffic_line_start), QPointF.y(self._traffic_line_start),
                                           QPointF.x(end_pos), QPointF.y(end_pos))
            final_line.setPen(pen)
            self.scene.addItem(final_line)
            self.traffic_jam_lines.append(final_line)
            self.traffic_line_drawn.emit(self._traffic_line_start, end_pos)
            print(f"Traffic line drawn from {self._traffic_line_start} to {end_pos}")
            self._traffic_line_start = None
        elif self._is_drawing_rain_area and self._rain_area_start and event.button() == Qt.MouseButton.LeftButton:
             # Finalize the rain area rectangle
             if self._rain_area_rect_item:
                 final_rect = self._rain_area_rect_item.rect() # Get the final rect geometry
                 # Make the temporary item permanent (or draw a new one)
                 pen = QPen(QColor(0, 100, 200, 180), 2) # Slightly darker solid blue border
                 brush = QBrush(QColor(0, 150, 255, 70)) # Slightly less transparent fill
                 self._rain_area_rect_item.setPen(pen)
                 self._rain_area_rect_item.setBrush(brush)
                 # Keep the item, store it
                 self.rain_area_visuals.append(self._rain_area_rect_item)
                 self._rain_area_rect_item = None # Reset temporary item holder

                 # Emit the signal with the rectangle coordinates
                 self.rain_area_defined.emit(final_rect)
                 print(f"Rain area defined: {final_rect}") # Debug
             self._rain_area_start = None
             # Optional: Deactivate drawing mode automatically after one area?
             # self.set_rain_drawing_mode(False)
             # self.parent().sidebar.rain_area_button.setChecked(False) # If you have access to parent
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

    def clear_rain_areas(self):
        """Removes all drawn rain area visuals from the scene."""
        for item in self.rain_area_visuals:
            self.scene.removeItem(item)
        self.rain_area_visuals.clear()
        print("Cleared rain area visuals") # Debug

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
        # Disable zoom if any drawing mode is active
        if not self._is_drawing_traffic and not self._is_drawing_rain_area:
            zoom_in_factor = 1.15
            zoom_out_factor = 1 / zoom_in_factor
            old_pos = self.mapToScene(event.position().toPoint())
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor
            self.scale(zoom_factor, zoom_factor)
            self.scale_factor *= zoom_factor
            new_pos = self.mapToScene(event.position().toPoint())
            delta = new_pos - old_pos
            self.translate(delta.x(), delta.y())
        # else:
            # print("Zoom disabled while drawing.")




