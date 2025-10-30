import sys
from PyQt6.QtWidgets import QApplication

# Create QApplication first, before any imports that might use QPixmap
app = QApplication(sys.argv)

# Now import your main window
from app.main_window import MainWindow

# Create and show window
window = MainWindow()
window.show()
sys.exit(app.exec())