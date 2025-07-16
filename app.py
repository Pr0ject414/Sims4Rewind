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
from system_tray import SystemTrayIcon
from ui.main_window import Sims4RewindApp
from ui.view_model import BackupViewModel
from ui import dialogs # Import dialogs

__version__ = "1.0.1" # Main application version

def main():
    """Application entry point."""
    print("Python sys.path:")
    for p in sys.path:
        print(f"  {p}")
    print("\n")

    # Create the main application instance
    app = QApplication(sys.argv)


    

    # --- Dependency Creation ---
    # Create components that don't depend on others first
    backup_view_model = BackupViewModel()
    startup_manager = StartupManager()

    # Create the main window, passing initial dependencies
    window = Sims4RewindApp(
        config_manager=None, # Will be set later
        backup_service=None, # Will be set later
        backup_view_model=backup_view_model,
        startup_manager=startup_manager,
        updater=None # Pass the updater instance
    )

    # Now create components that depend on the window's signals or other components
    config_manager = ConfigManager(log_message_callback=window.log_message_requested.emit)
    
    # Load settings to initialize the service
    settings = config_manager.load_settings()
    backup_service = BackupService(
        saves_folder=settings.get("saves_folder"),
        backup_folder=settings.get("backup_folder"),
        backup_count=settings.get("backup_count"),
        compress_backups=settings.get("compress_backups"),
        log_message_requested=window.log_message_requested # Pass the signal directly
    )

    # Now that config_manager and backup_service are fully created, set them in the window
    window.set_dependencies_and_connect_signals(config_manager, backup_service)

    # --- Update Check (Google Drive) ---
    try:
        from private_update.updater_google_drive import GoogleDriveUpdater

        updater = GoogleDriveUpdater(log_callback=window.log_message_requested.emit)
        window.updater = updater # Set the updater instance in the window
        window.show_update_button(True) # Show the update button

        # Perform initial update check on startup
        update_available, latest_version = updater.check_for_update()
        if update_available:
            if dialogs.ask_question(window, "Update Available", f"Version {latest_version} is available. Do you want to download and install it?"):
                downloaded_zip = updater.download_update()
                if downloaded_zip:
                    if dialogs.ask_question(window, "Install Update", "Update downloaded. Application needs to restart to install. Continue?"):
                        if updater.install_update(downloaded_zip):
                            sys.exit(0) # Exit the current app to allow updater to take over
                        else:
                            window.log_message_requested.emit("Update installation failed.")
                    else:
                        window.log_message_requested.emit("Update installation cancelled.")
                else:
                    window.log_message_requested.emit("Update download failed.")
            else:
                window.log_message_requested.emit("Update cancelled by user.")

    except ImportError as e:
        window.log_message_requested.emit(f"Google Drive update functionality not available (private_update module not found). Error: {e}")
        import traceback
        window.log_message_requested.emit("Traceback:\n" + traceback.format_exc())
    except Exception as e:
        window.log_message_requested.emit(f"Error during Google Drive update check: {e}")

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
