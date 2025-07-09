# =====================================================================
# FILE: test_system_tray.py (Corrected)
# =====================================================================
# This file contains the unit tests for the SystemTrayIcon class.

import sys
import os
import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from system_tray import SystemTrayIcon

@pytest.fixture(scope="module")
def qapp():
    """Ensures a QApplication instance exists for the test module."""
    return QApplication.instance() or QApplication(sys.argv)

@pytest.fixture
def mock_window():
    """Provides a MagicMock for the main window with necessary attributes."""
    window = MagicMock()
    # Mock the UI hierarchy needed for signal connection in the constructor
    window.ui.toggle_monitoring_button.click = MagicMock()
    window.app_quit = MagicMock()
    return window

def test_creation(qapp, mock_window):
    """Test that the tray icon and menu are created without errors."""
    tray = SystemTrayIcon(mock_window)
    assert tray.toolTip() == "Sims4Rewind"
    # 4 actions: Show, Monitor, Separator, Exit
    assert len(tray.contextMenu().actions()) == 4
    assert tray.contextMenu().actions()[0].text() == "Show/Hide Settings"

def test_monitoring_action_update(qapp, mock_window):
    """Test that the monitoring action in the menu updates correctly."""
    tray = SystemTrayIcon(mock_window)
    
    tray.update_monitoring_action(True)
    assert tray.monitoring_action.isChecked()
    assert tray.monitoring_action.text() == "Stop Monitoring"
    
    tray.update_monitoring_action(False)
    assert not tray.monitoring_action.isChecked()
    assert tray.monitoring_action.text() == "Start Monitoring"

def test_toggle_window(qapp, mock_window):
    """Test the toggle_window method shows/hides the window."""
    tray = SystemTrayIcon(mock_window)
    
    # Simulate window is hidden, then toggle
    mock_window.isVisible.return_value = False
    tray.toggle_window()
    mock_window.show.assert_called_once()
    mock_window.hide.assert_not_called()
    
    # Simulate window is visible, then toggle
    mock_window.isVisible.return_value = True
    tray.toggle_window()
    mock_window.hide.assert_called_once()

def test_show_notification(qapp, mock_window, mocker):
    """Test that show_notification calls the underlying QSystemTrayIcon.showMessage method."""
    tray = SystemTrayIcon(mock_window)
    mock_showMessage = mocker.patch.object(tray, 'showMessage')

    title = "Test Title"
    message = "Test Message"
    tray.show_notification(title, message)

    mock_showMessage.assert_called_once_with(title, message, tray.MessageIcon.Information, 10000)

    # Test with custom icon and msecs
    mock_showMessage.reset_mock()
    tray.show_notification("Error", "Something went wrong", icon=tray.MessageIcon.Critical, msecs=5000)
    mock_showMessage.assert_called_once_with("Error", "Something went wrong", tray.MessageIcon.Critical, 5000)