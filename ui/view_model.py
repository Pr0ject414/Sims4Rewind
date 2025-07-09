"""
This module defines the ViewModel for the backup list.
It holds the state and logic for filtering and displaying backups, completely
separating the UI state from the UI widgets.
"""

import os
from collections import defaultdict
from PyQt6.QtCore import QObject, pyqtSignal
from utils import get_original_from_backup

class BackupViewModel(QObject):
    """
    Manages the in-memory state of the backup list and provides filtered
    views for the UI.
    """
    # Signal emitted whenever the data changes, so the UI knows to refresh.
    model_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # The in-memory "source of truth" for the state of backups.
        self._organized_backups = defaultdict(list)

    def rescan_backup_folder(self, backup_folder):
        """
        Performs a full scan of the backup folder to rebuild the model.
        This should be called on startup or when the backup path changes.
        """
        self._organized_backups.clear()
        if not os.path.isdir(backup_folder):
            self.model_updated.emit()
            return

        try:
            files = [f for f in os.listdir(backup_folder) if f.endswith('.bak')]
            for filename in files:
                original_name = get_original_from_backup(filename)
                if original_name:
                    self._organized_backups[original_name].append(filename)
        except Exception as e:
            print(f"Error reading backup folder: {e}")
        
        self.model_updated.emit()

    def on_backup_created(self, new_backup_filename):
        """
        Updates the model with a newly created backup file, avoiding a full rescan.
        """
        original_name = get_original_from_backup(new_backup_filename)
        if not original_name:
            return

        self._organized_backups[original_name].append(new_backup_filename)
        self.model_updated.emit()

    def on_backup_pruned(self, pruned_backup_filename):
        """
        Updates the model by removing a pruned backup file.
        """
        original_name = get_original_from_backup(pruned_backup_filename)
        if not original_name or original_name not in self._organized_backups:
            return

        if pruned_backup_filename in self._organized_backups[original_name]:
            self._organized_backups[original_name].remove(pruned_backup_filename)
            # If no backups are left for this save, remove the key
            if not self._organized_backups[original_name]:
                del self._organized_backups[original_name]
        
        self.model_updated.emit()

    def get_filter_options(self):
        """Returns a sorted list of unique save file names for the filter dropdown."""
        return sorted(self._organized_backups.keys())

    def get_backups_for_display(self, filter_key, backup_folder):
        """
        Returns a list of backup filenames, sorted by time, based on the filter.
        """
        files_to_display = []
        if filter_key == "Show All Backups":
            for key in self._organized_backups:
                files_to_display.extend(self._organized_backups[key])
        elif filter_key in self._organized_backups:
            files_to_display = self._organized_backups[filter_key]
        
        if not files_to_display or not os.path.isdir(backup_folder):
            return []

        # Sort the final list by modification time (most recent first)
        try:
            files_to_display.sort(
                key=lambda f: os.path.getmtime(os.path.join(backup_folder, f)),
                reverse=True
            )
            return files_to_display
        except FileNotFoundError:
            # This can happen if a file is deleted externally. The model will be
            # corrected on the next full rescan.
            print("A backup file was not found during sorting.")
            return []