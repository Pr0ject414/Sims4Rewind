import sys
import os
import pytest

# Add project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from startup_manager import StartupManager

# Mock the entire win32com.client module for non-Windows environments or to avoid side-effects
@pytest.fixture
def mock_win32_client(mocker):
    """A fixture that properly mocks the win32com.client Dispatch method."""
    mock_shell = mocker.MagicMock()
    mock_shortcut = mocker.MagicMock()
    mock_shell.CreateShortcut.return_value = mock_shortcut
    
    # Mock the Dispatch method which is what's called in the StartupManager
    mock_dispatch = mocker.patch('win32com.client.Dispatch', return_value=mock_shell)
    
    return mock_dispatch, {"shell": mock_shell, "shortcut": mock_shortcut}

@pytest.fixture
def manager(mocker, mock_win32_client):
    """A fixture that provides a StartupManager instance with a mocked shortcut path."""
    # Mock os.path.exists to control whether the test thinks the shortcut exists
    mocker.patch('os.path.exists', return_value=False)
    mocker.patch('os.path.isdir', return_value=True)
    mocker.patch('os.remove')
    
    mocker.patch('startup_manager.get_startup_folder', return_value='C:/fake/startup/folder')
    
    startup_manager = StartupManager()
    
    # The mock_win32_client fixture returns the mocked objects
    _, mocks = mock_win32_client
    
    return startup_manager, mocks

def test_is_enabled_false_when_shortcut_doesnt_exist(manager, mocker):
    """Tests that is_enabled() returns False when the shortcut file is not found."""
    startup_manager, _ = manager
    mocker.patch('os.path.exists', return_value=False)
    assert startup_manager.is_enabled() is False

def test_is_enabled_true_when_shortcut_exists(manager, mocker):
    """Tests that is_enabled() returns True when the shortcut file is found."""
    startup_manager, _ = manager
    mocker.patch('os.path.isdir', return_value=True)
    mocker.patch('os.path.exists', return_value=True)
    assert startup_manager.is_enabled() is True

def test_set_startup_creates_shortcut_when_enabled(manager, mocker):
    """Tests that set_startup(True) creates a shortcut."""
    startup_manager, mocks = manager
    
    mocker.patch('os.path.exists', return_value=False)
    
    # Act
    startup_manager.set_startup(True)

    # Assert that the shortcut creation logic was called
    mocks["shell"].CreateShortcut.assert_called_once()
    mocks["shortcut"].save.assert_called_once()
    assert mocks["shortcut"].TargetPath == sys.executable
    assert "--startup" in mocks["shortcut"].Arguments

def test_set_startup_removes_shortcut_when_disabled(manager, mocker):
    """Tests that set_startup(False) removes an existing shortcut."""
    startup_manager, _ = manager
    mock_os_remove = mocker.patch('os.remove')
    
    mocker.patch('os.path.isdir', return_value=True)
    mocker.patch('os.path.exists', return_value=True)
    
    # Act
    startup_manager.set_startup(False)

    # Assert that os.remove was called with the correct path
    mock_os_remove.assert_called_once_with(startup_manager.shortcut_path)

def test_set_startup_does_nothing_if_already_enabled(manager, mocker, mock_win32_client):
    """Tests that no action is taken if trying to enable an already-enabled shortcut."""
    startup_manager, mocks = manager
    mock_dispatch, _ = mock_win32_client
    
    mocker.patch('os.path.isdir', return_value=True)
    mocker.patch('os.path.exists', return_value=True)
    
    # Act
    startup_manager.set_startup(True)

    # Assert
    mock_dispatch.assert_not_called()
    
def test_set_startup_does_nothing_if_already_disabled(manager, mocker):
    """Tests that no action is taken if trying to disable an already-disabled shortcut."""
    startup_manager, mocks = manager
    mock_os_remove = mocker.patch('os.remove')
    
    mocker.patch('os.path.exists', return_value=False)
    
    # Act
    startup_manager.set_startup(False)

    # Assert: os.remove should not have been called
    mock_os_remove.assert_not_called()