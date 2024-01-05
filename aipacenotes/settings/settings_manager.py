import json
import pprint
import logging
import copy
import os
import win32com.client
import re

from . import defaults
import aipacenotes.util


def deep_merge(dict1, dict2):
    result = dict1.copy()  # Start with dict1's keys and values
    for key, value in dict2.items():  # Add dict2's keys and values
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                # If both are dicts, recurse
                result[key] = deep_merge(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                # If both are lists, extend the list from dict1 with elements from the list in dict2
                result[key] = result[key] + value
            else:
                # If they are of different types or not both lists/dicts, replace the value in dict1 with that from dict2
                result[key] = value
        else:
            # If the key from dict2 doesn't exist in dict1, add it to result
            result[key] = value
    return result

def home_dir():
    hom = os.environ.get('HOME', os.environ.get('USERPROFILE'))
    hom = aipacenotes.util.normalize_path(hom)
    return hom

def expand_windows_symlinks(path):
    shell = win32com.client.Dispatch("WScript.Shell")
    parts = []
    while True:
        new_part = None

        if os.path.exists(path + '.lnk'):
            lnk_path = path + '.lnk'
            shortcut = shell.CreateShortCut(lnk_path)
            new_part = shortcut.Targetpath

        path, part = os.path.split(path)

        if new_part is not None:
            parts.append(new_part)
        else:
            parts.append(part)

        # Break loop when path can't be split any further
        if path == '' or path == '/' or (os.path.splitdrive(path)[1] in ('', '/', '\\')):
            break

    parts.append(path)
    parts.reverse()

    return os.path.join(*parts)

class SettingsManager():
    var_regex = r'\$[a-zA-Z0-9_]+'

    def __init__(self, status_bar):
        self.status_bar = status_bar
        self.settings = self.expand_default_settings()
        self.voices = None

    def update_status_left(self, txt):
        self.status_bar.updateLeftLabel.emit(txt)

    def update_status_right(self, txt):
        self.status_bar.updateRightLabel.emit(txt)

    def replace_vars(self, vars, input_string):
        output_string = input_string
        matches = re.findall(self.var_regex, input_string)

        for match in matches:
            var_name = match[1:]
            if var_name in vars:
                replacement = vars[var_name]
                output_string = output_string.replace(match, replacement)

        return output_string

    def get_recording_cut_delay(self):
        return self.settings['recording_cut_delay']

    def get_pacenotes_search_paths(self):
        return self.settings['pacenotes_search_paths']

    def get_transcript_fname(self):
        return os.path.join(self.get_settings_dir(), self.settings['transcript_fname'])

    def get_settings_dir(self):
        val = self.settings['settings_dir']
        os.makedirs(val, exist_ok=True)
        return  val

    def get_tempdir(self):
        val = self.settings['temp_dir']
        os.makedirs(val, exist_ok=True)
        return  val

    def get_settings_path_user(self):
        return self.settings['settings_path_user']

    def expand_path(self, vars, fname):
        fname = self.replace_vars(vars, fname)
        fname = expand_windows_symlinks(fname)
        fname = os.path.normpath(fname)
        fname = aipacenotes.util.normalize_path(fname)
        return fname

    def expand_default_settings(self):
        settings = copy.deepcopy(defaults.default_settings)
        settings['HOME'] = home_dir()

        # expand settings dict values
        for key, val in settings.items():
            if type(val) == str:
                settings[key] = self.expand_path(settings, val)
            elif type(val) == list:
                settings[key] = [self.expand_path(settings, v) for v in val]

        return settings

    def pretty_print(self, name, data):
        pretty_printer = pprint.PrettyPrinter()
        formatted_dict = pretty_printer.pformat(data)
        logging.debug(f"{name}:\n\n%s\n", formatted_dict)

    def load(self):
        logging.info(f"loading settings")
        user_settings = self.get_settings_path_user()

        if os.path.isfile(user_settings):
            logging.info(f"merging in user settings file at {user_settings}")
            with open(user_settings, 'r') as file:
                data = json.load(file)
            self.settings = deep_merge(self.settings, data)
            # self.pretty_print("settings from {user_settings}", data)
        else:
            logging.info("no user settings file found at %s", user_settings)

        self.pretty_print('settings', self.settings)

        self.load_voices()

    def load_voices(self):
        voices_files = self.settings['voice_files']
        logging.info(f"loading {len(voices_files)} voice files")
        self.voices = {}
        ext = '.zip'

        for e in voices_files:
            if ext in e:
                logging.debug(f"voice file ({ext}): {e}")
                count = 0
                zip_fname, inner_fname = self.split_path_after_ext(ext, e)
                if zip_fname and os.path.isfile(zip_fname):
                    data = aipacenotes.util.read_file_from_zip(zip_fname, inner_fname)
                    if data:
                        data = json.loads(data)
                        for k,v in data.items():
                            self.voices[k] = v
                            count += 1
                logging.debug(f"added {count} voices")
            else:
                logging.debug(f"voice file: {e}")
                count = 0
                if os.path.isfile(e):
                    with open(e, 'r') as file:
                        voices_data = json.load(file)
                        for k,v in voices_data.items():
                            self.voices[k] = v
                            count += 1
                logging.debug(f"added {count} voices")

        self.pretty_print('voices', self.voices)

    # assumes file_path does indeed contain ext.
    def split_path_after_ext(self, ext, file_path):
        if file_path.endswith(ext):
            logging.warn("file path with .zip must have additional path (the path inside the zip): %s", file_path)
            return (None, None)
        else:
            zip_fname, inner_fname = file_path.split(ext+'/')
            return (zip_fname+ext, inner_fname)

    def voice_config(self, voice):
        return self.voices.get(voice, None)
