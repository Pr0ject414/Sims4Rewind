import base64
import os
import shutil
from datetime import datetime

from PyQt6.QtCore import QMetaObject, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QMainWindow

from ui_main_window import Ui_Sims4RewindApp
from resources import ICON_DATA_REWIND
from utils import get_original_from_backup
from . import dialogs # Use relative import within the UI package

class Sims4RewindApp(QMainWindow):
    """
    This module contains the main application window (the View).
    Its sole responsibility is to display data from the ViewModel and delegate
    user actions to the appropriate services.
    """
    def __init__(self, config_manager, backup_service, backup_view_model, startup_manager):
        super().__init__()

        # Injected dependencies
        self.config = config_manager
        self.service = backup_service
        self.view_model = backup_view_model
        self.startup = startup_manager

        # UI setup
        self.ui = Ui_Sims4RewindApp()
        self.ui.setupUi(self)
        self._set_window_icon()

        self._connect_ui_signals()
        self._connect_service_signals()
        
        self._load_initial_settings()

    def _set_window_icon(self):
        """Sets the main window icon from embedded resource data."""
        try:
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(ICON_DATA_REWIND))
            self.setWindowIcon(QIcon(pixmap))
        except Exception as e:
            print(f"Could not load window icon: {e}")

    def _connect_ui_signals(self):
        """Connects widget signals to methods in this class."""
        self.ui.browse_saves_button.clicked.connect(self._browse_saves_folder)
        self.ui.browse_backups_button.clicked.connect(self._browse_backup_folder)
        self.ui.restore_button.clicked.connect(self._restore_backup)
        self.ui.restore_to_button.clicked.connect(self._restore_backup_to_location)
        self.ui.toggle_monitoring_button.toggled.connect(self._toggle_monitoring)
        self.ui.startup_checkbox.toggled.connect(self.startup.set_startup)
        self.ui.backup_filter_dropdown.currentIndexChanged.connect(self._update_backup_list_display)
        self.ui.backup_list_widget.itemSelectionChanged.connect(self._update_ui_element_states)

    def _connect_service_signals(self):
        """Connects signals from services and models to UI update slots."""
        self.service.monitoring_status_changed.connect(self._on_monitoring_status_changed)
        self.service.status_update_requested.connect(self._update_status_label)
        self.service.backup_created.connect(self.view_model.on_backup_created)
        self.service.backup_pruned.connect(self.view_model.on_backup_pruned)
        self.view_model.model_updated.connect(self._on_view_model_updated)

    def _load_initial_settings(self):
        """Loads settings and populates the UI fields."""
        settings = self.config.load_settings()
        self.ui.saves_folder_path.setText(settings.get("saves_folder"))
        self.ui.backup_folder_path.setText(settings.get("backup_folder"))
        self.ui.backup_count_spinbox.setValue(settings.get("backup_count"))
        self.ui.auto_monitor_checkbox.setChecked(settings.get("auto_monitor_on_startup"))
        self.ui.startup_checkbox.setChecked(self.startup.is_enabled())
        self.view_model.rescan_backup_folder(settings.get("backup_folder"))
        self._update_ui_element_states()

    def _save_current_settings(self):
        """Saves the current UI settings to the config file."""
        settings = {
            "saves_folder": self.ui.saves_folder_path.text(),
            "backup_folder": self.ui.backup_folder_path.text(),
            "backup_count": self.ui.backup_count_spinbox.value(),
            "auto_monitor_on_startup": self.ui.auto_monitor_checkbox.isChecked()
        }
        self.config.save_settings(settings)
        print("Settings saved.")

    def _update_ui_element_states(self):
        """Enables or disables UI elements based on current state."""
        has_selection = self.ui.backup_list_widget.currentItem() is not None
        self.ui.restore_button.setEnabled(has_selection)

    # --- UI Update Slots (triggered by signals) ---

    def _on_monitoring_status_changed(self, is_monitoring):
        """Updates the UI when monitoring starts or stops."""
        self.ui.toggle_monitoring_button.setChecked(is_monitoring)
        self.ui.toggle_monitoring_button.setText("Stop Monitoring" if is_monitoring else "Start Monitoring")
        self._update_status_label("Monitoring active." if is_monitoring else "Idle.")

    def _on_view_model_updated(self):
        """Called when the view model's data changes. Refreshes the UI."""
        self._populate_filter_dropdown()
        self._update_backup_list_display()
        self._update_ui_element_states()

    def _update_status_label(self, message):
        """Updates the status bar with a new message."""
        self.ui.status_label.setText(f"Status: {message}")

    def _populate_filter_dropdown(self):
        """Populates the filter dropdown from the view model."""
        dropdown = self.ui.backup_filter_dropdown
        current_selection = dropdown.currentText()
        dropdown.blockSignals(True)
        dropdown.clear()
        dropdown.addItem("Show All Backups")
        dropdown.addItems(self.view_model.get_filter_options())
        index = dropdown.findText(current_selection)
        dropdown.setCurrentIndex(index if index != -1 else 0)
        dropdown.blockSignals(False)

    def _update_backup_list_display(self):
        """Repopulates the backup list from the view model based on the current filter."""
        self.ui.backup_list_widget.clear()
        filter_key = self.ui.backup_filter_dropdown.currentText()
        backup_folder = self.ui.backup_folder_path.text()
        backups = self.view_model.get_backups_for_display(filter_key, backup_folder)
        self.ui.backup_list_widget.addItems(backups)

    # --- User Action Handlers (triggered by UI signals) ---

    def _browse_saves_folder(self):
        """Delegates browsing for the saves folder."""
        folder = dialogs.browse_for_directory(self, "Select Sims 4 Saves Folder")
        if folder:
            self.ui.saves_folder_path.setText(folder)

    def _browse_backup_folder(self):
        """Delegates browsing for the backup folder."""
        folder = dialogs.browse_for_directory(self, "Select Backup Location")
        if folder:
            self.ui.backup_folder_path.setText(folder)
            self.view_model.rescan_backup_folder(folder)

    def _toggle_monitoring(self, checked):
        """Delegates starting or stopping monitoring to the backup service."""
        if checked:
            self._save_current_settings()
            self.service.update_settings(
                self.ui.saves_folder_path.text(),
                self.ui.backup_folder_path.text(),
                self.ui.backup_count_spinbox.value()
            )
            self.service.start_monitoring()
        else:
            self.service.stop_monitoring()

    def _restore_backup(self):
        """Handles the logic for restoring a selected backup."""
        selected_item = self.ui.backup_list_widget.currentItem()
        if not selected_item:
            return

        backup_filename = selected_item.text()
        original_savename = get_original_from_backup(backup_filename)
        if not original_savename:
            dialogs.show_critical(self, "Restore Error", f"Could not parse '{backup_filename}'.")
            return

        question = (f"This will restore the backup:\n\n{backup_filename}\n\n"
                    f"The current live file '{original_savename}' will be renamed as a safety precaution.\n\n"
                    "Are you sure you want to continue?")

        if not dialogs.ask_question(self, "Confirm Restore", question):
            self._update_status_label("Restore operation cancelled.")
            return

        try:
            saves_folder = self.ui.saves_folder_path.text()
            backup_folder = self.ui.backup_folder_path.text()
            live_save_path = os.path.join(saves_folder, original_savename)
            backup_source_path = os.path.join(backup_folder, backup_filename)

            if os.path.exists(live_save_path):
                timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                safety_path = f"{live_save_path}.pre-restore-{timestamp}"
                shutil.move(live_save_path, safety_path)
            
            shutil.copy2(backup_source_path, live_save_path)
            dialogs.show_info(self, "Success", f"Successfully restored '{original_savename}'.")
            self._update_status_label(f"Successfully restored {original_savename}.")
        except Exception as e:
            dialogs.show_critical(self, "Restore Failed", f"An unexpected error occurred: {e}")
            self._update_status_label("Restore failed. See error popup.")

    def _restore_backup_to_location(self):
        """Handles restoring a selected backup to a user-specified location."""
        selected_item = self.ui.backup_list_widget.currentItem()
        if not selected_item:
            dialogs.show_warning(self, "Restore Error", "Please select a backup file from the list first.")
            return

        backup_filename = selected_item.text()
        original_savename = get_original_from_backup(backup_filename)
        if not original_savename:
            dialogs.show_critical(self, "Restore Error", f"Could not parse original save name from '{backup_filename}'.")
            return

        # Suggest a default filename based on the original save name
        default_filename = original_savename
        
        # Open file dialog to get destination path and filename
        # We need to import QFileDialog for this
        from PyQt6.QtWidgets import QFileDialog
        destination_path, _ = QFileDialog.getSaveFileName(
            self, "Save Backup As", default_filename, "All Files (*)"
        )

        if not destination_path:
            self._update_status_label("Restore to location cancelled.")
            return

        try:
            backup_folder = self.ui.backup_folder_path.text()
            backup_source_path = os.path.join(backup_folder, backup_filename)
            
            shutil.copy2(backup_source_path, destination_path)
            dialogs.show_info(self, "Success", f"Successfully restored '{backup_filename}' to '{destination_path}'.")
            self._update_status_label(f"Successfully restored {backup_filename} to {destination_path}.")
        except Exception as e:
            dialogs.show_critical(self, "Restore Failed", f"An unexpected error occurred during restore:\n\n{e}")
            self._update_status_label("Restore to location failed. See error popup.")

    def closeEvent(self, event):
        """Handles the user trying to close the window."""
        action = dialogs.ask_minimize_or_exit(self)
        if action == "minimize":
            self.hide()
            event.ignore()
        elif action == "exit":
            self.service.stop_monitoring()
            self._save_current_settings()
            event.accept()
        else: # cancel
            event.ignore()
