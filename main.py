# =====================================================================
# FILE: main.py
# =====================================================================
# This is the main entry point for the Sims4Rewind application.
# It now launches the system tray icon and manages the main window.

import sys
from PyQt6.QtWidgets import QApplication
from main_window import Sims4RewindApp
from system_tray import SystemTrayIcon

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # This prevents the app from closing when the main window is hidden
    app.setQuitOnLastWindowClosed(False)

    # Create the main window but don't show it yet
    window = Sims4RewindApp()
    
    # Create the system tray icon and pass it a reference to the main window
    tray_icon = SystemTrayIcon(window)
    tray_icon.show()

    # Connect the window's monitoring status to the tray menu
    window.monitoring_status_changed.connect(tray_icon.update_monitoring_action)
    
    # If the app was NOT launched on startup, show the main window initially.
    # Otherwise, it will just start in the tray.
    if "--startup" not in sys.argv:
        window.show()

    sys.exit(app.exec())
