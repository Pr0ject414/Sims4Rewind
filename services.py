"""
This module defines the BackupService, which is responsible for managing the
file monitoring background thread and handling the core backup logic.
"""

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