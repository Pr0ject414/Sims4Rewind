# =====================================================================
# FILE: backup_handler.py
# =====================================================================
# This file contains the core backup logic. It now performs an
# initial backup of any save files that are missing one upon startup.

import os
import shutil
import time
import hashlib
from datetime import datetime
from PyQt6.QtCore import QObject
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from utils import get_original_from_backup

class BackupEventHandler(FileSystemEventHandler):
    """Handles file system events from watchdog with debouncing."""
    def __init__(self, backup_handler_instance):
        super().__init__()
        self.backup_handler = backup_handler_instance
        self.last_processed = {}
        self.debounce_interval = 3  # seconds to wait for more changes before processing

    def on_modified(self, event):
        """Called by watchdog when a file or directory is modified."""
        if event.is_directory or not event.src_path.endswith('.save'):
            return

        current_time = time.time()
        last_time = self.last_processed.get(event.src_path, 0)

        # Debounce to prevent processing multiple rapid-fire save events for the same file
        if current_time - last_time > self.debounce_interval:
            print(f"Modification detected (processing): {event.src_path}")
            self.last_processed[event.src_path] = current_time
            self.backup_handler.check_and_create_backup(event.src_path)

class BackupHandler(QObject):
    """
    Manages the backup process in a separate thread.
    Communicates with the main UI thread via Qt signals passed as callbacks.
    """
    def __init__(self, saves_folder, backup_folder, backup_count, status_callback, created_callback, pruned_callback):
        super().__init__()
        self.saves_folder = saves_folder
        self.backup_folder = backup_folder
        self.backup_count = backup_count
        self.observer = Observer()
        self._is_running = False
        self.last_backup_hashes = {}
        # Store the callback functions that will emit signals on the main thread
        self.status_callback = status_callback
        self.created_callback = created_callback
        self.pruned_callback = pruned_callback

    def run(self):
        """The main worker method. This runs on the dedicated backup thread."""
        self._is_running = True
        self._initialize_and_create_initial_backups() # CHANGED
        event_handler = BackupEventHandler(self)
        self.observer.schedule(event_handler, self.saves_folder, recursive=True)
        self.observer.start()
        self.status_callback(f"Monitoring '{self.saves_folder}'...")

        # The worker's event loop
        while self._is_running:
            time.sleep(1)

        self.observer.stop()
        self.observer.join()
        self.status_callback("Monitoring stopped.")

    def stop(self):
        """Signals the monitoring loop to terminate."""
        self._is_running = False

    def _calculate_hash(self, file_path, retries=3, delay=0.2):
        """
        Calculates the SHA-256 hash of a file. Includes a retry mechanism
        to handle potential file locks from the game writing the file.
        """
        sha256_hash = hashlib.sha256()
        last_exception = None
        for attempt in range(retries):
            try:
                with open(file_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                return sha256_hash.hexdigest()
            except (IOError, PermissionError) as e:
                last_exception = e
                time.sleep(delay)
        
        self.status_callback(f"Failed to read file {os.path.basename(file_path)} after {retries} attempts.")
        print(f"Could not calculate hash for {os.path.basename(file_path)} after {retries} attempts. Final error: {last_exception}")
        return None

    def _initialize_and_create_initial_backups(self): # RENAMED
        """
        Scans the backup folder on startup to get hashes of the latest backups,
        then scans the saves folder to create an initial backup for any file that
        does not have one yet.
        """
        if not os.path.isdir(self.backup_folder):
            os.makedirs(self.backup_folder, exist_ok=True) # Create backup folder if it doesn't exist

        self.status_callback("Initializing... scanning existing backups.")

        grouped_backups = {}
        for filename in os.listdir(self.backup_folder):
            if filename.endswith(".bak"):
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
        
        # --- NEW LOGIC START ---
        # Now, scan the saves folder to create initial backups for any files that don't have one.
        self.status_callback("Checking for any save files that need an initial backup...")
        if os.path.isdir(self.saves_folder):
            for filename in os.listdir(self.saves_folder):
                if filename.endswith('.save'):
                    # Check if we already processed a backup for this file during hash initialization
                    if filename not in self.last_backup_hashes:
                        print(f"File '{filename}' has no backup. Creating initial one.")
                        self.status_callback(f"Creating initial backup for {filename}...")
                        file_path = os.path.join(self.saves_folder, filename)
                        # This will handle the hashing, copying, and UI notification
                        self.check_and_create_backup(file_path)
        # --- NEW LOGIC END ---

        self.status_callback("Initialization and initial backup check complete.")

    def check_and_create_backup(self, file_path):
        """Checks file hash and creates a backup if content has changed."""
        try:
            original_filename = os.path.basename(file_path)
            current_hash = self._calculate_hash(file_path)

            if not current_hash:
                return # Error was already reported by _calculate_hash

            last_hash = self.last_backup_hashes.get(original_filename)

            if current_hash == last_hash:
                self.status_callback(f"Content of {original_filename} unchanged. Skipping.")
                return

            if not os.path.exists(self.backup_folder):
                os.makedirs(self.backup_folder)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_filename = f"{original_filename}_{timestamp}.bak"
            destination_path = os.path.join(self.backup_folder, backup_filename)

            shutil.copy2(file_path, destination_path)

            self.last_backup_hashes[original_filename] = current_hash
            self.status_callback(f"Created backup: {backup_filename}")

            # Notify the main thread that a new backup was created
            self.created_callback(backup_filename)

            # Clean up old backups for this specific save file
            self.prune_backups(original_filename)

        except Exception as e:
            self.status_callback(f"Error creating backup: {e}")

    def prune_backups(self, original_filename):
        """Deletes the oldest backups for a given save file if they exceed the configured limit."""
        try:
            # Get a list of all backup files related to the original save name
            backups_for_this_save = []
            for f in os.listdir(self.backup_folder):
                if get_original_from_backup(f) == original_filename:
                    backups_for_this_save.append(f)
            
            # Sort the backups by modification time, oldest first
            backups_for_this_save.sort(key=lambda f: os.path.getmtime(os.path.join(self.backup_folder, f)))

            if len(backups_for_this_save) > self.backup_count:
                num_to_delete = len(backups_for_this_save) - self.backup_count
                for i in range(num_to_delete):
                    filename_to_delete = backups_for_this_save[i]
                    path_to_delete = os.path.join(self.backup_folder, filename_to_delete)
                    os.remove(path_to_delete)
                    self.status_callback(f"Pruned old backup: {filename_to_delete}")
                    
                    # Notify the main thread that a backup was pruned
                    self.pruned_callback(filename_to_delete)

        except Exception as e:
            self.status_callback(f"Error pruning backups: {e}")