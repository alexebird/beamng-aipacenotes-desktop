import json
import copy
import pathlib
import os
import re

import aipacenotes.util

class Pacenote:
    def __init__(self, notebook, data):
        self.notebook = notebook
        self.data = data

    def __str__(self):
        exist = 'F'
        if  self.note_file_exists():
            exist = 'T'
        return f'[{exist}] {self.name()}: {self.note()} | {self.note_abs_path()}'
    
    def name(self):
        return self.data['name']
    
    def language(self):
        return self.data['language']
    
    def oldId(self):
        return self.data['oldId']
    
    def note(self):
        return self.data['note']
    
    def codriver(self):
        return self.data['codriver']
    
    def voice(self):
        return self.codriver()['voice']
    
    def codriver_name(self):
        return self.codriver()['name']

    def note_hash(self):
        hash_value = 0
        for char in self.note():
            hash_value = (hash_value * 33 + ord(char)) % 2_147_483_647
        return hash_value
    
    def note_basename(self):
        return f'pacenote_{self.note_hash()}.ogg'
    
    def note_abs_path(self):
        return aipacenotes.util.normalize_path(os.path.join(self.pacenotes_dir(), self.note_basename()))

    def pacenotes_dir(self):
        self.notebook.ensure_pacenotes_dir()
        the_dir = aipacenotes.util.normalize_path(os.path.join(self.notebook.pacenotes_dir(), self.language(), self.codriver_name()))
        pathlib.Path(the_dir).mkdir(parents=True, exist_ok=True)
        return the_dir
    
    def note_file_exists(self):
        return os.path.isfile(self.note_abs_path())

    def needs_update(self):
        return not self.note_file_exists()

    def write_file(self, data):
        self.notebook.ensure_pacenotes_dir()
        with open(self.note_abs_path(), 'wb') as f:
            f.write(data)

class Notebook:
    def __init__(self, notebook_file, data):
        self.notebook_file = notebook_file
        self.data = data
        self._pacenotes = None

    def __str__(self):
        return self.name()

    def __len__(self):
        return len(self.pacenotes())
    
    def name(self):
        return self.data['name']

    def clean_name(self):
        s = self.name()
        s = re.sub(r'[^a-zA-Z0-9]', '_', s)  # Replace everything but letters and numbers with '_'
        s = re.sub(r'_+', '_', s)            # Replace multiple consecutive '_' with a single '_'
        return s
    
    def pacenotes(self, use_cache=True):
        if not use_cache:
            self._pacenotes = None

        if self._pacenotes:
            return self._pacenotes
        
        codrivers = self.data['codrivers']
        pacenotes = []

        for codriver_data in codrivers:
            for pacenote_data in self.data['pacenotes']:
                # for each note language, make a copy of the whole note data.
                for lang,note in pacenote_data['notes'].items():
                    if codriver_data['language'] == lang:
                        pn_data_copy = copy.deepcopy(pacenote_data)
                        pn_data_copy['note'] = note
                        pn_data_copy['language'] = lang
                        pn_data_copy['codriver'] = codriver_data # copy.deepcopy(codriver_data)
                        pacenote = Pacenote(self, pn_data_copy)
                        pacenotes.append(pacenote)
        
        self._pacenotes = pacenotes

        return self._pacenotes

        # return [Pacenote(self, e) for e in self.data['pacenotes']]
    
    def pacenotes_dir(self):
        return aipacenotes.util.normalize_path(os.path.join(self.notebook_file.pacenotes_dir(), self.clean_name()))
    
    def ensure_pacenotes_dir(self):
        pathlib.Path(self.pacenotes_dir()).mkdir(parents=False, exist_ok=True)

    def file_explorer_path(self):
        return self.pacenotes_dir()

class NotebookFile:
    # pacenotes_root_name = 'aipacenotes/notebooks'

    def __init__(self, fname):
        self.fname = aipacenotes.util.normalize_path(fname)
        self.ensure_pacenotes_dir()

    def __str__(self):
        # return aipacenotes.util.normalize_path(os.path.join(self.mission_id(), self.basename()))
        return aipacenotes.util.normalize_path(self.fname)
    
    def dirname(self):
        return aipacenotes.util.normalize_path(os.path.dirname(self.fname))

    def pacenotes_dir(self):
        return aipacenotes.util.normalize_path(os.path.join(os.path.dirname(self.fname), 'generated_pacenotes'))
    
    def ensure_pacenotes_dir(self):
        pathlib.Path(self.pacenotes_dir()).mkdir(parents=False, exist_ok=True)
    
    def basename(self):
        return os.path.basename(self.fname)

    def file_explorer_path(self):
        return self.dirname()
    
    def load(self):
        with open(self.fname) as f:
            self.data = json.load(f)
    
    def notebook(self):
        return Notebook(self, self.data)

    def mission_id(self):
        pattern = r"missions/([^/]+/[^/]+/[^/]+)"
        match = re.search(pattern, self.fname)

        if match:
            return aipacenotes.util.normalize_path(match.group(1))
        else:
            raise ValueError(f"couldnt extract mission id from: {self.fname}")