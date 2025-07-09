# =====================================================================
# FILE: utils.py
# =====================================================================
# This file contains shared utility functions used across the application
# to promote code reuse and adhere to the DRY principle.

import re

def get_original_from_backup(backup_filename: str) -> str | None:
    """
    Parses a backup filename to get the original .save filename using a robust
    regular expression that is case-insensitive and handles the timestamp.
    e.g., "slot_00000002.save_2023-10-27_10-30-00.bak" -> "slot_00000002.save"
    e.g., "slot_00000002.save_2023-10-27_10-30-00.zip" -> "slot_00000002.save"

    Args:
        backup_filename: The full filename of the backup file.

    Returns:
        The original save filename, or None if parsing fails.
    """
    # Handle cases where the input is None or not a string
    if not isinstance(backup_filename, str):
        return None
    
    # This regular expression looks for the following pattern:
    #   (.+)       - Group 1: Captures the original filename (e.g., "Slot_00000002.save").
    #              - The `.+` is greedy but will stop at the underscore before the date.
    #   _          - A literal underscore separating the name from the timestamp.
    #   (\d{4}...) - A group matching the specific timestamp format (YYYY-MM-DD_HH-MM-SS).
    #   \.(bak|zip)$ - The literal string ".bak" or ".zip" at the end of the filename.
    #   re.IGNORECASE makes the match work for both "Slot" and "slot", etc.
    match = re.match(r'(.*?\.save)_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})\.(bak|zip)$', backup_filename, re.IGNORECASE)
    if match:
        return match.group(1)
    return None