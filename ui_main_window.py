# =====================================================================
# FILE: ui_main_window.py
# =====================================================================
# This file is responsible ONLY for defining the user interface layout
# and widgets. It contains no application logic.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QListWidget, QSpinBox, QCheckBox, QGroupBox, QComboBox
)

class Ui_Sims4RewindApp(object):
    def setupUi(self, MainWindow):
        """
        Sets up the entire user interface for the main window.
        All widgets are created, styled, and arranged here.
        """
        MainWindow.setObjectName("Sims4Rewind")
        MainWindow.setWindowTitle("Sims4Rewind")
        MainWindow.setGeometry(100, 100, 700, 550)
        MainWindow.setMinimumSize(600, 500)

        self.central_widget = QWidget(MainWindow)
        MainWindow.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(15, 15, 15, 15)

        # --- Settings Group ---
        self.settings_group = QGroupBox("Configuration")
        settings_layout = QVBoxLayout()
        self.saves_folder_path = QLineEdit()
        self.browse_saves_button = QPushButton("Browse...")
        self.backup_folder_path = QLineEdit()
        self.browse_backups_button = QPushButton("Browse...")
        self.backup_count_spinbox = QSpinBox()
        self.startup_checkbox = QCheckBox("Start with Windows")
        self.auto_monitor_checkbox = QCheckBox("Auto-monitor on startup")

        saves_layout = QHBoxLayout()
        saves_layout.addWidget(QLabel("Sims 4 Saves Folder:"))
        saves_layout.addWidget(self.saves_folder_path)
        saves_layout.addWidget(self.browse_saves_button)
        settings_layout.addLayout(saves_layout)

        backup_layout = QHBoxLayout()
        backup_layout.addWidget(QLabel("Backup Location:"))
        backup_layout.addWidget(self.backup_folder_path)
        backup_layout.addWidget(self.browse_backups_button)
        settings_layout.addLayout(backup_layout)
        
        other_settings_layout = QHBoxLayout()
        other_settings_layout.addWidget(QLabel("Backups to keep per file:"))
        self.backup_count_spinbox.setRange(1, 100)
        other_settings_layout.addWidget(self.backup_count_spinbox)
        other_settings_layout.addStretch()
        other_settings_layout.addWidget(self.auto_monitor_checkbox)
        other_settings_layout.addWidget(self.startup_checkbox)
        settings_layout.addLayout(other_settings_layout)

        self.settings_group.setLayout(settings_layout)
        self.main_layout.addWidget(self.settings_group)

        # --- Status and Monitoring ---
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Status: Idle. Configure settings and start monitoring.")
        self.status_label.setStyleSheet("font-style: italic; color: #555;")
        self.toggle_monitoring_button = QPushButton("Start Monitoring")
        self.toggle_monitoring_button.setCheckable(True)
        self.toggle_monitoring_button.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; border-radius: 5px; padding: 5px;}
            QPushButton:checked { background-color: #f44336; }
        """)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.toggle_monitoring_button)
        self.main_layout.addLayout(status_layout)

        # --- Backup List and Restore ---
        self.backups_group = QGroupBox("Available Backups")
        backups_layout = QVBoxLayout()

        # --- CHANGE START: Add the filter dropdown ---
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Save File:"))
        self.backup_filter_dropdown = QComboBox()
        filter_layout.addWidget(self.backup_filter_dropdown)
        filter_layout.addStretch()
        backups_layout.addLayout(filter_layout)
        # --- CHANGE END ---

        self.backup_list_widget = QListWidget()
        
        # Restore Buttons Layout
        restore_buttons_layout = QHBoxLayout()
        self.restore_to_button = QPushButton("Restore to...")
        self.restore_to_button.setStyleSheet("background-color: #FFC107; color: black; border-radius: 5px; padding: 5px;") # Yellowish color
        restore_buttons_layout.addWidget(self.restore_to_button)

        self.restore_button = QPushButton("Restore Selected Backup")
        self.restore_button.setStyleSheet("background-color: #008CBA; color: white; border-radius: 5px; padding: 5px;")
        restore_buttons_layout.addWidget(self.restore_button)

        backups_layout.addWidget(self.backup_list_widget)
        backups_layout.addLayout(restore_buttons_layout)
        self.backups_group.setLayout(backups_layout)
        self.main_layout.addWidget(self.backups_group)