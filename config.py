# =====================================================================
# FILE: config.py
# =====================================================================
# This file defines the ConfigManager class, which is responsible
# for all interactions with the config.json file.

import json
import os
from PyQt6.QtWidgets import QMessageBox

class ConfigManager:
    """Handles loading and saving of application settings from a JSON file."""
    def __init__(self, config_file="config.json"):
        """Initializes the ConfigManager with a path to the config file."""
        self.config_file = config_file
        self._default_settings = {
            "saves_folder": "",
            "backup_folder": "",
            "backup_count": 10,
            "auto_monitor_on_startup": True,
        }

    def load_settings(self):
        """
        Loads settings from the JSON file.
        Returns a dictionary of settings, falling back to defaults if not found/error.
        """
        settings = self._default_settings.copy()
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge loaded settings with defaults to ensure all keys exist
                    settings.update(loaded_settings)
                print("Settings loaded successfully.")
                return settings
            except (json.JSONDecodeError, IOError) as e:
                QMessageBox.warning(None, "Config Error", f"Could not load settings file: {e}. It may be corrupt.")
                return settings # Return defaults on error
        else:
            print("No config file found. Using default settings.")
            return settings # Return defaults if no file

    def save_settings(self, settings):
        """
        Saves the provided settings dictionary to the JSON file.
        """
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
        except IOError as e:
            QMessageBox.critical(None, "Config Error", f"Could not save settings to file: {e}.")