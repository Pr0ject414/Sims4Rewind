# =====================================================================
# FILE: startup_manager.py (Final Corrected Version)
# =====================================================================
# This file handles adding or removing the application from the
# user's startup folder.

import os
import sys
from PyQt6.QtWidgets import QMessageBox

# Note: We are no longer using the pyshortcuts library to create shortcuts
# as its API has proven to be unstable for this specific use case.
# Instead, we will use pywin32 directly for Windows, which is more reliable.

def get_startup_folder():
    """Manually determines the startup folder for the current OS."""
    if sys.platform == 'win32':
        return os.path.expandvars("%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup")
    # Add other OS paths here if needed in the future
    return None


class StartupManager:
    """Manages the application's shortcut in the OS-specific Startup folder."""
    def __init__(self, app_name="Sims4Rewind"):
        self.app_name = app_name
        self.startup_folder = get_startup_folder()
        
        if self.startup_folder and sys.platform == 'win32':
            self.shortcut_path = os.path.join(self.startup_folder, f"{self.app_name}.lnk")
        else:
            self.shortcut_path = None

    def is_enabled(self):
        """Checks if the startup shortcut currently exists."""
        if not self.shortcut_path:
            return False
            
        if not os.path.isdir(self.startup_folder):
            return False
            
        return os.path.exists(self.shortcut_path)

    def set_startup(self, enable):
        """
        Enables or disables running the application on startup.
        :param enable: True to add to startup, False to remove.
        """
        if not self.shortcut_path:
            print("Startup management is not supported on this OS.")
            return

        try:
            if enable:
                if not self.is_enabled():
                    # --- THIS IS THE NEW, DIRECT WINDOWS IMPLEMENTATION ---
                    if sys.platform == 'win32':
                        import win32com.client # Import here to keep it OS-specific
                        
                        shell = win32com.client.Dispatch("WScript.Shell")
                        shortcut = shell.CreateShortcut(self.shortcut_path)
                        
                        target_path = sys.executable
                        
                        shortcut.TargetPath = target_path
                        shortcut.Arguments = "--startup"
                        # The working directory should be where the .exe is
                        shortcut.WorkingDirectory = os.path.dirname(target_path)
                        # The .exe can serve as its own icon source
                        shortcut.IconLocation = target_path
                        shortcut.save()
                        
                        print(f"Created startup shortcut: {self.shortcut_path}")
                    else:
                        print("Startup shortcut creation is only implemented for Windows.")
            else:
                if self.is_enabled():
                    os.remove(self.shortcut_path)
                    print(f"Removed startup shortcut: {self.shortcut_path}")
        except Exception as e:
            error_message = f"Error modifying startup shortcut: {e}"
            print(error_message)
            QMessageBox.critical(None, "Startup Error", error_message)