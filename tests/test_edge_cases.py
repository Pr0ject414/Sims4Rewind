"""
Tests for edge cases and error handling scenarios.
"""

import sys
import os
import pytest
import shutil
import time
from unittest.mock import MagicMock, patch

# Add project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.main_window import Sims4RewindApp
from services import BackupService
from backup_handler import BackupHandler

@pytest.fixture
def app(qtbot, mocker):
    """A fixture that creates the main application window with mocked dependencies."""
    mock_config = MagicMock()
    mock_service = MagicMock()
    mock_view_model = MagicMock()
    mock_startup = MagicMock()

    # Configure the mock config manager to return a dictionary with default values
    mock_settings = {
        "saves_folder": "D:/dummy/saves",
        "backup_folder": "D:/dummy/backups",
        "backup_count": 5,
        "auto_monitor_on_startup": False,
        "compress_backups": False
    }
    mock_config.load_settings.return_value = mock_settings
    mock_startup.is_enabled.return_value = False

    # Patch the dialogs module to prevent real dialogs from opening during tests.
    mocker.patch('ui.main_window.dialogs')

    test_app = Sims4RewindApp(
        config_manager=mock_config,
        backup_service=mock_service,
        backup_view_model=mock_view_model,
        startup_manager=mock_startup
    )
    qtbot.addWidget(test_app)
    return test_app, mock_config, mock_service, mock_view_model, mock_startup


@patch('ui.main_window.dialogs') # Mock the dialogs module in the main_window's scope
def test_restore_io_error_handling(mock_dialogs, app):
    """Tests that an IOError during restore is handled gracefully by showing a dialog."""
    main_app, _, _, _, _ = app
    
    # Configure the UI state for the test
    main_app.ui.saves_folder_path.setText("D:/dummy/saves")
    main_app.ui.backup_folder_path.setText("D:/dummy/backups")
    main_app.ui.backup_list_widget.addItem("Slot_00000001.save_2023-01-01_12-00-00.bak")
    main_app.ui.backup_list_widget.setCurrentRow(0)

    # Mock the confirmation dialog to return 'Yes'
    mock_dialogs.ask_question.return_value = True

    # Patch the BackupService.restore_backup_file to raise an error when called
    with patch.object(main_app.service, 'restore_backup_file', side_effect=IOError("Disk full")):
        # Act: Trigger the restore operation
        main_app._restore_backup()
    
    # Assert: Check that the critical error dialog was shown with the correct message
    mock_dialogs.show_critical.assert_called_once()
    # Check that the error message passed to the dialog contains "Disk full"
    assert "Disk full" in mock_dialogs.show_critical.call_args[0][2]

def test_prune_file_not_found_error(tmp_path, mocker):
    """Tests that the pruning logic handles a file being deleted externally."""
    saves_dir = tmp_path / "Saves"
    saves_dir.mkdir()
    backup_dir = tmp_path / "Backups"
    backup_dir.mkdir()
    save_file_path = saves_dir / "Slot_00000001.save"
    save_file_path.touch()

    # Use a real BackupHandler for this logic test
    handler = BackupHandler(str(saves_dir), str(backup_dir), 1, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), False, MagicMock())

    # Create two backups
    save_file_path.write_text("v1")
    handler.check_and_create_backup(str(save_file_path))
    time.sleep(0.1) # Ensure timestamp is different

    # Manually delete the backup that was just created
    backup_files = os.listdir(backup_dir)
    os.remove(os.path.join(backup_dir, backup_files[0]))

    # Act: Trigger pruning by creating another backup
    save_file_path.write_text("v2") # Modify the file
    time.sleep(0.1) # Ensure timestamp is different
    handler.check_and_create_backup(str(save_file_path))
    
    # Assert: The application should not crash, and the logic should complete.
    # The number of files should now be 1 (the newest backup).
    assert len(os.listdir(backup_dir)) == 1