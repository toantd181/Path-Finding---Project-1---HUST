#!/usr/bin/env python3
"""
Pathfinding Application Launcher
"""
import sys
from PyQt6.QtWidgets import QApplication

def main():
    # Create QApplication FIRST
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Offline Pathfinding")
    app.setOrganizationName("ToantdDev")
    
    # Import AFTER QApplication exists
    from app.main_window import MainWindow
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()