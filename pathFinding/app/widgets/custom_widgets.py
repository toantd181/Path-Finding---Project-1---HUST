from PyQt6.QtWidgets import QPushButton

class FindPathButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Find Path")
        # Additional initialization can be added here if needed