# =====================================================================
# FILE: main.py
# =====================================================================
# This is the main entry point for the Sims4Rewind application.
# It now ensures only a single instance of the app can run at a time,
# launches the system tray icon, and manages the main window.

import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QSharedMemory
from main_window import Sims4RewindApp
from system_tray import SystemTrayIcon

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # --- SINGLE INSTANCE CHECK START ---
    # Use a unique key for the shared memory block
    unique_key = "Sims4Rewind_single_instance_lock"
    shared_memory = QSharedMemory(unique_key)

    # Attempt to create the shared memory segment.
    # If it returns false, another instance is already running.
    if not shared_memory.create(1):
        # Show a message box to the user
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText("An instance of Sims4Rewind is already running.")
        msg_box.setInformativeText("Please check your system tray. The application will now exit.")
        msg_box.setWindowTitle("Sims4Rewind - Already Running")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
        sys.exit(0) # Exit cleanly
    # --- SINGLE INSTANCE CHECK END ---

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