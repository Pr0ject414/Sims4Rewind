import sys
import os
import time
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backup_handler import BackupHandler

@pytest.fixture
def temp_dirs(tmp_path):
    """A pytest fixture to create temporary save and backup directories for each test."""
    saves_dir = tmp_path / "Saves"
    saves_dir.mkdir()
    backup_dir = tmp_path / "Backups"
    backup_dir.mkdir()
    return saves_dir, backup_dir

def create_mock_save(path, content="save data"):
    """Helper function to create a dummy save file."""
    with open(path, "w") as f:
        f.write(content)

def test_initial_backup_creation(temp_dirs, mocker):
    """Tests if an initial backup is created for a pre-existing save file."""
    saves_dir, backup_dir = temp_dirs
    
    # Arrange: Create a save file *before* the handler starts
    save_file_path = saves_dir / "Slot_00000001.save"
    create_mock_save(save_file_path)

    # Mock the UI callbacks
    mock_status_cb = mocker.MagicMock()
    mock_created_cb = mocker.MagicMock()
    mock_pruned_cb = mocker.MagicMock()

    # Act: Initialize and run the initial scan part of the handler
    handler = BackupHandler(str(saves_dir), str(backup_dir), 5, mock_status_cb, mock_created_cb, mock_pruned_cb, mocker.MagicMock(), mocker.MagicMock(), False, mocker.MagicMock())
    handler._is_running = True # FIX: Simulate the running state for the test
    handler._initialize_and_create_initial_backups()

    # Assert: Check that a backup was created
    assert len(os.listdir(backup_dir)) == 1
    assert "Slot_00000001.save" in os.listdir(backup_dir)[0]
    mock_created_cb.assert_called_once() # The UI should be notified

def test_backup_on_modification(temp_dirs, mocker):
    """Tests if a new backup is created when a file is modified."""
    saves_dir, backup_dir = temp_dirs
    save_file_path = saves_dir / "Slot_00000001.save"
    create_mock_save(save_file_path, "version 1")

    # Arrange: Run the initial backup
    handler = BackupHandler(str(saves_dir), str(backup_dir), 5, mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock(), False, mocker.MagicMock())
    handler._is_running = True # FIX: Simulate the running state for the test
    handler._initialize_and_create_initial_backups()
    assert len(os.listdir(backup_dir)) == 1

    # Act: Modify the save file
    time.sleep(1.1) # Wait to ensure timestamp is different
    create_mock_save(save_file_path, "version 2")
    handler.check_and_create_backup(str(save_file_path))

    # Assert: A second, new backup should exist
    assert len(os.listdir(backup_dir)) == 2

def test_backup_skipped_for_unchanged_content(temp_dirs, mocker):
    """Tests that a backup is skipped if the content hash is the same."""
    saves_dir, backup_dir = temp_dirs
    save_file_path = saves_dir / "Slot_00000001.save"
    create_mock_save(save_file_path, "same content")

    mock_status_cb = mocker.MagicMock()
    
    # Arrange: Run the initial backup
    handler = BackupHandler(str(saves_dir), str(backup_dir), 5, mock_status_cb, mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock(), mocker.MagicMock(), False, mocker.MagicMock())
    handler._is_running = True # FIX: Simulate the running state for the test
    handler._initialize_and_create_initial_backups()
    assert len(os.listdir(backup_dir)) == 1

    # Act: "Touch" the file without changing its content
    time.sleep(1.1)
    create_mock_save(save_file_path, "same content")
    handler.check_and_create_backup(str(save_file_path))

    # Assert: No new backup should be created
    assert len(os.listdir(backup_dir)) == 1
    # Check if the status callback was called with the "Skipping" message
    assert any("Skipping" in call.args[0] for call in mock_status_cb.call_args_list)

def test_backup_pruning(temp_dirs, mocker):
    """Tests that old backups are pruned when the backup count is exceeded."""
    saves_dir, backup_dir = temp_dirs
    backup_count = 3
    save_file_path = saves_dir / "Slot_00000001.save"
    mock_pruned_cb = mocker.MagicMock()
    
    handler = BackupHandler(str(saves_dir), str(backup_dir), backup_count, mocker.MagicMock(), mocker.MagicMock(), mock_pruned_cb, mocker.MagicMock(), mocker.MagicMock(), False, mocker.MagicMock())

    # Act: Create more backups than the limit
    for i in range(backup_count + 2):
        create_mock_save(save_file_path, f"version {i}")
        handler.check_and_create_backup(str(save_file_path))
        time.sleep(1.1) # Wait to ensure timestamps are unique

    # Assert: The number of backups should be exactly the backup_count limit
    assert len(os.listdir(backup_dir)) == backup_count
    # The prune callback should have been called twice
    assert mock_pruned_cb.call_count == 2
