# =====================================================================
# FILE: system_tray.py
# =====================================================================
# This file defines the SystemTrayIcon class, which manages the
# application's presence and menu in the system tray.

import base64
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QWidget
from resources import ICON_DATA_REWIND # Import the encoded icon

class SystemTrayIcon(QSystemTrayIcon):
    """
    Manages the application's system tray icon and its context menu.
    """
    def __init__(self, main_window, parent=None):
        # FIX: The parent for Qt objects must be a QObject. A mock object is not.
        # We determine the real QWidget parent here for use by child widgets.
        widget_parent = main_window if isinstance(main_window, QWidget) else None
        
        super().__init__(widget_parent)
        self.main_window = main_window

        # --- Set the Icon ---
        # Decode the base64 data and load it into a QPixmap, then a QIcon
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(ICON_DATA_REWIND))
        self.setIcon(QIcon(pixmap))
        self.setToolTip("Sims4Rewind")

        # --- Create the Menu ---
        # FIX: QMenu's parent must be a QWidget or None.
        self.menu = QMenu(widget_parent)
        
        # Show/Hide Window Action
        self.show_action = QAction("Show/Hide Settings", self)
        self.show_action.triggered.connect(self.toggle_window)
        self.menu.addAction(self.show_action)

        # Start/Stop Monitoring Action
        self.monitoring_action = QAction("Start Monitoring", self)
        self.monitoring_action.setCheckable(True)
        # We connect this to the main window's toggle button's click method
        # This check makes the class testable with a simple mock object
        if hasattr(self.main_window, 'ui') and hasattr(self.main_window.ui, 'toggle_monitoring_button'):
            self.monitoring_action.triggered.connect(self.main_window.ui.toggle_monitoring_button.click)
        self.menu.addAction(self.monitoring_action)

        self.menu.addSeparator()

        # Exit Action
        self.exit_action = QAction("Exit", self)
        self.exit_action.triggered.connect(self.main_window.close)
        self.menu.addAction(self.exit_action)

        self.setContextMenu(self.menu)

        # Connect the tray icon's activation (e.g., left-click) to toggle the window
        self.activated.connect(self.on_activated)

    def on_activated(self, reason):
        """Handle activation events on the tray icon."""
        # Show the window on a left-click
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window()
    
    def toggle_window(self):
        """Shows the main window if it's hidden, and hides it if it's visible."""
        if self.main_window.isVisible():
            self.main_window.hide()
        else:
            self.main_window.show()
            self.main_window.activateWindow() # Bring to front

    def update_monitoring_action(self, is_monitoring):
        """Updates the text and checked state of the monitoring action in the menu."""
        self.monitoring_action.setChecked(is_monitoring)
        self.monitoring_action.setText("Stop Monitoring" if is_monitoring else "Start Monitoring")

    def show_notification(self, title, message, icon=QSystemTrayIcon.MessageIcon.Information, msecs=10000):
        """Displays a desktop notification from the system tray icon."""
        self.showMessage(title, message, icon, msecs)