"""
This module defines the BackupService, which is responsible for managing the
file monitoring background thread and handling the core backup logic.
"""

import os
import shutil
import zipfile
from datetime import datetime

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from backup_handler import BackupHandler

class BackupService(QObject):
    """
    Manages the lifecycle of the file monitoring thread and BackupHandler.
    This service acts as an intermediary between the UI and the backup logic,
    decoupling them.
    """
    # Signals that the UI can connect to, to stay updated.
    monitoring_status_changed = pyqtSignal(bool)
    status_update_requested = pyqtSignal(str)
    backup_created = pyqtSignal(str)
    backup_pruned = pyqtSignal(str)
    backup_notification_requested = pyqtSignal(str, str) # title, message
    status_notification_requested = pyqtSignal(str, str) # title, message

    def __init__(self, saves_folder, backup_folder, backup_count, compress_backups, parent=None):
        super().__init__(parent)
        self.saves_folder = saves_folder
        self.backup_folder = backup_folder
        self.backup_count = backup_count
        self.compress_backups = compress_backups

        self.backup_thread = None
        self.backup_handler = None

    def start_monitoring(self):
        """
        Starts the file monitoring worker thread.
        """
        if self.backup_thread and self.backup_thread.isRunning():
            return # Already running

        self.backup_thread = QThread()
        self.backup_handler = BackupHandler(
            saves_folder=self.saves_folder,
            backup_folder=self.backup_folder,
            backup_count=self.backup_count,
            # Pass the emit methods of our own signals as callbacks
            status_callback=self.status_update_requested.emit,
            created_callback=self.backup_created.emit,
            pruned_callback=self.backup_pruned.emit,
            backup_notification_callback=self.backup_notification_requested.emit,
            status_notification_callback=self.status_notification_requested.emit,
            compress_backups=self.compress_backups
        )
        
        # Move the worker object to the new thread
        self.backup_handler.moveToThread(self.backup_thread)

        # Connect the thread's started signal to the worker's main run method
        self.backup_thread.started.connect(self.backup_handler.run)
        
        self.backup_thread.start()
        self.monitoring_status_changed.emit(True)
        self.status_notification_requested.emit("Monitoring Started", "Sims4Rewind is now actively monitoring your save files.")
        print("Monitoring thread started.")

    def stop_monitoring(self):
        """
        Stops the file monitoring worker thread gracefully.
        """
        if not (self.backup_thread and self.backup_thread.isRunning()):
            return

        if self.backup_handler:
            self.backup_handler.stop()
        
        self.backup_thread.quit()
        self.backup_thread.wait(5000) # Wait up to 5s for clean exit

        self.monitoring_status_changed.emit(False)
        self.status_notification_requested.emit("Monitoring Stopped", "Sims4Rewind has stopped monitoring.")
        print("Monitoring thread stopped.")

    def update_settings(self, saves_folder, backup_folder, backup_count, compress_backups):
        """Updates the settings for the backup service."""
        self.saves_folder = saves_folder
        self.backup_folder = backup_folder
        self.backup_count = backup_count
        self.compress_backups = compress_backups
        # If monitoring is active, restart it with the new settings
        if self.backup_thread and self.backup_thread.isRunning():
            self.stop_monitoring()
            self.start_monitoring()

    def restore_backup_file(self, backup_source_path: str, destination_path: str, original_savename: str, is_compressed: bool, is_live_restore: bool = False) -> None:
        """
        Restores a backup file to the specified destination.
        Handles both compressed (.zip) and uncompressed (.bak) backups.
        If is_live_restore is True, it will rename the existing live save file as a safety precaution.
        """
        try:
            if is_live_restore:
                # Handle safety backup for live restore
                if os.path.exists(destination_path):
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    safety_path = f"{destination_path}.pre-restore-{timestamp}"
                    shutil.move(destination_path, safety_path)
                    self.status_notification_requested.emit("Restore Info", f"Renamed existing live save to {os.path.basename(safety_path)} as safety backup.")

            if is_compressed:
                with zipfile.ZipFile(backup_source_path, 'r') as zf:
                    # Extract the original save file from the zip to the chosen destination
                    # The destination_path includes the filename, so we extract to its dirname
                    extract_to_dir = os.path.dirname(destination_path) if not is_live_restore else os.path.dirname(destination_path)
                    zf.extract(original_savename, extract_to_dir)
                    
                    # If it's restore to location, rename the extracted file to the desired destination_path
                    if not is_live_restore:
                        extracted_file_path = os.path.join(extract_to_dir, original_savename)
                        os.rename(extracted_file_path, destination_path)
            else:
                shutil.copy2(backup_source_path, destination_path)
            
            self.status_notification_requested.emit("Restore Success", f"Successfully restored {os.path.basename(backup_source_path)}.")

        except Exception as e:
            self.status_notification_requested.emit("Restore Error", f"An error occurred during restore: {e}")
            raise # Re-raise the exception for the UI to handle
