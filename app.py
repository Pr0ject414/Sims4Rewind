"""
Main application entry point.
This script is responsible for creating all application objects (services, models, UI)
and wiring them together before starting the event loop.
"""

import sys
from PyQt6.QtWidgets import QApplication

from config import ConfigManager
from services import BackupService
from startup_manager import StartupManager
from system_tray import SystemTrayIcon # Import SystemTrayIcon
from ui.main_window import Sims4RewindApp
from ui.view_model import BackupViewModel

def main():
    """Application entry point."""
    # Create the main application instance
    app = QApplication(sys.argv)

    # --- Dependency Creation ---
    # Create all the necessary components of our application.
    config_manager = ConfigManager()
    startup_manager = StartupManager()
    backup_view_model = BackupViewModel()
    
    # Load settings to initialize the service
    settings = config_manager.load_settings()
    backup_service = BackupService(
        saves_folder=settings.get("saves_folder"),
        backup_folder=settings.get("backup_folder"),
        backup_count=settings.get("backup_count"),
        compress_backups=settings.get("compress_backups")
    )

    # --- Dependency Injection ---
    # Create the main window and inject all the components it needs (its dependencies).
    window = Sims4RewindApp(
        config_manager=config_manager,
        backup_service=backup_service,
        backup_view_model=backup_view_model,
        startup_manager=startup_manager
    )
    
    # Setup System Tray Icon
    system_tray_icon = SystemTrayIcon(window) # Pass the main window to the tray icon
    system_tray_icon.show()

    # Connect notification signals from the backup service to the system tray
    backup_service.backup_notification_requested.connect(system_tray_icon.show_notification)
    backup_service.status_notification_requested.connect(system_tray_icon.show_notification)

    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
