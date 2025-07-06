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
from PyQt6.QtCore import QThread, pyqtSignal, QMetaObject, Qt
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
    monitoring_status_changed = pyqtSignal(bool)
    status_update_requested = pyqtSignal(str)
    backup_list_changed = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.ui = Ui_Sims4RewindApp()
        self.ui.setupUi(self)
        self._set_window_icon()

        self.config_manager = ConfigManager()
        self.startup_manager = StartupManager()
        self.backup_thread = None
        self.backup_handler = None
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

        # Connect thread-safe signals
        self.status_update_requested.connect(self._update_status_label)
        self.backup_list_changed.connect(self._rescan_and_update_backup_view)
        self.ui.backup_filter_dropdown.currentIndexChanged.connect(self._update_backup_list_display)

    def _load_initial_settings(self):
        """Loads settings from the config file and populates the UI."""
        settings = self.config_manager.load_settings()

        for widget in [self.ui.saves_folder_path, self.ui.backup_folder_path,
                       self.ui.backup_count_spinbox, self.ui.startup_checkbox,
                       self.ui.auto_monitor_checkbox]:
            widget.blockSignals(True)

        self.ui.saves_folder_path.setText(settings.get("saves_folder"))
        self.ui.backup_folder_path.setText(settings.get("backup_folder"))
        self.ui.backup_count_spinbox.setValue(settings.get("backup_count"))
        self.ui.auto_monitor_checkbox.setChecked(settings.get("auto_monitor_on_startup"))
        self.ui.startup_checkbox.setChecked(self.startup_manager.is_enabled())

        for widget in [self.ui.saves_folder_path, self.ui.backup_folder_path,
                       self.ui.backup_count_spinbox, self.ui.startup_checkbox,
                       self.ui.auto_monitor_checkbox]:
            widget.blockSignals(False)
        self._rescan_and_update_backup_view()

    def _rescan_and_update_backup_view(self):
        """
        Scans the backup folder, organizes backups, then updates the filter dropdown
        and the visible backup list. This is the new master refresh function.
        """
        backup_folder = self.ui.backup_folder_path.text()
        self.organized_backups.clear()

        if not os.path.isdir(backup_folder):
            self._populate_filter_dropdown()
            self._update_backup_list_display()
            return

        try:
            files = [f for f in os.listdir(backup_folder) if f.endswith('.bak')]
            for filename in files:
                original_name = get_original_from_backup(filename)
                if original_name:
                    self.organized_backups[original_name].append(filename)
        except Exception as e:
            self._update_status_label(f"Error reading backup folder: {e}")
        
        self._populate_filter_dropdown()
        self._update_backup_list_display()

    def _populate_filter_dropdown(self):
        """Populates the filter dropdown with unique save file names."""
        dropdown = self.ui.backup_filter_dropdown
        # Store current selection to try and preserve it
        current_selection = dropdown.currentText()

        dropdown.blockSignals(True) # Prevent triggering a refresh while we repopulate
        dropdown.clear()
        
        dropdown.addItem("Show All Backups")
        
        sorted_save_names = sorted(self.organized_backups.keys())
        for name in sorted_save_names:
            dropdown.addItem(name)
        
        # Try to restore the previous selection
        index = dropdown.findText(current_selection)
        if index != -1:
            dropdown.setCurrentIndex(index)

        dropdown.blockSignals(False)

    def _update_backup_list_display(self):
        """
        Clears and repopulates the backup list widget based on the current
        filter selection.
        """
        self.ui.backup_list_widget.clear()
        filter_key = self.ui.backup_filter_dropdown.currentText()
        backup_folder = self.ui.backup_folder_path.text()
        
        files_to_display = []

        if filter_key == "Show All Backups":
            # Flatten the list of all backups from all keys
            for key in self.organized_backups:
                files_to_display.extend(self.organized_backups[key])
        elif filter_key in self.organized_backups:
            # Show backups only for the selected save file
            files_to_display = self.organized_backups[filter_key]
        
        if not files_to_display:
            return

        # Sort the final list by modification time (most recent first)
        try:
            files_to_display.sort(
                key=lambda f: os.path.getmtime(os.path.join(backup_folder, f)),
                reverse=True
            )
            self.ui.backup_list_widget.addItems(files_to_display)
        except FileNotFoundError:
            # This can happen if a file is deleted between scanning and sorting
            self._update_status_label("A backup file was deleted. Refreshing list...")
            self._rescan_and_update_backup_view()
        except Exception as e:
            self._update_status_label(f"Error displaying backups: {e}")


    def _check_for_autostart(self):
        settings = self.config_manager.load_settings()
        auto_monitor = settings.get("auto_monitor_on_startup", False)

        if "--startup" in sys.argv and auto_monitor:
            print("Launched on startup, auto-starting monitoring.")
            QMetaObject.invokeMethod(self.ui.toggle_monitoring_button, 'setChecked', Qt.ConnectionType.QueuedConnection, True)

    def _save_current_settings(self):
        settings = {
            "saves_folder": self.ui.saves_folder_path.text(),
            "backup_folder": self.ui.backup_folder_path.text(),
            "backup_count": self.ui.backup_count_spinbox.value(),
            "auto_monitor_on_startup": self.ui.auto_monitor_checkbox.isChecked()
        }
        self.config_manager.save_settings(settings)
        print("Settings saved.")

    def closeEvent(self, event):
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
        if self.backup_handler:
            self.backup_handler.stop()
        if self.backup_thread:
            self.backup_thread.quit()
            self.backup_thread.wait()

        self._save_current_settings()
        QApplication.instance().quit()

    def _update_status_label(self, message):
        """Thread-safe method to update the status label."""
        self.ui.status_label.setText(f"Status: {message}")

    def _browse_saves_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Sims 4 Saves Folder")
        if folder:
            self.ui.saves_folder_path.setText(folder)

    def _browse_backup_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Location")
        if folder:
            self.ui.backup_folder_path.setText(folder)
            self._rescan_and_update_backup_view()

    def _restore_backup(self):
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
        """Starts or stops the file monitoring thread."""
        self.monitoring_status_changed.emit(checked)
        if checked:
            saves_folder = self.ui.saves_folder_path.text()
            backup_folder = self.ui.backup_folder_path.text()

            if not os.path.isdir(saves_folder) or not os.path.isdir(backup_folder):
                QMessageBox.warning(self, "Error", "Please select valid Sims 4 Saves and Backup folders.")
                self.ui.toggle_monitoring_button.setChecked(False)
                return

            self.ui.toggle_monitoring_button.setText("Stop Monitoring")

            self.backup_thread = QThread()
            self.backup_handler = BackupHandler(
                saves_folder=saves_folder,
                backup_folder=backup_folder,
                backup_count=self.ui.backup_count_spinbox.value(),
                status_callback=self.status_update_requested.emit,
                created_callback=self.backup_list_changed.emit
            )
            self.backup_handler.moveToThread(self.backup_thread)

            self.backup_thread.started.connect(self.backup_handler.run)
            self.backup_thread.start()
        else:
            if self.backup_handler:
                self.backup_handler.stop()
            if self.backup_thread:
                self.backup_thread.quit()
                self.backup_thread.wait()
            self._update_status_label("Idle.")
            self.ui.toggle_monitoring_button.setText("Start Monitoring")

    def _toggle_startup(self, checked):
        """Enables or disables the app from running on Windows startup."""
        self.startup_manager.set_startup(checked)