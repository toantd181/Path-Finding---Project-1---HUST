from PyQt6.QtWidgets import (QApplication, QGraphicsView, QGraphicsScene,
                             QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsLineItem,
                             QGraphicsRectItem, QGraphicsSimpleTextItem) # Added QGraphicsSimpleTextItem
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QIcon, QFont # Added QIcon, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QLineF
import os # Import os
from .tools.traffic_light_tool import TrafficLightState # Import the state class

# Define keys for storing data on graphics items
EFFECT_DATA_KEY = Qt.ItemDataRole.UserRole + 1 # Use UserRole + n for custom data

# --- Traffic Light Icon ---
# Load the icon once
TRAFFIC_LIGHT_ICON_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'icons', 'traffic-light.png')
TRAFFIC_LIGHT_ICON = QIcon(TRAFFIC_LIGHT_ICON_PATH)
TRAFFIC_LIGHT_PIXMAP = TRAFFIC_LIGHT_ICON.pixmap(32, 32) # Adjust size as needed
if TRAFFIC_LIGHT_PIXMAP.isNull():
    print(f"Warning: Could not load traffic light icon: {TRAFFIC_LIGHT_ICON_PATH}")
# ---

# --- Countdown Text Font ---
COUNTDOWN_FONT = QFont("Arial", 10, QFont.Weight.Bold)
COUNTDOWN_COLOR = QColor("white")
COUNTDOWN_BG_COLOR = QColor(0, 0, 0, 150) # Semi-transparent black background
# ---

class MapViewer(QGraphicsView):
    # Signal emitted when a traffic line is drawn, sending start and end points
    traffic_line_drawn = pyqtSignal(QPointF, QPointF)
    # Signal emitted when a rain area rectangle is defined
    rain_area_defined = pyqtSignal(QRectF)
    # Signal emitted when a block way line is drawn
    block_way_drawn = pyqtSignal(QPointF, QPointF) # New signal
    # Signal emitted when any effect visual is removed via Shift+Click
    effects_changed = pyqtSignal()

    # --- New Signals for Traffic Light ---
    # Emitted after user clicks to place the icon
    traffic_light_icon_placed = pyqtSignal(QPointF)
    # Emitted after user finishes drawing the effect line and all visuals are created
    # Sends: icon_pos, line_start, line_end, icon_item, line_item, text_item
    traffic_light_visuals_created = pyqtSignal(QPointF, QPointF, QPointF, QGraphicsPixmapItem, QGraphicsLineItem, QGraphicsSimpleTextItem) # Correct signal definition

    def __init__(self, image_path, on_point_selected, scene=None):
        super().__init__()
        self.scene = scene if scene else QGraphicsScene(self)
        self.setScene(self.scene)

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"Error: Could not load map image from {image_path}")
        else:
            self.scene.addPixmap(pixmap)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scale_factor = 1.0
        self.on_point_selected = on_point_selected

        # --- Point and Path Items ---
        self._permanent_start_item = None
        self._permanent_end_item = None
        self._temporary_point_item = None
        self.path_items = []

        # --- Effect Visuals Storage ---
        self.traffic_jam_lines = []
        self.rain_area_visuals = []
        self.block_way_visuals = []
        # Store tuples: (icon_item, line_item, text_item, data_dict)
        # data_dict will hold durations, state, timer etc. managed by MainWindow
        self.traffic_light_visuals = [] # New list for traffic lights

        # --- Drawing States ---
        self._is_drawing_traffic = False
        self._traffic_line_start = None
        self._traffic_line_item = None

        self._is_drawing_rain_area = False
        self._rain_area_start = None
        self._rain_area_rect_item = None

        self._is_drawing_block_way = False
        self._block_way_start = None
        self._block_way_line_item = None

        # --- Traffic Light Drawing State --- New ---
        self._is_placing_traffic_light_icon = False # True when tool active, waiting for click
        self._is_drawing_traffic_light_line = False # True after icon placed, drawing line
        self._traffic_light_icon_pos = None      # Position where the icon was placed
        self._traffic_light_line_start = None    # Start of the effect line (usually same as icon pos)
        self._traffic_light_line_item = None     # Temporary line item while drawing effect line
        self._current_traffic_light_icon_item = None # Temporary icon item shown before line draw
        # --- End Traffic Light State ---

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    # --- Drawing Mode Setters ---
    def set_traffic_drawing_mode(self, enabled: bool):
        self._is_drawing_traffic = enabled
        self._is_drawing_rain_area = False
        self._is_drawing_block_way = False
        self._is_placing_traffic_light_icon = False # Ensure others are off
        self._is_drawing_traffic_light_line = False
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._cleanup_temp_drawing()

    def set_rain_drawing_mode(self, enabled: bool):
        self._is_drawing_traffic = False
        self._is_drawing_rain_area = enabled
        self._is_drawing_block_way = False
        self._is_placing_traffic_light_icon = False
        self._is_drawing_traffic_light_line = False
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._cleanup_temp_drawing()

    def set_block_way_drawing_mode(self, enabled: bool):
        self._is_drawing_traffic = False
        self._is_drawing_rain_area = False
        self._is_drawing_block_way = enabled
        self._is_placing_traffic_light_icon = False
        self._is_drawing_traffic_light_line = False
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._cleanup_temp_drawing()

    def set_traffic_light_placement_mode(self, enabled: bool):
        """Activates mode to place the traffic light icon first."""
        self._is_drawing_traffic = False
        self._is_drawing_rain_area = False
        self._is_drawing_block_way = False
        self._is_placing_traffic_light_icon = enabled
        self._is_drawing_traffic_light_line = False # Not drawing line yet
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            # Maybe a specific cursor for placing?
            self.setCursor(Qt.CursorShape.PointingHandCursor) # Indicate placement
        else:
            # If deactivated externally, reset state
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._cleanup_temp_drawing() # Clean up any partial placement

    def _cleanup_temp_drawing(self):
        """Removes temporary drawing items."""
        if self._traffic_line_item:
            self.scene.removeItem(self._traffic_line_item)
            self._traffic_line_item = None
        if self._rain_area_rect_item:
            self.scene.removeItem(self._rain_area_rect_item)
            self._rain_area_rect_item = None
        if self._block_way_line_item:
            self.scene.removeItem(self._block_way_line_item)
            self._block_way_line_item = None
        if self._traffic_light_line_item:
            self.scene.removeItem(self._traffic_light_line_item)
            self._traffic_light_line_item = None
        if self._current_traffic_light_icon_item: # Remove temporary icon if placement cancelled
             self.scene.removeItem(self._current_traffic_light_icon_item)
             self._current_traffic_light_icon_item = None
        # Reset drawing state variables
        self._traffic_line_start = None
        self._rain_area_start = None
        self._block_way_start = None
        self._traffic_light_icon_pos = None
        self._traffic_light_line_start = None


    def mousePressEvent(self, event):
        pos = self.mapToScene(event.pos())
        modifiers = QApplication.keyboardModifiers() # Use QApplication for modifiers

        # --- Shift+Click: Remove Effect ---
        if modifiers == Qt.KeyboardModifier.ShiftModifier and event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
            if item:
                removed = False
                # Check and remove from traffic jam lines
                if item in self.traffic_jam_lines:
                    self.scene.removeItem(item)
                    self.traffic_jam_lines.remove(item)
                    removed = True
                # Check and remove from rain areas
                elif item in self.rain_area_visuals:
                    self.scene.removeItem(item)
                    self.rain_area_visuals.remove(item)
                    removed = True
                # Check and remove from block ways
                elif item in self.block_way_visuals:
                    self.scene.removeItem(item)
                    self.block_way_visuals.remove(item)
                    removed = True
                # Check and remove from traffic lights (remove icon, line, and text)
                else:
                    for i, (icon_item, line_item, text_item, _) in enumerate(self.traffic_light_visuals):
                        # Check if clicked item is any part of the traffic light visual group
                        if item == icon_item or item == line_item or item == text_item:
                            self.scene.removeItem(icon_item)
                            self.scene.removeItem(line_item)
                            self.scene.removeItem(text_item) # Remove text item as well
                            # MainWindow needs to know which specific light was removed
                            # We can pass the item's data back or handle timer stop in MainWindow based on item removal
                            removed_data = self.traffic_light_visuals.pop(i)[3] # Get data before removing (index 3 now)
                            # Store data on the item being clicked for MainWindow to identify
                            if isinstance(item, (QGraphicsPixmapItem, QGraphicsLineItem, QGraphicsSimpleTextItem)):
                                item.setData(EFFECT_DATA_KEY, removed_data)
                            removed = True
                            break # Found and removed

                if removed:
                    print(f"Removed effect item at {pos}")
                    self.effects_changed.emit() # Signal that effects need recalculation
                    event.accept()
                    return # Don't process further
            # If shift-click didn't hit a removable item, fall through to default or other actions

        # --- Normal Drawing / Point Selection ---
        if self._is_placing_traffic_light_icon:
            # First click: Place the icon
            self._traffic_light_icon_pos = pos
            # Draw a temporary icon to show placement
            self._current_traffic_light_icon_item = self.draw_traffic_light_icon(pos, temporary=True)
            # Emit signal to MainWindow (it might need durations from sidebar)
            self.traffic_light_icon_placed.emit(pos)
            # Transition state: Now expect user to draw the effect line
            self._is_placing_traffic_light_icon = False
            self._is_drawing_traffic_light_line = True
            self._traffic_light_line_start = pos # Line starts from icon center
            # Keep cross cursor for line drawing
            self.setCursor(Qt.CursorShape.CrossCursor)
            print(f"Traffic light icon placed at {pos}, now draw effect line.")
            event.accept()
        elif self._is_drawing_traffic_light_line:
            # This state is primarily handled by move/release for the line
            # A click here might cancel? Or just start the line draw from icon pos.
            # Let's assume move/release handles the line drawing after icon placement.
            # Press event starts the temporary line drawing.
            if not self._traffic_light_line_item: # Start drawing the line
                 pen = QPen(QColor("orange"), 2, Qt.PenStyle.DashLine)
                 self._traffic_light_line_item = QGraphicsLineItem(QLineF(self._traffic_light_line_start, pos))
                 self._traffic_light_line_item.setPen(pen)
                 self.scene.addItem(self._traffic_light_line_item)
                 event.accept()
        elif self._is_drawing_traffic:
            self._traffic_line_start = pos
            pen = QPen(QColor("red"), 2, Qt.PenStyle.DashLine)
            self._traffic_line_item = QGraphicsLineItem(QLineF(pos, pos))
            self._traffic_line_item.setPen(pen)
            self.scene.addItem(self._traffic_line_item)
            event.accept()
        elif self._is_drawing_rain_area:
            self._rain_area_start = pos
            brush = QBrush(QColor(0, 0, 255, 50)) # Semi-transparent blue
            pen = QPen(QColor("blue"), 1, Qt.PenStyle.DashLine)
            self._rain_area_rect_item = QGraphicsRectItem(QRectF(pos, pos))
            self._rain_area_rect_item.setBrush(brush)
            self._rain_area_rect_item.setPen(pen)
            self.scene.addItem(self._rain_area_rect_item)
            event.accept()
        elif self._is_drawing_block_way:
            self._block_way_start = pos
            pen = QPen(QColor("black"), 3, Qt.PenStyle.DashLine) # Thicker dashed line
            self._block_way_line_item = QGraphicsLineItem(QLineF(pos, pos))
            self._block_way_line_item.setPen(pen)
            self.scene.addItem(self._block_way_line_item)
            event.accept()
        else:
            # Normal mode: Select start/end point or pan
            # Check if clicking on an existing permanent marker to clear it
            item = self.itemAt(event.pos())
            cleared_point = False
            if item == self._permanent_start_item:
                self.clear_permanent_point("start")
                cleared_point = True
            elif item == self._permanent_end_item:
                self.clear_permanent_point("end")
                cleared_point = True

            if cleared_point:
                 # Also clear the path if a point is cleared
                 self.clear_path()
                 # Call the callback to update MainWindow's state
                 self.on_point_selected(None, -1, -1) # Indicate point cleared
                 event.accept()
                 return

            # If not clearing, proceed with temporary point placement / panning
            self.draw_point(pos, QColor("gray"), radius=6, temporary=True) # Show click feedback
            # Let MainWindow find nearest node via callback
            self.on_point_selected(None, pos.x(), pos.y()) # Let MainWindow decide if it's start/end
            # Don't accept the event here, allow base class panning if no tool active
            if self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
                 super().mousePressEvent(event) # Allow panning
            else:
                 event.accept() # Accept if a tool *was* active but we clicked elsewhere


    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self._is_drawing_traffic_light_line and self._traffic_light_line_item:
            # Update the temporary effect line end point
            line = self._traffic_light_line_item.line()
            line.setP2(pos)
            self._traffic_light_line_item.setLine(line)
            event.accept()
        elif self._is_drawing_traffic and self._traffic_line_item:
            line = self._traffic_line_item.line()
            line.setP2(pos)
            self._traffic_line_item.setLine(line)
            event.accept()
        elif self._is_drawing_rain_area and self._rain_area_rect_item:
            rect = QRectF(self._rain_area_start, pos).normalized()
            self._rain_area_rect_item.setRect(rect)
            event.accept()
        elif self._is_drawing_block_way and self._block_way_line_item:
            line = self._block_way_line_item.line()
            line.setP2(pos)
            self._block_way_line_item.setLine(line)
            event.accept()
        else:
            # Allow panning
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        pos = self.mapToScene(event.pos())
        if self._is_drawing_traffic_light_line and self._traffic_light_line_item:
            # Finalize traffic light placement: create permanent visuals
            line = self._traffic_light_line_item.line()
            final_icon_pos = self._traffic_light_icon_pos
            final_line_start = line.p1() # Should be same as icon pos
            final_line_end = line.p2()

            # Remove temporary items
            self.scene.removeItem(self._traffic_light_line_item)
            self._traffic_light_line_item = None
            if self._current_traffic_light_icon_item: # Remove temp icon used during line draw
                self.scene.removeItem(self._current_traffic_light_icon_item)
                self._current_traffic_light_icon_item = None

            # Create permanent visuals (icon, line, and text)
            perm_icon_item = self.draw_traffic_light_icon(final_icon_pos)
            perm_line_item = self.draw_traffic_light_effect_line(final_line_start, final_line_end)
            # Create the countdown text item (initially empty or showing default)
            perm_text_item = self.create_traffic_light_countdown_text(final_icon_pos)

            # Store visuals (MainWindow will add instance data later via signal handler)
            traffic_light_data = {
                "type": "traffic_light",
                "icon_pos": final_icon_pos,
                "line_start": final_line_start,
                "line_end": final_line_end
                # Instance and durations added by MainWindow
            }
            perm_icon_item.setData(EFFECT_DATA_KEY, traffic_light_data) # Link data
            perm_line_item.setData(EFFECT_DATA_KEY, traffic_light_data) # Link data
            perm_text_item.setData(EFFECT_DATA_KEY, traffic_light_data) # Link data too
            # Store tuple including the text item
            self.traffic_light_visuals.append((perm_icon_item, perm_line_item, perm_text_item, traffic_light_data))

            # Emit signal with all info, including the new text item
            self.traffic_light_visuals_created.emit(final_icon_pos, final_line_start, final_line_end, perm_icon_item, perm_line_item, perm_text_item)

            # Reset state and cursor
            self._is_drawing_traffic_light_line = False
            self._traffic_light_icon_pos = None
            self._traffic_light_line_start = None
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # Uncheck the button in the sidebar - MainWindow should handle this via signal/slot
            event.accept()

        elif self._is_drawing_traffic and self._traffic_line_item:
            # Finalize traffic jam line
            final_line = self._traffic_line_item.line()
            self.scene.removeItem(self._traffic_line_item)
            self._traffic_line_item = None

            perm_line = QGraphicsLineItem(final_line)
            perm_line.setPen(QPen(QColor("red"), 2))
            perm_line.setToolTip("Traffic Jam")
            self.scene.addItem(perm_line)
            self.traffic_jam_lines.append(perm_line) # Store permanent item

            self.traffic_line_drawn.emit(final_line.p1(), final_line.p2()) # Emit signal

            # Reset state, cursor, and uncheck button
            self._is_drawing_traffic = False
            self._traffic_line_start = None
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # self.parent().sidebar.traffic_jam_button.setChecked(False)
            event.accept()

        elif self._is_drawing_rain_area and self._rain_area_rect_item:
            # Finalize rain area
            final_rect = self._rain_area_rect_item.rect()
            self.scene.removeItem(self._rain_area_rect_item)
            self._rain_area_rect_item = None

            perm_rect = QGraphicsRectItem(final_rect)
            perm_rect.setBrush(QBrush(QColor(0, 0, 255, 80))) # Slightly less transparent final
            perm_rect.setPen(QPen(QColor("blue"), 1))
            perm_rect.setToolTip("Rain Area")
            self.scene.addItem(perm_rect)
            self.rain_area_visuals.append(perm_rect) # Store permanent item

            self.rain_area_defined.emit(final_rect) # Emit signal

            # Reset state, cursor, and uncheck button
            self._is_drawing_rain_area = False
            self._rain_area_start = None
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # self.parent().sidebar.rain_area_button.setChecked(False)
            event.accept()

        elif self._is_drawing_block_way and self._block_way_line_item:
            # Finalize block way line
            final_line = self._block_way_line_item.line()
            self.scene.removeItem(self._block_way_line_item)
            self._block_way_line_item = None

            perm_line = QGraphicsLineItem(final_line)
            perm_line.setPen(QPen(QColor("black"), 3)) # Solid black line
            perm_line.setToolTip("Blocked Way")
            self.scene.addItem(perm_line)
            self.block_way_visuals.append(perm_line) # Store permanent item

            self.block_way_drawn.emit(final_line.p1(), final_line.p2()) # Emit signal

            # Reset state, cursor, and uncheck button
            self._is_drawing_block_way = False
            self._block_way_start = None
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # self.parent().sidebar.block_way_button.setChecked(False)
            event.accept()

        else:
            # Clear temporary selection point if it exists
            self.clear_temporary_point()
            # Allow panning release
            super().mouseReleaseEvent(event)


    # --- Point Drawing ---
    def draw_point(self, pos: QPointF, color, radius=5, temporary=False, point_type=None):
        """Draws a point (circle) on the map."""
        # Clear previous temporary point if drawing a new one
        if temporary:
            self.clear_temporary_point(point_type) # Pass type to clear specific temp if needed

        ellipse = QGraphicsEllipseItem(pos.x() - radius, pos.y() - radius, 2 * radius, 2 * radius)
        ellipse.setBrush(QBrush(color))
        ellipse.setPen(QPen(Qt.PenStyle.NoPen)) # No border for points usually
        self.scene.addItem(ellipse)

        if temporary:
            self._temporary_point_item = ellipse # Store reference to temporary item
        return ellipse # Return the item

    def clear_temporary_point(self, point_type=None): # Added point_type, though not used yet
        """Removes the temporary point marker from the scene."""
        if self._temporary_point_item:
            self.scene.removeItem(self._temporary_point_item)
            self._temporary_point_item = None

    def set_permanent_point(self, point_type, pos: QPointF):
        """Sets or updates the permanent start or end point marker."""
        if point_type == "start":
            if self._permanent_start_item:
                self.scene.removeItem(self._permanent_start_item)
            self._permanent_start_item = self.draw_point(pos, QColor("green"), radius=7)
            self._permanent_start_item.setToolTip(f"Start Point ({pos.x():.1f}, {pos.y():.1f})")
        elif point_type == "end":
            if self._permanent_end_item:
                self.scene.removeItem(self._permanent_end_item)
            self._permanent_end_item = self.draw_point(pos, QColor("blue"), radius=7)
            self._permanent_end_item.setToolTip(f"End Point ({pos.x():.1f}, {pos.y():.1f})")

    def clear_permanent_point(self, point_type):
        """Clears a specific permanent point marker."""
        if point_type == "start" and self._permanent_start_item:
            self.scene.removeItem(self._permanent_start_item)
            self._permanent_start_item = None
        elif point_type == "end" and self._permanent_end_item:
            self.scene.removeItem(self._permanent_end_item)
            self._permanent_end_item = None

    # --- Traffic Light Visuals --- New Methods ---
    def draw_traffic_light_icon(self, pos: QPointF, temporary=False):
        """Draws the traffic light icon at the given position."""
        if TRAFFIC_LIGHT_PIXMAP.isNull(): # Fallback if icon failed to load
            # Draw a simple placeholder, e.g., a colored circle
            radius = 8
            ellipse = QGraphicsEllipseItem(pos.x() - radius, pos.y() - radius, 2 * radius, 2 * radius)
            ellipse.setBrush(QBrush(QColor("purple"))) # Placeholder color
            ellipse.setPen(QPen(Qt.PenStyle.NoPen))
            item = ellipse
        else:
            pixmap_item = QGraphicsPixmapItem(TRAFFIC_LIGHT_PIXMAP)
            # Center the pixmap on the position
            pixmap_item.setOffset(pos - QPointF(TRAFFIC_LIGHT_PIXMAP.width() / 2, TRAFFIC_LIGHT_PIXMAP.height() / 2))
            item = pixmap_item

        item.setToolTip("Traffic Light")
        if temporary:
             item.setOpacity(0.7) # Make temporary visuals slightly transparent
        self.scene.addItem(item)
        return item

    def draw_traffic_light_effect_line(self, p1: QPointF, p2: QPointF):
        """Draws the permanent effect line for a traffic light."""
        line = QGraphicsLineItem(QLineF(p1, p2))
        # Use a distinct style, maybe orange?
        pen = QPen(QColor("orange"), 2, Qt.PenStyle.SolidLine)
        line.setPen(pen)
        line.setToolTip("Traffic Light Effect Area")
        self.scene.addItem(line)
        return line

    def create_traffic_light_countdown_text(self, icon_pos: QPointF):
        """Creates and adds the text item for the countdown timer."""
        text_item = QGraphicsSimpleTextItem("") # Start empty
        text_item.setFont(COUNTDOWN_FONT)
        text_item.setBrush(QBrush(COUNTDOWN_COLOR))
        # Position it slightly below or beside the icon
        # Adjust offset as needed based on icon size
        text_offset = QPointF(0, TRAFFIC_LIGHT_PIXMAP.height() / 2 + 2)
        text_item.setPos(icon_pos + text_offset)
        text_item.setZValue(3) # Ensure text is on top
        # Optional: Add background for better visibility
        # text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations) # Keep text size constant? Maybe not desired.
        # A background rect could be added separately and grouped if needed.
        self.scene.addItem(text_item)
        return text_item

    def update_traffic_light_countdown(self, text_item: QGraphicsSimpleTextItem, remaining_seconds: int):
        """Updates the text of the countdown display item."""
        if text_item and text_item.scene() == self.scene: # Check if item still exists
             text_item.setText(str(remaining_seconds))
             # Color is now handled by update_traffic_light_visual_state

    def update_traffic_light_visual_state(self, icon_item: QGraphicsPixmapItem, text_item: QGraphicsSimpleTextItem, state_name: str):
        """Updates the visual appearance (tooltip and text color) of a traffic light."""
        # Update tooltip
        color_map_text = {"red": "Red", "yellow": "Yellow", "green": "Green"}
        state_text = color_map_text.get(state_name, "Unknown")
        icon_item.setToolTip(f"Traffic Light ({state_text})")

        # Update text color
        if text_item and text_item.scene() == self.scene:
            color_map_brush = {
                TrafficLightState.RED: QColor("red"),
                TrafficLightState.YELLOW: QColor("yellow"),
                TrafficLightState.GREEN: QColor("lime") # Use lime for better visibility than dark green
            }
            text_color = color_map_brush.get(state_name, COUNTDOWN_COLOR) # Default to white if state unknown
            text_item.setBrush(QBrush(text_color))


    # --- Clearing Methods ---
    def clear_path(self):
        for item in self.path_items:
            self.scene.removeItem(item)
        self.path_items.clear()

    def clear_traffic_jams(self):
        for item in self.traffic_jam_lines:
            self.scene.removeItem(item)
        self.traffic_jam_lines.clear()

    def clear_rain_areas(self):
        for item in self.rain_area_visuals:
            self.scene.removeItem(item)
        self.rain_area_visuals.clear()

    def clear_block_ways(self):
        for item in self.block_way_visuals:
            self.scene.removeItem(item)
        self.block_way_visuals.clear()

    def clear_traffic_lights(self):
        """Clears all traffic light visuals (icon, line, text)."""
        for icon_item, line_item, text_item, _ in self.traffic_light_visuals:
            if icon_item and icon_item.scene() == self.scene: # Check if still in scene
                 self.scene.removeItem(icon_item)
            if line_item and line_item.scene() == self.scene:
                 self.scene.removeItem(line_item)
            if text_item and text_item.scene() == self.scene: # Remove text item
                 self.scene.removeItem(text_item)
        self.traffic_light_visuals.clear()
        # Note: Timers associated with these need to be stopped in MainWindow

    def clear_all_effects(self):
        """Clears all types of effects."""
        self.clear_traffic_jams()
        self.clear_rain_areas()
        self.clear_block_ways()
        self.clear_traffic_lights()
        self.effects_changed.emit() # Signal recalculation after clearing all

    # --- Path Drawing ---
    def draw_path(self, path, node_positions):
        self.clear_path()
        if not path or len(path) < 2:
            return

        pen = QPen(QColor("magenta"), 3) # Path color
        for i in range(len(path) - 1):
            try:
                u, v = path[i], path[i+1]
                pos_u = QPointF(*node_positions[u]) # Unpack tuple
                pos_v = QPointF(*node_positions[v]) # Unpack tuple
                line = QGraphicsLineItem(QLineF(pos_u, pos_v))
                line.setPen(pen)
                line.setZValue(1) # Draw path above effects slightly
                self.scene.addItem(line)
                self.path_items.append(line)
            except KeyError as e:
                print(f"Warning: Node position not found for {e} while drawing path.")
            except Exception as e:
                print(f"Error drawing path segment: {e}")

    # --- Zooming ---
    def wheelEvent(self, event):
        zoom_in_factor = 1.1
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

        # Move scene to keep mouse pointer over the same spot
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    # --- Helper (Consider removing if not needed) ---
    # def _get_sidebar_tool(self, tool_type):
    #     # This approach is generally discouraged (tight coupling)
    #     # Pass necessary data (like durations) through signals instead.
    #     # Placeholder if absolutely needed, but try to avoid.
    #     # if hasattr(self.parent(), 'sidebar'):
    #     #     if tool_type == 'traffic_light':
    #     #         return self.parent().sidebar.traffic_light_tool
    #     return None




