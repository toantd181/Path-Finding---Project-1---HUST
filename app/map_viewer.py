import sys
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsRectItem
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal

# Define keys for storing data on graphics items
EFFECT_DATA_KEY = Qt.ItemDataRole.UserRole + 1 # Use UserRole + n for custom data

class MapViewer(QGraphicsView):
    # Signal emitted when a traffic line is drawn, sending start and end points
    traffic_line_drawn = pyqtSignal(QPointF, QPointF)
    # Signal emitted when a rain area rectangle is defined
    rain_area_defined = pyqtSignal(QRectF)
    # Signal emitted when any effect visual is removed via Shift+Click
    effects_changed = pyqtSignal()

    def __init__(self, image_path, on_point_selected, scene=None): # Accept scene optionally
        super().__init__()
        # Use provided scene or create a new one
        self.scene = scene if scene else QGraphicsScene(self)
        self.setScene(self.scene)

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
             print(f"Error: Could not load map image from {image_path}")
             # Handle error appropriately, maybe raise exception or show message
        else:
            self.map_item = QGraphicsPixmapItem(pixmap)
            # Add map item only if pixmap loaded successfully
            self.scene.addItem(self.map_item)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scale_factor = 1.0
        self.on_point_selected = on_point_selected # Callback for start/end node selection

        # --- Point and Path Items ---
        # These are now managed more directly by MainWindow interacting with MapViewer methods
        # self.start_point_item = None # Use set_permanent_point instead
        # self.end_point_item = None
        self._permanent_start_item = None # Store the final start marker
        self._permanent_end_item = None   # Store the final end marker
        self._temporary_point_item = None # For click feedback before node snapping
        self.path_items = [] # Store path lines to clear them later

        # --- Traffic Jam Drawing State ---
        self._is_drawing_traffic = False
        self._traffic_line_start = None
        self._traffic_line_item = None # Temporary item while drawing
        self.traffic_jam_lines = [] # Store final traffic jam line QGraphicsLineItems

        # --- Rain Area Drawing State ---
        self._is_drawing_rain_area = False
        self._rain_area_start = None
        self._rain_area_rect_item = None # Temporary rectangle item
        self.rain_area_visuals = [] # Store final rain area QGraphicsRectItems

        # Set initial drag mode
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag) # Start with normal interaction

    # --- Drawing Mode Setters (set_traffic_drawing_mode, set_rain_drawing_mode) remain the same ---
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
        """Handles mouse press for point selection, starting draws, OR removing effects."""
        pos = self.mapToScene(event.pos())
        modifiers = event.modifiers()

        # --- Shift+Click: Remove Effect ---
        if modifiers & Qt.KeyboardModifier.ShiftModifier and event.button() == Qt.MouseButton.LeftButton:
            item_to_remove = None
            list_to_update = None
            # Find item under cursor - itemAt returns topmost item
            clicked_item = self.itemAt(event.pos())

            if clicked_item:
                # Check if it's one of our effect items by checking stored data or list membership
                if clicked_item in self.traffic_jam_lines:
                    item_to_remove = clicked_item
                    list_to_update = self.traffic_jam_lines
                    print(f"Shift+Click detected on a traffic line.")
                elif clicked_item in self.rain_area_visuals:
                    item_to_remove = clicked_item
                    list_to_update = self.rain_area_visuals
                    print(f"Shift+Click detected on a rain area.")

            if item_to_remove and list_to_update is not None:
                self.scene.removeItem(item_to_remove)
                list_to_update.remove(item_to_remove)
                print(f"Removed effect visual.")
                self.effects_changed.emit() # Signal MainWindow to recalculate weights
                event.accept() # Consume the event
                return # Don't process further

            # If Shift+Click didn't hit a removable item, maybe allow default behavior?
            # Or just do nothing. For now, do nothing.
            event.accept()
            return

        # --- Normal Drawing / Point Selection ---
        if self._is_drawing_traffic:
            if event.button() == Qt.MouseButton.LeftButton:
                self._traffic_line_start = pos
                pen = QPen(QColor("orange"), 2, Qt.PenStyle.DashLine)
                # Use QPointF directly
                self._traffic_line_item = QGraphicsLineItem(self._traffic_line_start.x(), self._traffic_line_start.y(),
                                                            self._traffic_line_start.x(), self._traffic_line_start.y())
                self._traffic_line_item.setPen(pen)
                self.scene.addItem(self._traffic_line_item)
                event.accept() # Consume event
            # Prevent default behavior
        elif self._is_drawing_rain_area:
             if event.button() == Qt.MouseButton.LeftButton:
                 self._rain_area_start = pos
                 pen = QPen(QColor(0, 150, 255, 150), 2, Qt.PenStyle.DashLine)
                 brush = QBrush(QColor(0, 150, 255, 50))
                 self._rain_area_rect_item = QGraphicsRectItem(QRectF(self._rain_area_start, self._rain_area_start))
                 self._rain_area_rect_item.setPen(pen)
                 self._rain_area_rect_item.setBrush(brush)
                 self.scene.addItem(self._rain_area_rect_item)
                 event.accept() # Consume event
             # Prevent default behavior
        else:
            # --- Original Point Selection Logic ---
            # Draw temporary feedback point immediately on click
            self.clear_temporary_point(None) # Clear previous temp point
            temp_color = Qt.GlobalColor.yellow # Color for temporary point
            self._temporary_point_item = self.draw_point(pos, temp_color, radius=4, temporary=True)

            # Call the handler in MainWindow to find the nearest node
            if event.button() == Qt.MouseButton.LeftButton:
                self.on_point_selected("start", pos.x(), pos.y())
            elif event.button() == Qt.MouseButton.RightButton:
                self.on_point_selected("end", pos.x(), pos.y())

            # Allow default behavior ONLY if not selecting points (e.g., middle mouse button)
            if event.button() not in [Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton]:
                super().mousePressEvent(event)
            else:
                event.accept() # Consume left/right clicks if used for selection


    def mouseMoveEvent(self, event):
        """Handles mouse move for drawing traffic line, rain area OR panning."""
        current_pos = self.mapToScene(event.pos())

        if self._is_drawing_traffic and self._traffic_line_start and self._traffic_line_item:
            # Update the end point of the temporary line
            self._traffic_line_item.setLine(self._traffic_line_start.x(), self._traffic_line_start.y(),
                                            current_pos.x(), current_pos.y())
            event.accept()
        elif self._is_drawing_rain_area and self._rain_area_start and self._rain_area_rect_item:
             # Update the rectangle dimensions
             rect = QRectF(self._rain_area_start, current_pos).normalized() # Ensure positive width/height
             self._rain_area_rect_item.setRect(rect)
             event.accept()
        elif event.buttons() & (Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton) and not self._is_drawing_traffic and not self._is_drawing_rain_area:
             # Prevent panning if left/right mouse is down for point selection (even if mouse moves slightly)
             event.accept()
        else:
            # Allow default behavior (panning)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handles mouse release to finalize traffic line, rain area OR finish panning."""
        end_pos = self.mapToScene(event.pos())

        if self._is_drawing_traffic and self._traffic_line_start and event.button() == Qt.MouseButton.LeftButton:
            # Remove temporary drawing item
            if self._traffic_line_item:
                self.scene.removeItem(self._traffic_line_item)
                self._traffic_line_item = None

            # Create the final, persistent line item
            pen = QPen(QColor("orange"), 3)
            final_line = QGraphicsLineItem(self._traffic_line_start.x(), self._traffic_line_start.y(),
                                           end_pos.x(), end_pos.y())
            final_line.setPen(pen)

            # Store effect data (e.g., weight) - MainWindow will provide this via signal/slot later
            # For now, emit the raw line data
            # final_line.setData(EFFECT_DATA_KEY, {"type": "traffic", "weight": traffic_weight}) # Placeholder

            self.scene.addItem(final_line)
            self.traffic_jam_lines.append(final_line) # Store the persistent item

            # Emit signal for MainWindow to handle weight calculation
            self.traffic_line_drawn.emit(self._traffic_line_start, end_pos)
            print(f"Traffic line finalized from {self._traffic_line_start} to {end_pos}")
            self._traffic_line_start = None
            event.accept()

        elif self._is_drawing_rain_area and self._rain_area_start and event.button() == Qt.MouseButton.LeftButton:
             # Finalize the rain area rectangle
             if self._rain_area_rect_item:
                 final_rect = self._rain_area_rect_item.rect() # Get the final rect geometry

                 # Make the temporary item permanent (or draw a new one)
                 pen = QPen(QColor(0, 100, 200, 180), 2) # Slightly darker solid blue border
                 brush = QBrush(QColor(0, 150, 255, 70)) # Slightly less transparent fill
                 self._rain_area_rect_item.setPen(pen)
                 self._rain_area_rect_item.setBrush(brush)

                 # Store effect data (e.g., weight) - MainWindow will provide this
                 # self._rain_area_rect_item.setData(EFFECT_DATA_KEY, {"type": "rain", "weight": rain_weight}) # Placeholder

                 # Keep the item, store it
                 self.rain_area_visuals.append(self._rain_area_rect_item)
                 self._rain_area_rect_item = None # Reset temporary item holder

                 # Emit the signal with the rectangle coordinates for MainWindow
                 self.rain_area_defined.emit(final_rect)
                 print(f"Rain area finalized: {final_rect}") # Debug
             self._rain_area_start = None
             event.accept()
             # Optional: Deactivate drawing mode automatically after one area?
             # self.set_rain_drawing_mode(False)
             # self.parent().sidebar.rain_area_button.setChecked(False) # If you have access to parent
        else:
            # Allow default behavior (e.g., finishing a pan)
            super().mouseReleaseEvent(event)

    # --- Point Drawing ---
    def draw_point(self, pos: QPointF, color, radius=5, temporary=False):
        """Draws a point on the map and returns the QGraphicsEllipseItem."""
        pen = QPen(color)
        brush = QBrush(color)
        # Create and add the ellipse item
        ellipse = QGraphicsEllipseItem(pos.x() - radius, pos.y() - radius, 2 * radius, 2 * radius)
        ellipse.setPen(pen)
        ellipse.setBrush(brush)
        if temporary:
            ellipse.setZValue(10) # Ensure temporary point is visible
        self.scene.addItem(ellipse)
        return ellipse # Return the item

    def clear_temporary_point(self, point_type=None): # Added point_type argument (optional)
        """Removes the temporary yellow feedback point."""
        if self._temporary_point_item:
            self.scene.removeItem(self._temporary_point_item)
            self._temporary_point_item = None

    def set_permanent_point(self, point_type, pos: QPointF):
        """Removes the temporary point and draws the final start/end point."""
        self.clear_temporary_point() # Remove yellow dot

        if point_type == "start":
            if self._permanent_start_item:
                self.scene.removeItem(self._permanent_start_item)
            self._permanent_start_item = self.draw_point(pos, Qt.GlobalColor.green)
        elif point_type == "end":
            if self._permanent_end_item:
                self.scene.removeItem(self._permanent_end_item)
            self._permanent_end_item = self.draw_point(pos, Qt.GlobalColor.red)

    # --- Clearing Methods ---
    def clear_path(self):
        """Removes the currently drawn path from the scene."""
        for item in self.path_items:
            if item.scene() == self.scene: # Check if still in scene
                 self.scene.removeItem(item)
        self.path_items.clear() # Clear the list

    def clear_traffic_jams(self):
        """Removes all drawn traffic jam lines from the scene."""
        for item in self.traffic_jam_lines:
             if item.scene() == self.scene:
                 self.scene.removeItem(item)
        self.traffic_jam_lines.clear()
        print("Cleared traffic jam visuals") # Debug

    def clear_rain_areas(self):
        """Removes all drawn rain area visuals from the scene."""
        for item in self.rain_area_visuals:
             if item.scene() == self.scene:
                 self.scene.removeItem(item)
        self.rain_area_visuals.clear()
        print("Cleared rain area visuals") # Debug

    # --- Path Drawing ---
    def draw_path(self, path, node_positions):
        """Draws the calculated path on the map."""
        self.clear_path() # Clear any existing path first

        if not path or len(path) < 2:
            return # Nothing to draw

        pen = QPen(Qt.GlobalColor.blue, 3) # Use a QPen object
        pen.setCapStyle(Qt.PenCapStyle.RoundCap) # Nicer line ends

        for i in range(len(path) - 1):
            try:
                start_node_name = path[i]
                end_node_name = path[i+1]
                start_pos_tuple = node_positions[start_node_name]
                end_pos_tuple = node_positions[end_node_name]

                # Convert tuples to QPointF for clarity if needed, though numbers work
                start_point = QPointF(start_pos_tuple[0], start_pos_tuple[1])
                end_point = QPointF(end_pos_tuple[0], end_pos_tuple[1])

                line = QGraphicsLineItem(start_point.x(), start_point.y(), end_point.x(), end_point.y())
                line.setPen(pen)
                line.setZValue(5) # Draw path above effects?
                self.scene.addItem(line)
                self.path_items.append(line) # Store reference

            except KeyError as e:
                print(f"Warning: Node {e} not found in node_positions while drawing path.")
            except Exception as e:
                print(f"Error drawing path segment between {start_node_name} and {end_node_name}: {e}")


    # --- Zooming ---
    def wheelEvent(self, event):
        """Handles mouse wheel events for zooming."""
        # Disable zoom if any drawing mode is active
        if not self._is_drawing_traffic and not self._is_drawing_rain_area:
            zoom_in_factor = 1.15
            zoom_out_factor = 1 / zoom_in_factor
            # Anchor zoom point
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor
            self.scale(zoom_factor, zoom_factor)
            # Update internal scale factor if needed for other calculations
            self.scale_factor *= zoom_factor
            # Reset anchor
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        # else:
            # print("Zoom disabled while drawing.")

    # --- Helper to get sidebar tool instance (needed for storing data) ---
    # This is not ideal coupling, consider passing data explicitly
    def _get_sidebar_tool(self, tool_type):
        """ Tries to get the tool instance from the sidebar (assumes parent structure). """
        try:
            # This assumes MainWindow is the parent, and it has a 'sidebar' attribute
            sidebar = self.parent().sidebar
            if tool_type == "traffic":
                return sidebar.traffic_tool
            elif tool_type == "rain":
                return sidebar.rain_tool
        except AttributeError:
            print("Warning: Could not access sidebar tools from MapViewer.")
        return None




