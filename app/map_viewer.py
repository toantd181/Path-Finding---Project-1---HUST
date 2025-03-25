import sys
from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter

class MapViewer(QGraphicsView):
    def __init__(self, image_path, on_point_selected):
        super().__init__()
        # Tạo scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        # Load ảnh vào QPixmap
        pixmap = QPixmap(image_path)
        self.map_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.map_item)
        # Kích thước viewport
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        # Thu phóng mặc định
        self.scale_factor = 1.0
        self.on_point_selected = on_point_selected 
        self.selected_points = {"start": None, "end":None}
    def mousePressEvent(self, event):
        """Xử lý khi người dùng click chọn điểm"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.mapToScene(event.pos())
            self.selected_points["start"] = (pos.x(), pos.y())
            self.draw_point(pos, Qt.GlobalColor.green)  # Điểm bắt đầu (màu xanh)
            self.on_point_selected("start", pos.x(), pos.y())

        elif event.button() == Qt.MouseButton.RightButton:
            pos = self.mapToScene(event.pos())
            self.selected_points["end"] = (pos.x(), pos.y())
            self.draw_point(pos, Qt.GlobalColor.red)  # Điểm kết thúc (màu đỏ)
            self.on_point_selected("end", pos.x(), pos.y())

    def draw_point(self, pos, color):
        """Vẽ điểm chọn trên bản đồ"""
        pen = QPen(color)
        brush = QBrush(color)
        radius = 5
        self.scene.addEllipse(pos.x() - radius, pos.y() - radius, 10, 10, pen, brush)

    def draw_path(self, path, node_positions):
        """Vẽ đường đi tìm được"""
        pen = QPen(Qt.GlobalColor.blue, 3)
        for i in range(len(path) - 1):
            x1, y1 = node_positions[path[i]]
            x2, y2 = node_positions[path[i + 1]]
            self.scene.addLine(x1, y1, x2, y2, pen)

    def wheelEvent(self, event):
        """Xử lý sự kiện lăn chuột để zoom"""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
            self.scale_factor *= zoom_in_factor
        else:
            self.scale(zoom_out_factor, zoom_out_factor)
            self.scale_factor *= zoom_out_factor


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = MapViewer("assets/map.png")  # Đổi đường dẫn ảnh nếu cần
    viewer.show()
    sys.exit(app.exec())

