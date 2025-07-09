"""
This module provides helper functions for creating and showing common UI dialogs,
like message boxes and file choosers. This keeps the main window code cleaner.
"""

from PyQt6.QtWidgets import QFileDialog, QMessageBox

def browse_for_directory(parent, caption):
    """Opens a dialog to select a directory and returns the path."""
    return QFileDialog.getExistingDirectory(parent, caption)

def show_info(parent, title, text):
    """Shows a standard information message box."""
    QMessageBox.information(parent, title, text)

def show_warning(parent, title, text):
    """Shows a standard warning message box."""
    QMessageBox.warning(parent, title, text)

def show_critical(parent, title, text):
    """Shows a standard critical error message box."""
    QMessageBox.critical(parent, title, text)

def ask_question(parent, title, text):
    """Asks a Yes/No question and returns True if Yes was clicked."""
    reply = QMessageBox.question(parent, title, text,
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.No)
    return reply == QMessageBox.StandardButton.Yes

def ask_minimize_or_exit(parent):
    """
    Shows the custom "Minimize or Exit?" dialog.
    Returns 'minimize', 'exit', or 'cancel'.
    """
    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle("Minimize or Exit?")
    msg_box.setText("What would you like to do?")
    msg_box.setIcon(QMessageBox.Icon.Question)

    minimize_button = msg_box.addButton("Minimize to Tray", QMessageBox.ButtonRole.ActionRole)
    exit_button = msg_box.addButton("Exit Application", QMessageBox.ButtonRole.DestructiveRole)
    cancel_button = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    
    msg_box.setDefaultButton(minimize_button)
    msg_box.exec()

    clicked = msg_box.clickedButton()

    if clicked == minimize_button:
        return "minimize"
    elif clicked == exit_button:
        return "exit"
    else:
        return "cancel"