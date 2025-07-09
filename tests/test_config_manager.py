import sys
import os
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import ConfigManager

# Mock the QMessageBox to prevent GUI popups during tests
@pytest.fixture(autouse=True)
def no_qmessagebox(mocker):
    mocker.patch("PyQt6.QtWidgets.QMessageBox.warning")
    mocker.patch("PyQt6.QtWidgets.QMessageBox.critical")

@pytest.fixture
def config_path(tmp_path):
    """A fixture that provides a path to a temporary config file."""
    return tmp_path / "config.json"

def test_load_settings_returns_defaults_when_no_file(config_path):
    """Tests that default settings are returned if the config file doesn't exist."""
    manager = ConfigManager(config_file=str(config_path))
    settings = manager.load_settings()
    
    assert settings["saves_folder"] == ""
    assert settings["backup_count"] == 10
    assert settings["auto_monitor_on_startup"] is True

def test_save_and_load_settings(config_path):
    """Tests that settings can be saved to and loaded from a file."""
    manager = ConfigManager(config_file=str(config_path))
    
    # Arrange: Define custom settings
    custom_settings = {
        "saves_folder": "C:/Saves",
        "backup_folder": "D:/Backups",
        "backup_count": 25,
        "auto_monitor_on_startup": False,
        "compress_backups": False
    }

    # Act: Save the settings
    manager.save_settings(custom_settings)

    # Assert: The file should exist and its content should be correct
    assert os.path.exists(config_path)
    
    # Act: Create a new manager to load the saved settings
    new_manager = ConfigManager(config_file=str(config_path))
    loaded_settings = new_manager.load_settings()

    # Assert: The loaded settings should match the custom settings
    assert loaded_settings == custom_settings

def test_load_merges_with_defaults(config_path):
    """Tests that a partial config file is correctly merged with default values."""
    # Arrange: Create a config file with only some keys
    partial_data = {
        "saves_folder": "MySaves",
        "backup_count": 5
    }
    with open(config_path, "w") as f:
        json.dump(partial_data, f)
    
    # Act: Load the settings
    manager = ConfigManager(config_file=str(config_path))
    settings = manager.load_settings()

    # Assert: Ensure existing values are loaded and missing ones are defaulted
    assert settings["saves_folder"] == "MySaves"
    assert settings["backup_count"] == 5
    assert settings["backup_folder"] == "" # This should come from the defaults
    assert settings["auto_monitor_on_startup"] is True # This should come from the defaults

def test_load_handles_corrupt_json(config_path):
    """Tests that default settings are returned if the JSON is invalid."""
    # Arrange: Create a corrupt config file
    with open(config_path, "w") as f:
        f.write("{'invalid_json': True,}") # Not valid JSON
        
    # Act: Load the settings
    manager = ConfigManager(config_file=str(config_path))
    settings = manager.load_settings()

    # Assert: The loaded settings should be the defaults
    assert settings == manager._default_settings