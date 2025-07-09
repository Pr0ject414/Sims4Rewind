# Sims4Rewind: Future Improvements & Feature Suggestions

This document outlines potential new features and significant upgrades for the Sims4Rewind application. Each suggestion includes a description of the feature, its benefits to the user, and a brief technical overview of how it could be implemented.

---

## 1. Desktop Notifications for Key Events (Implemented)

**This is the most impactful and practical next feature to enhance the user experience.**

*   **Description:** The application now shows brief, non-intrusive desktop notifications for important events, allowing the user to have peace of mind that the application is working without needing to open the main window.
*   **Events Notified:**
    *   Backup successfully created.
    *   Monitoring started/stopped.
    *   Initial backup scan complete.
    *   Errors during file operations (e.g., failed to read file, backup error).
*   **Benefit:** Provides immediate, "set it and forget it" confidence. Users are instantly aware of successful backups and, more importantly, are alerted if the tool stops working for any reason.
*   **Implementation Details:** This feature was added by extending the `SystemTrayIcon` class, adding new notification signals to `BackupService` and `BackupHandler`, and connecting these signals to the system tray's notification method.

---

## 2. "Restore to..." Functionality

* **Description:** Add a "Restore to..." button next to the existing "Restore" button. This would open a file dialog prompting the user to choose a folder and a new name for the restored save file.
* **Benefit:** This provides a non-destructive way for users to inspect or test old backups. They can restore a save to their desktop, check it in-game, and decide if they want to overwrite their current live save, preventing accidental data loss.
* **Implementation Plan:**
    1.  Add a new `QPushButton` to `ui_main_window.py`.
    2.  Create a new method, `_restore_backup_to...`, in `main_window.py`.
    3.  This method would call `QFileDialog.getSaveFileName` to get the destination path from the user.
    4.  The core logic would be a simple `shutil.copy2` from the selected backup file to the user's chosen destination.

---

## 3. Backup Compression (.zip)

* **Description:** Add an option in the settings (e.g., a "Compress backups" checkbox) to save backups as `.zip` files instead of raw `.bak` files.
* **Benefit:** Significantly reduces the disk space used by the backup folder. Sims 4 save files are often highly compressible. This is a great feature for users with a large number of saves or limited storage.
* **Implementation Plan:**
    1.  Add a `compress_backups` boolean to the `config.json` file and a corresponding `QCheckBox` in `ui_main_window.py`.
    2.  In `backup_handler.py`, the `check_and_create_backup` method would be modified. If compression is enabled, it would use Python's built-in `zipfile` library to create a zip archive containing the single `.save` file.
    3.  The `_restore_backup` method in `main_window.py` would need to be updated to handle unzipping the file upon restore.
    4.  The `get_original_from_backup` utility function would also need to be updated to parse `.zip` filenames.

---

## 4. Detailed Log Tab

* **Description:** Add a new tab to the main window containing a scrollable, read-only text box. This log would display a timestamped history of all major actions performed by the application.
* **Actions to Log:**
    * Application start/exit.
    * Monitoring started/stopped.
    * Backup created/pruned.
    * File skipped (content unchanged).
    * Any errors encountered.
* **Benefit:** Creates a persistent audit trail that helps with troubleshooting and gives the user a complete history of the application's activity. It is more comprehensive than the ephemeral status bar.
* **Implementation Plan:**
    1.  Modify `ui_main_window.py` to use a `QTabWidget`.
    2.  Add a new "Log" tab containing a `QTextEdit` widget set to be read-only.
    3.  Create a new logging handler (or a simple signal) that appends messages to this `QTextEdit` widget. All status updates currently sent to the status bar would also be sent to this log.