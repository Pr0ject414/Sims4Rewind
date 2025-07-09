import sys
import os
import pytest

# Add the project root to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import get_original_from_backup

def test_get_original_from_standard_backup():
    """Tests a standard, correctly formatted backup filename."""
    backup_name = "Slot_00000002.save_2023-10-27_10-30-00.bak"
    expected = "Slot_00000002.save"
    assert get_original_from_backup(backup_name) == expected

def test_get_original_is_case_insensitive():
    """Tests that the function handles different casing."""
    backup_name = "slot_00000003.save_2024-01-01_12-00-00.bak"
    expected = "slot_00000003.save"
    assert get_original_from_backup(backup_name) == expected

def test_get_original_handles_extra_underscores_in_name():
    """Tests a filename that might have underscores in the original part."""
    backup_name = "My_Awesome_Save_File.save_2025-07-08_18-30-00.bak"
    expected = "My_Awesome_Save_File.save"
    assert get_original_from_backup(backup_name) == expected

def test_get_original_returns_none_for_invalid_format():
    """Tests that it returns None for a file that doesn't match the pattern."""
    backup_name = "NotAValidBackup.txt"
    assert get_original_from_backup(backup_name) is None

def test_get_original_returns_none_for_non_bak_file():
    """Tests that it returns None if the extension is not .bak."""
    backup_name = "Slot_00000002.save_2023-10-27_10-30-00.backup"
    assert get_original_from_backup(backup_name) is None

def test_get_original_handles_none_and_empty_string():
    """Tests edge cases like None or an empty string input."""
    assert get_original_from_backup(None) is None
    assert get_original_from_backup("") is None