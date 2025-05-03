from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from .tools.sidebar import Sidebar

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Path Finding Application")
        self.setGeometry(100, 100, 800, 600)

        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Layout for the central widget
        layout = QVBoxLayout(central_widget)

        # Create and add the sidebar
        self.sidebar = Sidebar()
        layout.addWidget(self.sidebar)

        # Add more widgets and layout configurations as needed
        # For example, you could add a main area for displaying the pathfinding grid or results.