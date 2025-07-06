# =====================================================================
# FILE: utils.py
# =====================================================================
# This file contains shared utility functions used across the application
# to promote code reuse and adhere to the DRY principle.

def get_original_from_backup(backup_filename: str) -> str | None:
    """
    Parses a backup filename to get the original .save filename.
    e.g., "Slot_00000002.save_2023-10-27_10-30-00.bak" -> "Slot_00000002.save"

    Args:
        backup_filename: The full filename of the backup file.

    Returns:
        The original save filename, or None if parsing fails.
    """
    try:
        # Find the last occurrence of .save_ and take everything before it
        base_name, _ = backup_filename.rsplit('.save_', 1)
        return base_name + '.save'
    except (ValueError, AttributeError):
        # ValueError if .rsplit fails, AttributeError if input isn't a string
        print(f"Could not parse backup name: {backup_filename}")
        return None