# =====================================================================
# FILE: main_window.py
# =====================================================================
# This file defines the main application logic, now with a filterable
# backup list for improved user experience.

import os
import sys
import shutil
import base64
from collections import defaultdict
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QMetaObject, Qt, QTimer
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QApplication
from config import ConfigManager
from ui_main_window import Ui_Sims4RewindApp
from backup_handler import BackupHandler
from startup_manager import StartupManager
from utils import get_original_from_backup
from resources import ICON_DATA_REWIND

class Sims4RewindApp(QMainWindow):
    """
    Main application window class.
    Connects the UI from Ui_Sims4RewindApp to the application logic.
    """
    # --- THREAD-SAFE SIGNALS ---
    # These signals are emitted from the worker thread or from within the main
    # thread to safely trigger UI updates.
    monitoring_status_changed = pyqtSignal(bool)
    status_update_requested = pyqtSignal(str)
    # These signals now carry data to prevent race conditions. The UI will
    # update its state based on this data instead of re-reading the filesystem.
    backup_created = pyqtSignal(str) # Carries the new backup filename
    backup_pruned = pyqtSignal(str)  # Carries the pruned backup filename

    def __init__(self):
        super().__init__()

        self.ui = Ui_Sims4RewindApp()
        self.ui.setupUi(self)
        self._set_window_icon()

        self.config_manager = ConfigManager()
        self.startup_manager = StartupManager()
        self.backup_thread = None
        self.backup_handler = None
        self.autostart_timer = None
        self.autostart_retries = 0

        # This dictionary is the in-memory "source of truth" for the state of backups.
        # It is updated by signals and used to populate the UI.
        self.organized_backups = defaultdict(list)

        self._connect_signals()
        self._load_initial_settings()
        self._check_for_autostart()

    def _set_window_icon(self):
        """Sets the main window icon from the embedded resource data."""
        try:
            icon_data = base64.b64decode(ICON_DATA_REWIND)
            pixmap = QPixmap()
            pixmap.loadFromData(icon_data)
            self.setWindowIcon(QIcon(pixmap))
        except Exception as e:
            print(f"Could not load window icon from resources: {e}")

    def _connect_signals(self):
        """Connects all widget signals to their corresponding slots."""
        self.ui.browse_saves_button.clicked.connect(self._browse_saves_folder)
        self.ui.browse_backups_button.clicked.connect(self._browse_backup_folder)
        self.ui.restore_button.clicked.connect(self._restore_backup)
        self.ui.toggle_monitoring_button.toggled.connect(self._toggle_monitoring)
        self.ui.startup_checkbox.toggled.connect(self._toggle_startup)

        # Connect thread-safe signals to their handler methods (slots)
        self.status_update_requested.connect(self._update_status_label)
        self.backup_created.connect(self._on_backup_created)
        self.backup_pruned.connect(self._on_backup_pruned)
        self.ui.backup_filter_dropdown.currentIndexChanged.connect(self._update_backup_list_display)

    def _load_initial_settings(self):
        """Loads settings from the config file and populates the UI."""
        settings = self.config_manager.load_settings()

        # Block signals to prevent triggering events while we programmatically set values
        for widget in [self.ui.saves_folder_path, self.ui.backup_folder_path,
                       self.ui.backup_count_spinbox, self.ui.startup_checkbox,
                       self.ui.auto_monitor_checkbox]:
            widget.blockSignals(True)

        self.ui.saves_folder_path.setText(settings.get("saves_folder"))
        self.ui.backup_folder_path.setText(settings.get("backup_folder"))
        self.ui.backup_count_spinbox.setValue(settings.get("backup_count"))
        self.ui.auto_monitor_checkbox.setChecked(settings.get("auto_monitor_on_startup"))
        self.ui.startup_checkbox.setChecked(self.startup_manager.is_enabled())

        # Unblock signals now that initial values are set
        for widget in [self.ui.saves_folder_path, self.ui.backup_folder_path,
                       self.ui.backup_count_spinbox, self.ui.startup_checkbox,
                       self.ui.auto_monitor_checkbox]:
            widget.blockSignals(False)

        # Perform an initial scan of the backup folder to populate the UI
        self._rescan_and_update_backup_view()

    def _rescan_and_update_backup_view(self):
        """
        Scans the backup folder from the filesystem. This is the master
        refresh function, intended to be called only on startup or when a
        folder path is changed by the user.
        """
        backup_folder = self.ui.backup_folder_path.text()
        self.organized_backups.clear() # Reset the in-memory model

        if not os.path.isdir(backup_folder):
            self._populate_filter_dropdown()
            self._update_backup_list_display()
            return

        try:
            files = [f for f in os.listdir(backup_folder) if f.endswith('.bak')]
            for filename in files:
                original_name = get_original_from_backup(filename)
                if original_name:
                    # Add the file to our in-memory dictionary
                    self.organized_backups[original_name].append(filename)
        except Exception as e:
            self._update_status_label(f"Error reading backup folder: {e}")
        
        self._populate_filter_dropdown()
        self._update_backup_list_display()

    def _on_backup_created(self, new_backup_filename):
        """
        Slot that handles the `backup_created` signal. Updates the in-memory
        model with the new backup file, avoiding a full disk rescan.
        """
        original_name = get_original_from_backup(new_backup_filename)
        if not original_name:
            return

        # Check if this is a backup for a brand new save file
        is_new_save_type = original_name not in self.organized_backups

        # Add the new backup to our in-memory list
        self.organized_backups[original_name].append(new_backup_filename)

        # If it's a new type of save, we need to refresh the filter dropdown
        if is_new_save_type:
            self._populate_filter_dropdown()

        # Always refresh the list of visible backups
        self._update_backup_list_display()

    def _on_backup_pruned(self, pruned_backup_filename):
        """
        Slot that handles the `backup_pruned` signal. Removes the pruned file
        from the in-memory model.
        """
        original_name = get_original_from_backup(pruned_backup_filename)
        if not original_name:
            return

        # Safely remove the pruned file from our in-memory list
        if original_name in self.organized_backups:
            if pruned_backup_filename in self.organized_backups[original_name]:
                self.organized_backups[original_name].remove(pruned_backup_filename)
        
        # Refresh the visible list to reflect the removal
        self._update_backup_list_display()

    def _populate_filter_dropdown(self):
        """Populates the filter dropdown with unique save file names from the in-memory model."""
        dropdown = self.ui.backup_filter_dropdown
        current_selection = dropdown.currentText()

        dropdown.blockSignals(True)
        dropdown.clear()
        
        dropdown.addItem("Show All Backups")
        
        # Sort keys from our in-memory dictionary for a consistent order
        sorted_save_names = sorted(self.organized_backups.keys())
        for name in sorted_save_names:
            dropdown.addItem(name)
        
        index = dropdown.findText(current_selection)
        if index != -1:
            dropdown.setCurrentIndex(index)

        dropdown.blockSignals(False)

    def _update_backup_list_display(self):
        """
        Clears and repopulates the backup list widget based on the current
        filter selection, using the in-memory `organized_backups` dictionary.
        """
        self.ui.backup_list_widget.clear()
        filter_key = self.ui.backup_filter_dropdown.currentText()
        backup_folder = self.ui.backup_folder_path.text()
        
        files_to_display = []

        if filter_key == "Show All Backups":
            # Flatten the list of all backups from all keys in our model
            for key in self.organized_backups:
                files_to_display.extend(self.organized_backups[key])
        elif filter_key in self.organized_backups:
            # Show backups only for the selected save file from our model
            files_to_display = self.organized_backups[filter_key]
        
        if not files_to_display:
            return

        # Sort the final list by modification time (most recent first)
        try:
            # Note: A filesystem read is still required here for sorting by time,
            # but it is much safer than listing the directory. The risk of a
            # race condition is negligible as we are only reading metadata of
            # files we already know exist from our model.
            files_to_display.sort(
                key=lambda f: os.path.getmtime(os.path.join(backup_folder, f)),
                reverse=True
            )
            self.ui.backup_list_widget.addItems(files_to_display)
        except FileNotFoundError:
            # This can happen in the rare case a file is deleted outside the app
            # between the signal and this UI update. A full rescan will fix it.
            self._update_status_label("A backup file was deleted. Refreshing list...")
            self._rescan_and_update_backup_view()
        except Exception as e:
            self._update_status_label(f"Error displaying backups: {e}")

    def _check_for_autostart(self):
        """
        Checks if the app was launched on startup and, if so, initiates
        monitoring with a delay and retry mechanism to handle slow-to-mount
        drives (like Google Drive).
        """
        settings = self.config_manager.load_settings()
        auto_monitor = settings.get("auto_monitor_on_startup", False)

        if "--startup" in sys.argv and auto_monitor:
            print("Launched on startup. Will attempt to start monitoring shortly...")
            self._update_status_label("Waiting for folders to become available...")
            
            # Defer the first check to allow the system to settle.
            self.autostart_timer = QTimer(self)
            self.autostart_timer.setSingleShot(True)
            self.autostart_timer.timeout.connect(self._attempt_autostart_monitoring)
            self.autostart_timer.start(5000) # Start after 5 seconds

    def _attempt_autostart_monitoring(self):
        """
        Periodically checks if the configured save/backup paths are valid.
        If they are, it starts monitoring. If not, it retries a few times.
        """
        MAX_RETRIES = 30 # Total wait time will be 30 * 20s = 600 seconds (10 minutes)
        RETRY_INTERVAL_MS = 20000 # 20 seconds

        saves_folder = self.ui.saves_folder_path.text()
        backup_folder = self.ui.backup_folder_path.text()

        paths_are_valid = os.path.isdir(saves_folder) and os.path.isdir(backup_folder)

        if paths_are_valid:
            print("Folders are valid. Starting monitoring.")
            self._update_status_label("Folders detected. Starting monitoring...")
            # Use a queued connection to ensure this toggle happens cleanly in the main event loop
            QMetaObject.invokeMethod(self.ui.toggle_monitoring_button, 'toggle', Qt.ConnectionType.QueuedConnection)
            if self.autostart_timer:
                self.autostart_timer.stop()
            return

        # If paths are not valid, retry if we have attempts left
        self.autostart_retries += 1
        if self.autostart_retries <= MAX_RETRIES:
            print(f"Folders not ready. Retrying in {RETRY_INTERVAL_MS / 1000}s... (Attempt {self.autostart_retries}/{MAX_RETRIES})")
            self._update_status_label(f"Folders not ready. Retrying... ({self.autostart_retries}/{MAX_RETRIES})")

            # Set up the next retry
            self.autostart_timer.setSingleShot(True) # Ensure it only runs once per timeout
            self.autostart_timer.timeout.disconnect() # Disconnect previous connection to be safe
            self.autostart_timer.timeout.connect(self._attempt_autostart_monitoring)
            self.autostart_timer.start(RETRY_INTERVAL_MS)
        else:
            # If we've exhausted all retries, show a persistent error
            print("Failed to validate folders after multiple retries. Aborting autostart.")
            self._update_status_label("Error: Could not find folders. Monitoring disabled.")
            QMessageBox.warning(self, "Autostart Failed",
                                "Sims 4 Rewind could not find your configured Saves or Backup folder after several attempts.\n\n"
                                "Please ensure the locations are correct and accessible, then start monitoring manually.")
            
    def _save_current_settings(self):
        """Saves the current UI settings to the config file."""
        settings = {
            "saves_folder": self.ui.saves_folder_path.text(),
            "backup_folder": self.ui.backup_folder_path.text(),
            "backup_count": self.ui.backup_count_spinbox.value(),
            "auto_monitor_on_startup": self.ui.auto_monitor_checkbox.isChecked()
        }
        self.config_manager.save_settings(settings)
        print("Settings saved.")

    def closeEvent(self, event):
        """Handles the user trying to close the window."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Minimize or Exit?")
        msg_box.setText("What would you like to do?")
        msg_box.setIcon(QMessageBox.Icon.Question)

        minimize_button = msg_box.addButton("Minimize to Tray", QMessageBox.ButtonRole.ActionRole)
        exit_button = msg_box.addButton("Exit Application", QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.setDefaultButton(minimize_button)
        msg_box.exec()

        clicked = msg_box.clickedButton()

        if clicked == minimize_button:
            self.hide()
            self._update_status_label("Running in system tray.")
            event.ignore()
        elif clicked == exit_button:
            self.app_quit()
        else:
            event.ignore()
            
    def app_quit(self):
        """Gracefully stops all background processes and exits the application."""
        if self.backup_handler:
            self.backup_handler.stop()
        if self.backup_thread:
            self.backup_thread.quit()
            self.backup_thread.wait() # Wait for the thread to finish cleanly

        self._save_current_settings()
        QApplication.instance().quit()

    def _update_status_label(self, message):
        """Thread-safe method to update the status label."""
        self.ui.status_label.setText(f"Status: {message}")

    def _browse_saves_folder(self):
        """Opens a dialog to select the Sims 4 saves folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Sims 4 Saves Folder")
        if folder:
            self.ui.saves_folder_path.setText(folder)

    def _browse_backup_folder(self):
        """Opens a dialog to select the backup folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Location")
        if folder:
            self.ui.backup_folder_path.setText(folder)
            self._rescan_and_update_backup_view() # Rescan filesystem on manual change

    def _restore_backup(self):
        """Restores a selected backup file to the live saves folder."""
        selected_item = self.ui.backup_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Restore Error", "Please select a backup file from the list first.")
            return

        backup_filename = selected_item.text()
        saves_folder = self.ui.saves_folder_path.text()
        backup_folder = self.ui.backup_folder_path.text()

        original_savename = get_original_from_backup(backup_filename)
        if not original_savename:
            QMessageBox.critical(self, "Restore Error", f"Could not determine original save name from '{backup_filename}'.")
            return

        reply = QMessageBox.question(self, "Confirm Restore",
            f"This will restore the backup:\n\n{backup_filename}\n\n"
            f"The current live file '{original_savename}' will be renamed as a safety precaution.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)

        if reply != QMessageBox.StandardButton.Yes:
            self._update_status_label("Restore operation cancelled.")
            return

        try:
            live_save_path = os.path.join(saves_folder, original_savename)
            backup_source_path = os.path.join(backup_folder, backup_filename)

            if not os.path.exists(live_save_path):
                QMessageBox.information(self, "Info", f"The file '{original_savename}' does not currently exist in the saves folder. A new one will be created from the backup.")
            else:
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                safety_backup_path = f"{live_save_path}.pre-restore-{timestamp}"
                shutil.move(live_save_path, safety_backup_path)
                print(f"Safety rename: '{live_save_path}' -> '{safety_backup_path}'")

            shutil.copy2(backup_source_path, live_save_path)

            QMessageBox.information(self, "Success", f"Successfully restored '{original_savename}'.\n"
                                                      "The previous live file was saved as a '.pre-restore' file.")
            self._update_status_label(f"Successfully restored {original_savename}.")

        except Exception as e:
            QMessageBox.critical(self, "Restore Failed", f"An unexpected error occurred during restore:\n\n{e}")
            self._update_status_label("Restore failed. See error popup.")

    def _toggle_monitoring(self, checked):
        """Starts or stops the file monitoring worker thread."""
        self.monitoring_status_changed.emit(checked)
        if checked:
            saves_folder = self.ui.saves_folder_path.text()
            backup_folder = self.ui.backup_folder_path.text()

            # --- PATH VALIDATION ---
            # Ensure paths are valid directories before starting the thread.
            if not os.path.isdir(saves_folder):
                QMessageBox.warning(self, "Invalid Path", f"The Saves Folder is not a valid directory:\n{saves_folder}")
                self.ui.toggle_monitoring_button.setChecked(False) # Revert button state
                return
            if not os.path.isdir(backup_folder):
                QMessageBox.warning(self, "Invalid Path", f"The Backup Location is not a valid directory:\n{backup_folder}")
                self.ui.toggle_monitoring_button.setChecked(False) # Revert button state
                return

            self.ui.toggle_monitoring_button.setText("Stop Monitoring")

            # --- SETUP WORKER THREAD ---
            self.backup_thread = QThread()
            self.backup_handler = BackupHandler(
                saves_folder=saves_folder,
                backup_folder=backup_folder,
                backup_count=self.ui.backup_count_spinbox.value(),
                # Pass the emit methods of our signals directly as callbacks
                status_callback=self.status_update_requested.emit,
                created_callback=self.backup_created.emit,
                pruned_callback=self.backup_pruned.emit
            )
            # Move the worker object to the new thread
            self.backup_handler.moveToThread(self.backup_thread)

            # Connect the thread's started signal to the worker's main run method
            self.backup_thread.started.connect(self.backup_handler.run)
            self.backup_thread.start()
        else:
            # --- STOP WORKER THREAD ---
            if self.backup_handler:
                self.backup_handler.stop()
            if self.backup_thread:
                self.backup_thread.quit()
                self.backup_thread.wait() # Wait for clean exit
            self._update_status_label("Idle.")
            self.ui.toggle_monitoring_button.setText("Start Monitoring")

    def _toggle_startup(self, checked):
        """Enables or disables the app from running on Windows startup."""
        self.startup_manager.set_startup(checked)