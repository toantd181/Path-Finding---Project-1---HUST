from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from ..widgets.custom_widgets import FindPathButton

class Sidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)

        # --- Sidebar Contents ---
        title_label = QLabel("Tools")
        layout.addWidget(title_label)

        # Add Start and End point labels
        self.start_label = QLabel("Start: Not Selected")
        layout.addWidget(self.start_label)

        self.end_label = QLabel("End: Not Selected")
        layout.addWidget(self.end_label)

        # Find Path Button - Use the custom widget
        self.find_path_button = FindPathButton() # Instantiate the custom button
        layout.addWidget(self.find_path_button)

        # Add more widgets here if needed

        layout.addStretch() # Pushes content to the top