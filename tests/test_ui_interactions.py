"""
Tests for the UI interactions in the main window.
These tests use mock objects to isolate the UI from the backend services.
"""

import sys
import os
import pytest
from PyQt6.QtCore import pyqtSignal, QObject
from unittest.mock import MagicMock, patch

# Add project root to the path to allow imports from the 'ui' package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.main_window import Sims4RewindApp

@pytest.fixture
def app(qtbot, mocker):
    """
    A fixture that creates the main application window with all its dependencies mocked.
    This allows for isolated testing of the UI's behavior.
    """
    # Mock all the dependencies that will be injected into the main window
    mock_config = MagicMock()
    mock_service = MagicMock()
    mock_view_model = MagicMock()
    mock_startup = MagicMock()

    # Configure the mock config manager to return a dictionary with default values
    mock_settings = {
        "saves_folder": "D:/dummy/saves",
        "backup_folder": "D:/dummy/backups",
        "backup_count": 5,
        "auto_monitor_on_startup": False
    }
    mock_config.load_settings.return_value = mock_settings
    mock_startup.is_enabled.return_value = False

    # Patch the dialogs module to prevent real dialogs from opening during tests.
    mocker.patch('ui.main_window.dialogs')

    # Create the application instance with the mocked dependencies
    test_app = Sims4RewindApp(
        config_manager=mock_config,
        backup_service=mock_service,
        backup_view_model=mock_view_model,
        startup_manager=mock_startup
    )
    qtbot.addWidget(test_app)

    # Return the app and the mocks so tests can use them
    return test_app, mock_config, mock_service, mock_view_model, mock_startup

def test_restore_button_initially_disabled(app):
    """Tests that the Restore button is disabled when no backup is selected."""
    main_app, _, _, _, _ = app
    assert not main_app.ui.restore_button.isEnabled()

def test_restore_button_toggles_with_selection(app, qtbot):
    """Tests that the Restore button's state changes with list selection."""
    main_app, _, _, _, _ = app
    assert not main_app.ui.restore_button.isEnabled()

    # Simulate selecting an item in the list
    main_app.ui.backup_list_widget.addItem("backup_item_1")
    main_app.ui.backup_list_widget.setCurrentRow(0)
    
    assert main_app.ui.restore_button.isEnabled()

    # Simulate deselecting an item
    main_app.ui.backup_list_widget.setCurrentRow(-1)
    assert not main_app.ui.restore_button.isEnabled()

def test_monitoring_button_toggles_service(app):
    """Tests that the monitoring button calls the service methods."""
    main_app, _, mock_service, _, _ = app
    
    # Simulate turning monitoring ON
    main_app.ui.toggle_monitoring_button.setChecked(True)
    mock_service.start_monitoring.assert_called_once()

    # Simulate turning monitoring OFF
    main_app.ui.toggle_monitoring_button.setChecked(False)
    mock_service.stop_monitoring.assert_called_once()

def test_ui_updates_on_service_signal(app, qtbot):
    """Tests that the UI updates correctly when the service emits a signal."""
    main_app, _, mock_service, _, _ = app

    # Simulate the service starting monitoring on its own by directly calling the slot
    main_app._on_monitoring_status_changed(True)
    qtbot.wait(10) # Allow event loop to process UI updates
    assert "Stop Monitoring" in main_app.ui.toggle_monitoring_button.text()

    # Simulate the service stopping monitoring by directly calling the slot
    main_app._on_monitoring_status_changed(False)
    qtbot.wait(10) # Allow event loop to process UI updates
    assert "Start Monitoring" in main_app.ui.toggle_monitoring_button.text()
