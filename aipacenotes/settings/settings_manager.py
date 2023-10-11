import json
import os
import win32com.client

from . import defaults

def expand_windows_symlinks(path):
    # print(f"transform_path for {path}")
    shell = win32com.client.Dispatch("WScript.Shell")
    parts = []
    while True:
        new_part = None

        if os.path.exists(path + '.lnk'):
            lnk_path = path + '.lnk'
            shortcut = shell.CreateShortCut(lnk_path)
            new_part = shortcut.Targetpath

        # print(f"path={path}")
        path, part = os.path.split(path)
        # print(f"{path} {part} -> {new_part}")

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

def home_dir():
    hom = os.environ.get('HOME', os.environ.get('USERPROFILE'))
    hom = hom.replace('\\', '/')
    return hom

def replace_vars(input_string, input_dict):
    for key, func in input_dict.items():
        if "$" + key in input_string:
            input_string = input_string.replace("$" + key, func())
    return input_string

def deep_merge(dict1, dict2):
    result = dict1.copy()  # Start with dict1's keys and values
    for key, value in dict2.items():  # Add dict2's keys and values
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result

replacement_strings = {
    'HOME': home_dir,
}

class SettingsManager():
    default_settings_path = '$HOME/AppData/Local/AIPacenotes/settings.json'
    default_voices_path_user = '$HOME/AppData/Local/BeamNG.drive/latest/settings/aipacenotes/voices.json'
    default_voices_path_mod = '$HOME/AppData/Local/BeamNG.drive/latest/mods/unpacked/beamng-aipacenotes-mod/settings/aipacenotes/voices.json'

    def __init__(self, settings_fname=default_settings_path):
        settings_fname = replace_vars(settings_fname, replacement_strings)
        self.settings_fname = settings_fname
        self.settings = None

        # self.voices_fname = self.detect_voices_fname()
        self.voices = None
    
    def detect_voices_fname(self):
        voices_fname_user = replace_vars(self.default_voices_path_user, replacement_strings)
        voices_fname_user = expand_windows_symlinks(voices_fname_user)

        if os.path.isfile(voices_fname_user):
            return voices_fname_user
        else:
            voices_fname_mod = replace_vars(self.default_voices_path_mod, replacement_strings)
            voices_fname_mod = expand_windows_symlinks(voices_fname_mod)
            return voices_fname_mod
    
    def get_search_paths(self):
        return self.settings['pacenotes_search_paths']

    def load(self):
        print(f"loading settings")

        self.settings = defaults.default_settings

        if os.path.isfile(self.settings_fname):
            print(f"merging in settings file at {self.settings_fname}")
            with open(self.settings_fname, 'r') as file:
                data = json.load(file)

            self.settings = deep_merge(self.settings, data)
        
        search_paths = self.settings['pacenotes_search_paths'] 

        new_sp = []
        for sp in search_paths:
             updated = replace_vars(sp, replacement_strings)
             updated = expand_windows_symlinks(updated)
             new_sp.append(updated)

        self.settings['pacenotes_search_paths'] = new_sp
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
