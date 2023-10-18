import json
import copy
import os
import win32com.client
import re

from . import defaults

def deep_merge(dict1, dict2):
    result = dict1.copy()  # Start with dict1's keys and values
    for key, value in dict2.items():  # Add dict2's keys and values
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def home_dir():
    hom = os.environ.get('HOME', os.environ.get('USERPROFILE'))
    hom = hom.replace('\\', '/')
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

    def __init__(self):
        self.settings = self.expand_default_settings()
        self.voices = None

    def replace_vars(self, vars, input_string):
        output_string = input_string
        matches = re.findall(self.var_regex, input_string)

        for match in matches:
            var_name = match[1:]
            if var_name in vars:
                replacement = vars[var_name]
                output_string = output_string.replace(match, replacement)

        return output_string

    def detect_voices_fname(self):
        voices_fname_user = self.settings['voices_path_user']

        if os.path.isfile(voices_fname_user):
            return voices_fname_user
        else:
            voices_fname_mod = self.settings['voices_path_mod']
            return voices_fname_mod
    
    def get_pacenotes_search_paths(self):
        return self.settings['pacenotes_search_paths']
    
    def get_transcription_txt_fname(self):
        return os.path.join(self.get_settings_dir(), self.settings['transcription_txt'])
    
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
        return fname
    
    def expand_default_settings(self):
        settings = copy.deepcopy(defaults.default_settings)
        settings['HOME'] = home_dir()

        for key, val in settings.items():
            # print(f"{key}={settings[key]}")
            if type(val) == str:
                settings[key] = self.expand_path(settings, val)
            elif type(val) == list:
                settings[key] = [self.expand_path(settings, v) for v in val]
            # print(f"{key}={settings[key]}")

        return settings

    def load(self):
        print(f"loading settings")
        user_settings = self.get_settings_path_user()

        if os.path.isfile(user_settings):
            print(f"merging in settings file at {user_settings}")
            with open(user_settings, 'r') as file:
                data = json.load(file)
            self.settings = deep_merge(self.settings, data)
        
        print(f"settings={self.settings}")

        self.load_voices()

    def load_voices(self):
        fname = self.detect_voices_fname()
        if os.path.isfile(fname):
            with open(fname, 'r') as file:
                self.voices = json.load(file)
        else:
            print(f"no voice file detected at {fname}")
                
        print(f"voices={self.voices}")
