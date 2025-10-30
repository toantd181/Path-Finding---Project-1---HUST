from PyQt6.QtWidgets import (QGraphicsView, QGraphicsScene,
                             QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsLineItem,
                             QGraphicsRectItem, QGraphicsSimpleTextItem)
from PyQt6.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QIcon, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QLineF
import os
from .tools.traffic_light_tool import TrafficLightState

EFFECT_DATA_KEY = Qt.ItemDataRole.UserRole + 1

# Traffic Light Icon
TRAFFIC_LIGHT_ICON_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'icons', 'traffic-light.png')
TRAFFIC_LIGHT_ICON = QIcon(TRAFFIC_LIGHT_ICON_PATH)
TRAFFIC_LIGHT_PIXMAP = TRAFFIC_LIGHT_ICON.pixmap(32, 32)
if TRAFFIC_LIGHT_PIXMAP.isNull():
    print(f"Warning: Could not load traffic light icon: {TRAFFIC_LIGHT_ICON_PATH}")

COUNTDOWN_FONT = QFont("Arial", 10, QFont.Weight.Bold)
COUNTDOWN_COLOR = QColor("white")

class MapViewer(QGraphicsView):
    # Signals
    traffic_line_drawn = pyqtSignal(QPointF, QPointF)
    block_way_drawn = pyqtSignal(QPointF, QPointF)
    effects_changed = pyqtSignal()
    traffic_light_visuals_created = pyqtSignal(QPointF, QPointF, QPointF, QGraphicsPixmapItem, QGraphicsLineItem, QGraphicsSimpleTextItem)

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
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.scale_factor = 1.0
        self.on_point_selected = on_point_selected

        # Point and Path Items
        self._permanent_start_item = None
        self._permanent_end_item = None
        self._temporary_point_item = None
        self.path_items = []
        self.waypoint_markers = []  # Store waypoint visual markers

        # Effect Visuals Storage
        self.traffic_jam_lines = []
        self.block_way_visuals = []
        self.traffic_light_visuals = []

        # Drawing States
        self._is_drawing_traffic = False
        self._traffic_line_start = None
        self._traffic_line_item = None

        self._is_drawing_block_way = False
        self._block_way_start = None
        self._block_way_line_item = None

        self._is_placing_traffic_light_icon = False
        self._is_drawing_traffic_light_line = False
        self._traffic_light_icon_pos = None
        self._traffic_light_line_start = None
        self._traffic_light_line_item = None
        self._current_traffic_light_icon_item = None

        # Selection modes
        self._is_selecting_start = False
        self._is_selecting_end = False
        self._is_selecting_waypoint = False

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        # Improve interaction
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def set_waypoint_selection_mode(self, enabled: bool):
        """Set mode for selecting waypoints"""
        self._is_selecting_start = False
        self._is_selecting_end = False
        self._is_selecting_waypoint = enabled
        self._is_drawing_traffic = False
        self._is_drawing_block_way = False
        self._is_placing_traffic_light_icon = False
        self._is_drawing_traffic_light_line = False
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    # Drawing Mode Setters
    def set_start_selection_mode(self, enabled: bool):
        """Set mode for selecting start point"""
        self._is_selecting_start = enabled
        self._is_selecting_end = False
        self._is_selecting_waypoint = False
        self._is_drawing_traffic = False
        self._is_drawing_block_way = False
        self._is_placing_traffic_light_icon = False
        self._is_drawing_traffic_light_line = False
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_end_selection_mode(self, enabled: bool):
        """Set mode for selecting end point"""
        self._is_selecting_start = False
        self._is_selecting_end = enabled
        self._is_selecting_waypoint = False
        self._is_drawing_traffic = False
        self._is_drawing_block_way = False
        self._is_placing_traffic_light_icon = False
        self._is_drawing_traffic_light_line = False
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def set_traffic_drawing_mode(self, enabled: bool):
        self._is_selecting_start = False
        self._is_selecting_end = False
        self._is_selecting_waypoint = False
        self._is_drawing_traffic = enabled
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
        self._is_selecting_start = False
        self._is_selecting_end = False
        self._is_selecting_waypoint = False
        self._is_drawing_traffic = False
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
        self._is_selecting_start = False
        self._is_selecting_end = False
        self._is_selecting_waypoint = False
        self._is_drawing_traffic = False
        self._is_drawing_block_way = False
        self._is_placing_traffic_light_icon = enabled
        self._is_drawing_traffic_light_line = False
        if enabled:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._cleanup_temp_drawing()

    def _cleanup_temp_drawing(self):
        """Removes temporary drawing items."""
        if self._traffic_line_item:
            self.scene.removeItem(self._traffic_line_item)
            self._traffic_line_item = None
        if self._block_way_line_item:
            self.scene.removeItem(self._block_way_line_item)
            self._block_way_line_item = None
        if self._traffic_light_line_item:
            self.scene.removeItem(self._traffic_light_line_item)
            self._traffic_light_line_item = None
        if self._current_traffic_light_icon_item:
             self.scene.removeItem(self._current_traffic_light_icon_item)
             self._current_traffic_light_icon_item = None
        
        self._traffic_line_start = None
        self._block_way_start = None
        self._traffic_light_icon_pos = None
        self._traffic_light_line_start = None

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        pos = self.mapToScene(event.pos())
        modifiers = event.modifiers()

        # Shift+Click: Remove Effect
        if modifiers == Qt.KeyboardModifier.ShiftModifier:
            item = self.itemAt(event.pos())
            if item and self._remove_effect_at_item(item):
                event.accept()
                return

        # Handle drawing modes
        if self._is_placing_traffic_light_icon:
            self._handle_traffic_light_icon_placement(pos)
            event.accept()
        elif self._is_drawing_traffic_light_line:
            self._start_traffic_light_line_drawing(pos)
            event.accept()
        elif self._is_drawing_traffic:
            self._start_traffic_line_drawing(pos)
            event.accept()
        elif self._is_drawing_block_way:
            self._start_block_way_drawing(pos)
            event.accept()
        else:
            # Normal mode: Select start/end point
            self._handle_point_selection(event, pos)

    def _remove_effect_at_item(self, item):
        """Remove effect at the given item. Returns True if something was removed."""
        removed = False
        removed_data = None

        if item in self.traffic_jam_lines:
            self.scene.removeItem(item)
            self.traffic_jam_lines.remove(item)
            removed = True
        elif item in self.block_way_visuals:
            self.scene.removeItem(item)
            self.block_way_visuals.remove(item)
            removed = True
        else:
            # Check traffic lights
            for i, (icon_item, line_item, text_item, data) in enumerate(self.traffic_light_visuals):
                if item in (icon_item, line_item, text_item):
                    self.scene.removeItem(icon_item)
                    self.scene.removeItem(line_item)
                    self.scene.removeItem(text_item)
                    removed_visual_tuple = self.traffic_light_visuals.pop(i)
                    removed_data = removed_visual_tuple[3]
                    if isinstance(item, (QGraphicsPixmapItem, QGraphicsLineItem, QGraphicsSimpleTextItem)):
                        item.setData(EFFECT_DATA_KEY, removed_data)
                    removed = True
                    break

        if removed:
            print(f"Removed effect item. Data: {removed_data}")
            self.effects_changed.emit()
        return removed

    def _handle_traffic_light_icon_placement(self, pos):
        """Handle placement of traffic light icon"""
        self._traffic_light_icon_pos = pos
        self._current_traffic_light_icon_item = self.draw_traffic_light_icon(pos, temporary=True)
        self._is_placing_traffic_light_icon = False
        self._is_drawing_traffic_light_line = True
        self._traffic_light_line_start = pos
        self.setCursor(Qt.CursorShape.CrossCursor)
        print(f"Traffic light icon placed at {pos}, now draw effect line.")

    def _start_traffic_light_line_drawing(self, pos):
        """Start drawing the traffic light effect line"""
        if not self._traffic_light_line_item:
            pen = QPen(QColor("orange"), 2, Qt.PenStyle.DashLine)
            self._traffic_light_line_item = QGraphicsLineItem(QLineF(self._traffic_light_line_start, pos))
            self._traffic_light_line_item.setPen(pen)
            self.scene.addItem(self._traffic_light_line_item)

    def _start_traffic_line_drawing(self, pos):
        """Start drawing traffic line"""
        self._traffic_line_start = pos
        pen = QPen(QColor("red"), 2, Qt.PenStyle.DashLine)
        self._traffic_line_item = QGraphicsLineItem(QLineF(pos, pos))
        self._traffic_line_item.setPen(pen)
        self.scene.addItem(self._traffic_line_item)

    def _start_block_way_drawing(self, pos):
        """Start drawing block way line"""
        self._block_way_start = pos
        pen = QPen(QColor("black"), 3, Qt.PenStyle.DashLine)
        self._block_way_line_item = QGraphicsLineItem(QLineF(pos, pos))
        self._block_way_line_item.setPen(pen)
        self.scene.addItem(self._block_way_line_item)

    def _handle_point_selection(self, event, pos):
        """Handle point selection for start/end"""
        # First check if clicking on existing markers
        item = self.itemAt(event.pos())
        
        if item == self._permanent_start_item or item == self._permanent_end_item:
            # Don't allow clicking markers in selection mode - use clear buttons instead
            self.clear_temporary_point()
            event.accept()
            return

        # Show temporary feedback
        if self._is_selecting_start:
            self.draw_point(pos, QColor("lightgreen"), radius=8, temporary=True)
            self.on_point_selected("start", pos.x(), pos.y())
        elif self._is_selecting_end:
            self.draw_point(pos, QColor("lightblue"), radius=8, temporary=True)
            self.on_point_selected("end", pos.x(), pos.y())
        else:
            # Normal mode - just visual feedback
            self.draw_point(pos, QColor("gray"), radius=6, temporary=True)
        
        if self.dragMode() == QGraphicsView.DragMode.ScrollHandDrag:
            super().mousePressEvent(event)
        else:
            event.accept()

    def mouseMoveEvent(self, event):
        pos = self.mapToScene(event.pos())
        
        if self._is_drawing_traffic_light_line and self._traffic_light_line_item:
            line = self._traffic_light_line_item.line()
            line.setP2(pos)
            self._traffic_light_line_item.setLine(line)
            event.accept()
        elif self._is_drawing_traffic and self._traffic_line_item:
            line = self._traffic_line_item.line()
            line.setP2(pos)
            self._traffic_line_item.setLine(line)
            event.accept()
        elif self._is_drawing_block_way and self._block_way_line_item:
            line = self._block_way_line_item.line()
            line.setP2(pos)
            self._block_way_line_item.setLine(line)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        pos = self.mapToScene(event.pos())
        
        if self._is_drawing_traffic_light_line and self._traffic_light_line_item:
            self._finalize_traffic_light(pos)
            event.accept()
        elif self._is_drawing_traffic and self._traffic_line_item:
            self._finalize_traffic_line()
            event.accept()
        elif self._is_drawing_block_way and self._block_way_line_item:
            self._finalize_block_way()
            event.accept()
        else:
            self.clear_temporary_point()
            super().mouseReleaseEvent(event)

    def _finalize_traffic_light(self, pos):
        """Finalize traffic light placement"""
        line = self._traffic_light_line_item.line()
        final_icon_pos = self._traffic_light_icon_pos
        final_line_start = line.p1()
        final_line_end = line.p2()

        self.scene.removeItem(self._traffic_light_line_item)
        self._traffic_light_line_item = None
        if self._current_traffic_light_icon_item:
            self.scene.removeItem(self._current_traffic_light_icon_item)
            self._current_traffic_light_icon_item = None

        perm_icon_item = self.draw_traffic_light_icon(final_icon_pos)
        perm_line_item = self.draw_traffic_light_effect_line(final_line_start, final_line_end)
        perm_text_item = self.create_traffic_light_countdown_text(final_icon_pos)

        traffic_light_data = {
            "type": "traffic_light",
            "icon_pos": final_icon_pos,
            "line_start": final_line_start,
            "line_end": final_line_end
        }
        perm_icon_item.setData(EFFECT_DATA_KEY, traffic_light_data)
        perm_line_item.setData(EFFECT_DATA_KEY, traffic_light_data)
        perm_text_item.setData(EFFECT_DATA_KEY, traffic_light_data)
        
        self.traffic_light_visuals.append((perm_icon_item, perm_line_item, perm_text_item, traffic_light_data))
        self.traffic_light_visuals_created.emit(final_icon_pos, final_line_start, final_line_end, perm_icon_item, perm_line_item, perm_text_item)

        self._is_drawing_traffic_light_line = False
        self._traffic_light_icon_pos = None
        self._traffic_light_line_start = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _finalize_traffic_line(self):
        """Finalize traffic jam line"""
        final_line = self._traffic_line_item.line()
        self.scene.removeItem(self._traffic_line_item)
        self._traffic_line_item = None

        perm_line = QGraphicsLineItem(final_line)
        perm_line.setPen(QPen(QColor("red"), 2))
        perm_line.setToolTip("Traffic Jam")
        self.scene.addItem(perm_line)
        self.traffic_jam_lines.append(perm_line)

        self.traffic_line_drawn.emit(final_line.p1(), final_line.p2())

        self._is_drawing_traffic = False
        self._traffic_line_start = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def _finalize_block_way(self):
        """Finalize block way line"""
        final_line = self._block_way_line_item.line()
        self.scene.removeItem(self._block_way_line_item)
        self._block_way_line_item = None

        perm_line = QGraphicsLineItem(final_line)
        perm_line.setPen(QPen(QColor("black"), 3))
        perm_line.setToolTip("Blocked Way")
        self.scene.addItem(perm_line)
        self.block_way_visuals.append(perm_line)

        self.block_way_drawn.emit(final_line.p1(), final_line.p2())

        self._is_drawing_block_way = False
        self._block_way_start = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setCursor(Qt.CursorShape.ArrowCursor)

    # Point Drawing
    def draw_point(self, pos: QPointF, color, radius=5, temporary=False, point_type=None):
        """Draws a point (circle) on the map."""
        if temporary:
            self.clear_temporary_point(point_type)

        ellipse = QGraphicsEllipseItem(pos.x() - radius, pos.y() - radius, 2 * radius, 2 * radius)
        ellipse.setBrush(QBrush(color))
        ellipse.setPen(QPen(Qt.PenStyle.NoPen))
        self.scene.addItem(ellipse)

        if temporary:
            self._temporary_point_item = ellipse
        return ellipse

    def clear_temporary_point(self, point_type=None):
        """Removes the temporary point marker from the scene."""
        if self._temporary_point_item:
            self.scene.removeItem(self._temporary_point_item)
            self._temporary_point_item = None

    def set_permanent_point(self, point_type, pos: QPointF):
        """Sets or updates the permanent start or end point marker."""
        if point_type == "start":
            if self._permanent_start_item:
                self.scene.removeItem(self._permanent_start_item)
            self._permanent_start_item = self.draw_point(pos, QColor("green"), radius=8)
            self._permanent_start_item.setToolTip(f"Start Point")
        elif point_type == "end":
            if self._permanent_end_item:
                self.scene.removeItem(self._permanent_end_item)
            self._permanent_end_item = self.draw_point(pos, QColor("blue"), radius=8)
            self._permanent_end_item.setToolTip(f"End Point")

    def clear_permanent_point(self, point_type):
        """Clears a specific permanent point marker."""
        if point_type == "start" and self._permanent_start_item:
            self.scene.removeItem(self._permanent_start_item)
            self._permanent_start_item = None
        elif point_type == "end" and self._permanent_end_item:
            self.scene.removeItem(self._permanent_end_item)
            self._permanent_end_item = None

    # Traffic Light Visuals
    def draw_traffic_light_icon(self, pos: QPointF, temporary=False):
        """Draws the traffic light icon at the given position."""
        if TRAFFIC_LIGHT_PIXMAP.isNull():
            radius = 8
            ellipse = QGraphicsEllipseItem(pos.x() - radius, pos.y() - radius, 2 * radius, 2 * radius)
            ellipse.setBrush(QBrush(QColor("purple")))
            ellipse.setPen(QPen(Qt.PenStyle.NoPen))
            item = ellipse
        else:
            pixmap_item = QGraphicsPixmapItem(TRAFFIC_LIGHT_PIXMAP)
            pixmap_item.setOffset(pos - QPointF(TRAFFIC_LIGHT_PIXMAP.width() / 2, TRAFFIC_LIGHT_PIXMAP.height() / 2))
            item = pixmap_item

        item.setToolTip("Traffic Light")
        if temporary:
            item.setOpacity(0.7)
        self.scene.addItem(item)
        return item

    def draw_traffic_light_effect_line(self, p1: QPointF, p2: QPointF):
        """Draws the permanent effect line for a traffic light."""
        line = QGraphicsLineItem(QLineF(p1, p2))
        pen = QPen(QColor("orange"), 2, Qt.PenStyle.SolidLine)
        line.setPen(pen)
        line.setToolTip("Traffic Light Effect Area")
        self.scene.addItem(line)
        return line

    def create_traffic_light_countdown_text(self, icon_pos: QPointF):
        """Creates and adds the text item for the countdown timer."""
        text_item = QGraphicsSimpleTextItem("")
        text_item.setFont(COUNTDOWN_FONT)
        text_item.setBrush(QBrush(COUNTDOWN_COLOR))
        text_offset = QPointF(0, TRAFFIC_LIGHT_PIXMAP.height() / 2 + 2)
        text_item.setPos(icon_pos + text_offset)
        text_item.setZValue(3)
        self.scene.addItem(text_item)
        return text_item

    def update_traffic_light_countdown(self, text_item: QGraphicsSimpleTextItem, remaining_seconds: int):
        """Updates the text of the countdown display item."""
        if text_item and text_item.scene() == self.scene:
            text_item.setText(str(remaining_seconds))

    def update_traffic_light_visual_state(self, icon_item: QGraphicsPixmapItem, text_item: QGraphicsSimpleTextItem, state_name: str):
        """Updates the visual appearance of a traffic light."""
        color_map_text = {"red": "Red", "yellow": "Yellow", "green": "Green"}
        state_text = color_map_text.get(state_name, "Unknown")
        icon_item.setToolTip(f"Traffic Light ({state_text})")

        if text_item and text_item.scene() == self.scene:
            color_map_brush = {
                TrafficLightState.RED: QColor("red"),
                TrafficLightState.YELLOW: QColor("yellow"),
                TrafficLightState.GREEN: QColor("lime")
            }
            text_color = color_map_brush.get(state_name, COUNTDOWN_COLOR)
            text_item.setBrush(QBrush(text_color))

    # Clearing Methods
    def clear_path(self):
        for item in self.path_items:
            self.scene.removeItem(item)
        self.path_items.clear()

    def clear_traffic_jams(self):
        for item in self.traffic_jam_lines:
            self.scene.removeItem(item)
        self.traffic_jam_lines.clear()

    def clear_block_ways(self):
        for item in self.block_way_visuals:
            self.scene.removeItem(item)
        self.block_way_visuals.clear()

    def clear_traffic_lights(self):
        """Clears all traffic light visuals."""
        for icon_item, line_item, text_item, _ in self.traffic_light_visuals:
            if icon_item and icon_item.scene() == self.scene:
                self.scene.removeItem(icon_item)
            if line_item and line_item.scene() == self.scene:
                self.scene.removeItem(line_item)
            if text_item and text_item.scene() == self.scene:
                self.scene.removeItem(text_item)
        self.traffic_light_visuals.clear()

    def clear_all_effects(self):
        """Clears all types of effects."""
        self.clear_traffic_jams()
        self.clear_block_ways()
        self.clear_traffic_lights()
        self.effects_changed.emit()

    # Path Drawing
    def draw_path(self, path, node_positions):
        self.clear_path()
        if not path or len(path) < 2:
            return

        pen = QPen(QColor("magenta"), 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        
        for i in range(len(path) - 1):
            try:
                u, v = path[i], path[i+1]
                pos_u = QPointF(*node_positions[u])
                pos_v = QPointF(*node_positions[v])
                line = QGraphicsLineItem(QLineF(pos_u, pos_v))
                line.setPen(pen)
                line.setZValue(1)
                self.scene.addItem(line)
                self.path_items.append(line)
            except KeyError as e:
                print(f"Warning: Node position not found for {e} while drawing path.")
            except Exception as e:
                print(f"Error drawing path segment: {e}")

    # Zooming
    def wheelEvent(self, event):
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