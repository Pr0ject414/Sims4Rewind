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

## 2. "Restore to..." Functionality (Implemented)

*   **Description:** A "Restore to..." button has been added next to the existing "Restore" button. This opens a file dialog, allowing the user to choose a custom folder and name for the restored save file.
*   **Benefit:** Provides a non-destructive way for users to inspect or test old backups, preventing accidental data loss by allowing them to restore a save to a temporary location before overwriting their current live save.
*   **Implementation Details:** This feature involved adding a new `QPushButton` to `ui_main_window.py`, connecting it to a new `_restore_backup_to_location` method in `ui/main_window.py`, and utilizing `QFileDialog.getSaveFileName` and `shutil.copy2` for the file operation.

---

## 3. Backup Compression (.zip) (Implemented)

* **Description:** An option in the settings (e.g., a "Compress backups" checkbox) to save backups as `.zip` files instead of raw `.bak` files has been implemented.
* **Benefit:** Significantly reduces the disk space used by the backup folder. Sims 4 save files are often highly compressible. This is a great feature for users with a large number of saves or limited storage.
* **Implementation Details:** This feature involved adding a `compress_backups` boolean to the `config.json` file and a corresponding `QCheckBox` in `ui_main_window.py`. In `backup_handler.py`, the `check_and_create_backup` method was modified to use Python's built-in `zipfile` library to create a zip archive. The `_restore_backup` method in `main_window.py` was updated to handle unzipping the file upon restore, and the `get_original_from_backup` utility function was updated to parse `.zip` filenames.

---

## 4. Detailed Log Tab (Implemented)

*   **Description:** A new tab has been added to the main window containing a scrollable, read-only text box. This log displays a timestamped history of all major actions performed by the application.
*   **Actions Logged:**
    *   Application start/exit.
    *   Monitoring started/stopped.
    *   Backup created/pruned.
    *   File skipped (content unchanged).
    *   Any errors encountered.
*   **Benefit:** Creates a persistent audit trail that helps with troubleshooting and gives the user a complete history of the application's activity. It is more comprehensive than the ephemeral status bar.
*   **Implementation Details:** This feature involved modifying `ui_main_window.py` to use a `QTabWidget` and add a `QTextEdit` for the log. Messages are routed to this log via the `_update_status_label` method in `ui/main_window.py`, which now also emits a signal to append to the log. All `print()` statements in core logic were replaced with calls to status/notification callbacks.