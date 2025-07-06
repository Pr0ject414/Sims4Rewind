# =====================================================================
# FILE: backup_handler.py
# =====================================================================
# This file contains the core backup logic. It uses file hashing
# to prevent creating unnecessary backups of unchanged files.

import os
import shutil
import time
import hashlib
from datetime import datetime
from PyQt6.QtCore import QObject
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from utils import get_original_from_backup # <-- IMPORT THE NEW UTILITY

class BackupEventHandler(FileSystemEventHandler):
    """Handles file system events from watchdog with debouncing."""
    def __init__(self, backup_handler_instance):
        super().__init__()
        self.backup_handler = backup_handler_instance
        self.last_processed = {}
        self.debounce_interval = 3  # seconds

    def on_modified(self, event):
        """Called when a file or directory is modified."""
        if event.is_directory or not event.src_path.endswith('.save'):
            return

        current_time = time.time()
        last_time = self.last_processed.get(event.src_path, 0)

        if current_time - last_time > self.debounce_interval:
            print(f"Modification detected (processing): {event.src_path}")
            self.last_processed[event.src_path] = current_time
            self.backup_handler.check_and_create_backup(event.src_path)
        # else:
            # print(f"Modification detected (debounced): {event.src_path}")

class BackupHandler(QObject):
    """
    Manages the backup process using file hashing to ensure efficiency.
    Note: This class does not have signals as it is a pure worker.
    It will be controlled by the main thread which emits signals.
    """
    def __init__(self, saves_folder, backup_folder, backup_count, status_callback, created_callback):
        super().__init__()
        self.saves_folder = saves_folder
        self.backup_folder = backup_folder
        self.backup_count = backup_count
        self.observer = Observer()
        self._is_running = False
        self.last_backup_hashes = {}
        # Use callbacks to communicate with the main thread
        self.status_callback = status_callback
        self.created_callback = created_callback

    def run(self):
        """The main worker method that runs on the thread."""
        self._is_running = True
        self._initialize_hashes()
        event_handler = BackupEventHandler(self)
        self.observer.schedule(event_handler, self.saves_folder, recursive=True)
        self.observer.start()
        self.status_callback(f"Monitoring '{self.saves_folder}'...")

        while self._is_running:
            time.sleep(1)

        self.observer.stop()
        self.observer.join()
        self.status_callback("Monitoring stopped.")

    def stop(self):
        """Stops the monitoring loop."""
        self._is_running = False

    def _calculate_hash(self, file_path):
        """Calculates the SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except IOError:
            return None

    def _initialize_hashes(self):
        """Scans the backup folder to get hashes of the latest backups."""
        if not os.path.isdir(self.backup_folder):
            return

        self.status_callback("Initializing... scanning existing backups.")

        grouped_backups = {}
        for filename in os.listdir(self.backup_folder):
            if filename.endswith(".bak"):
                # --- CHANGE: USE THE UTILITY FUNCTION ---
                original_name = get_original_from_backup(filename)
                if original_name:
                    if original_name not in grouped_backups:
                        grouped_backups[original_name] = []
                    grouped_backups[original_name].append(filename)

        for original_name, backup_list in grouped_backups.items():
            backup_list.sort(key=lambda f: os.path.getmtime(os.path.join(self.backup_folder, f)), reverse=True)
            latest_backup_path = os.path.join(self.backup_folder, backup_list[0])
            latest_hash = self._calculate_hash(latest_backup_path)
            if latest_hash:
                self.last_backup_hashes[original_name] = latest_hash

        self.status_callback("Initialization complete.")

    def check_and_create_backup(self, file_path):
        """Checks file hash and creates a backup if content has changed."""
        try:
            original_filename = os.path.basename(file_path)
            current_hash = self._calculate_hash(file_path)

            if not current_hash:
                self.status_callback(f"Could not read/hash {original_filename}.")
                return

            last_hash = self.last_backup_hashes.get(original_filename)

            if current_hash == last_hash:
                log_message = f"Content of {original_filename} unchanged. Skipping backup."
                print(f"[LOG] {log_message}")
                self.status_callback(log_message)
                return

            if not os.path.exists(self.backup_folder):
                os.makedirs(self.backup_folder)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = f"{original_filename}_{timestamp}.bak"
            destination_path = os.path.join(self.backup_folder, backup_filename)

            shutil.copy2(file_path, destination_path)

            self.last_backup_hashes[original_filename] = current_hash
            self.status_callback(f"Created backup: {backup_filename}")

            self.prune_backups(original_filename)
            self.created_callback()

        except Exception as e:
            self.status_callback(f"Error creating backup: {e}")

    def prune_backups(self, original_filename):
        """Deletes the oldest backups if they exceed the configured limit."""
        try:
            backups = [
                f for f in os.listdir(self.backup_folder)
                if f.startswith(original_filename) and f.endswith('.bak')
            ]

            backups.sort(key=lambda f: os.path.getmtime(os.path.join(self.backup_folder, f)))

            if len(backups) > self.backup_count:
                num_to_delete = len(backups) - self.backup_count
                for i in range(num_to_delete):
                    file_to_delete = os.path.join(self.backup_folder, backups[i])
                    os.remove(file_to_delete)
                    self.status_callback(f"Pruned old backup: {backups[i]}")
        except Exception as e:
            self.status_callback(f"Error pruning backups: {e}")