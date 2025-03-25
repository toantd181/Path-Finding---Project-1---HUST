import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from map_viewer import MapViewer
from pathfinding import Pathfinding

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
        self.map_viewer = MapViewer("assets/map.png")
        layout.addWidget(self.map_viewer)

        central_widget.setLayout(layout)
        
        self.pathfinder = Pathfinding("data/graph.json")
        path = self.pathfinder.find_path("A", "C")
        self.map_viewer.draw_path(path, self.pathfinder.graph.nodes)
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

