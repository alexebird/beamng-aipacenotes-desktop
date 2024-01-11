from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QSpacerItem, QSizePolicy)

import aipacenotes.settings

class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Settings")
        self.setLayout(QVBoxLayout())
        self.resize(500, 150)

        # GroupBox for settings
        self.settings_group = QGroupBox("AI Pacenotes API")
        self.settings_layout = QVBoxLayout(self.settings_group)

        # Horizontal layout for API key
        self.api_key_layout = QHBoxLayout()
        self.api_key_layout.addWidget(QLabel("API Key:"))
        self.api_key_input = QLineEdit()
        # self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        # self.api_key_input.setPlaceholderText("Enter API Key")
        self.api_key_layout.addWidget(self.api_key_input)
        self.settings_layout.addLayout(self.api_key_layout)

        self.layout().addWidget(self.settings_group)

        self.buttons_layout = QHBoxLayout()

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        self.buttons_layout.addWidget(save_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        self.buttons_layout.addWidget(cancel_button)

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.buttons_layout.addItem(spacer)

        self.layout().addLayout(self.buttons_layout)

        self.load_settings()

    def load_settings(self):
        self.api_key_input.setText(aipacenotes.settings.user_settings.get_api_key())

    def save_settings(self):
        aipacenotes.settings.user_settings.set_api_key(self.api_key_input.text())
        self.accept()
