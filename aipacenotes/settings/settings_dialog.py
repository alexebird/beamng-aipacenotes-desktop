from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QGroupBox, QSpacerItem, QSizePolicy)

import aipacenotes.settings
from aipacenotes.tab_network.proxy_request import ProxyRequest

class SettingsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("User Settings")
        self.setLayout(QVBoxLayout())
        self.resize(550, 150)

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

        self.test_label = QLabel("")
        self.test_label.setFixedWidth(25)
        self.api_key_layout.addWidget(self.test_label)

        self.test_button = QPushButton("Test")
        self.test_button.clicked.connect(self.test_api_key)
        self.api_key_layout.addWidget(self.test_button)

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

    def test_api_key(self):
        # Call the do_healthcheck method when Test button is clicked
        self.test_label.setText("...")
        req = ProxyRequest.do_healthcheck(self.api_key_input.text())
        if req.response_json and req.response_json.get('authed', False) == True:
            self.test_label.setText("Ok!")
        else:
            self.test_label.setText("Fail!")
        self.test_label.update()
