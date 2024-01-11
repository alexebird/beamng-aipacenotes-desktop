import os
import logging
import json
import uuid

import aipacenotes.util

APP_NAME = 'AiPacenotesDesktop'

class UserSettingsManager:
    def __init__(self, app_name):
        self.app_name = app_name
        self.settings_file = self._get_settings_file_path()
        self.settings_data = self._load_settings()
        self.get_uuid() # generate the uuid

    def _get_settings_file_path(self):
        appdata_dir = os.getenv('APPDATA') if aipacenotes.util.is_windows() else os.path.expanduser("~/.config/")
        app_dir = os.path.join(appdata_dir, self.app_name)
        os.makedirs(app_dir, exist_ok=True)
        settings_path = os.path.join(app_dir, 'settings.json')
        logging.debug(f"user_settings path: {settings_path}")
        return settings_path

    def _load_settings(self):
        try:
            with open(self.settings_file, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'user_settings': {}, 'internal': {}}

    def save_settings(self):
        with open(self.settings_file, 'w') as file:
            json.dump(self.settings_data, file, indent=4)

    def get_uuid(self):
        uuid_str = self.settings_data.get('internal', {}).get('uuid')
        if not uuid_str:
            uuid_str = str(uuid.uuid4())
            self.settings_data.setdefault('internal', {})['uuid'] = uuid_str
            self.save_settings()
        return uuid_str

    def get_api_key(self):
        return self.settings_data.get('user_settings', {}).get('api_key', '')

    def set_api_key(self, api_key):
        self.settings_data.setdefault('user_settings', {})['api_key'] = api_key
        self.save_settings()


# create the singleton.
user_settings = UserSettingsManager(APP_NAME)
