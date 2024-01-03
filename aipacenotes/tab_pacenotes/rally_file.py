import copy
import json
import logging
import os
import pathlib
import re

import aipacenotes.util

class Pacenote:
    def __init__(self, notebook, data):
        self.notebook = notebook
        self.data = data

    def __str__(self):
        return f'{self.short_name()} | {self.note_abs_path()}'

    def short_name(self):
        exist = 'F'
        if  self.note_file_exists():
            exist = 'T'
        return f'[exist={exist}] {self.clean_codriver_name()} | {self.name()}: {self.note()}'

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

    def clean_codriver_name(self):
        return aipacenotes.util.clean_name_for_path(
            self.codriver_name() + '_'+self.language() + '_' + self.voice()
        )

    def pacenotes_dir(self):
        the_dir = aipacenotes.util.normalize_path(
            os.path.join(
                self.notebook.pacenotes_dir(),
                self.clean_codriver_name()
            )
        )
        return the_dir

    def note_file_exists(self):
        return os.path.isfile(self.note_abs_path())

    def needs_update(self):
        file_doesnt_exist = not self.note_file_exists()
        unknown = self.note() == aipacenotes.util.UNKNOWN_PLACEHOLDER
        empty = self.note().strip() == ""
        rv = file_doesnt_exist and not unknown and not empty
        if rv:
            logging.info(f"Pacenote.needs_update() {self.short_name()} | file_doesnt_exist={file_doesnt_exist} unknown={unknown} empty={empty} rv={rv}")
        return rv

    def ensure_pacenotes_dir(self):
        self.notebook.ensure_pacenotes_dir()
        pathlib.Path(self.pacenotes_dir()).mkdir(parents=True, exist_ok=True)

    def write_file(self, data):
        self.ensure_pacenotes_dir()
        with open(self.note_abs_path(), 'wb') as f:
            f.write(data)

    def delete_audio_file(self):
        file_path = self.note_abs_path()
        try:
            os.remove(file_path)
            logging.info(f"deleted: {file_path}")
        except OSError as e:
            logging.error(f"error: {file_path} : {e.strerror}")

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
        return aipacenotes.util.clean_name_for_path(self.name())

    def pacenotes(self, use_cache=True):
        if not use_cache:
            self._pacenotes = None

        if self._pacenotes:
            return self._pacenotes

        codrivers = self.data['codrivers']
        pacenotes = []

        def concat_note_data(note_data):
            before = note_data.get('before', '')
            note   = note_data.get('note', '')
            after  = note_data.get('after', '')
            return ' '.join([before, note, after]).strip()

        for codriver_data in codrivers:
            for pacenote_data in self.data['pacenotes']:
                # for each note language, make a copy of the whole note data.
                for lang,note_data in pacenote_data['notes'].items():
                    if codriver_data['language'] == lang:
                        pn_data_copy = copy.deepcopy(pacenote_data)
                        pn_data_copy['note'] = concat_note_data(note_data)
                        pn_data_copy['language'] = lang
                        pn_data_copy['codriver'] = codriver_data # copy.deepcopy(codriver_data)
                        pacenote = Pacenote(self, pn_data_copy)
                        pacenotes.append(pacenote)

        self._pacenotes = pacenotes

        return self._pacenotes

    def pacenotes_dir(self):
        return aipacenotes.util.normalize_path(os.path.join(self.notebook_file.pacenotes_dir(), self.clean_name()))

    def ensure_pacenotes_dir(self):
        self.notebook_file.ensure_pacenotes_dir()
        pathlib.Path(self.pacenotes_dir()).mkdir(parents=False, exist_ok=True)

class NotebookFile:

    def __init__(self, fname):
        self.fname = aipacenotes.util.normalize_path(fname)
        self.ensure_pacenotes_dir()
        self._mission_voices = None

    def __str__(self):
        return aipacenotes.util.normalize_path(self.fname)

    def dirname(self):
        return aipacenotes.util.normalize_path(os.path.dirname(self.fname))

    def pacenotes_dir(self):
        return aipacenotes.util.normalize_path(os.path.join(self.dirname(), 'generated_pacenotes'))

    def aipacenotes_dir(self):
        return aipacenotes.util.normalize_path(os.path.join(self.dirname(), '..'))

    def load_mission_voices(self):
        voices_fname = os.path.join(self.dirname(), '..', 'mission.voices.json')
        self._mission_voices = {}

        if os.path.isfile(voices_fname):
            with open(voices_fname, 'r') as f:
                voices_data = json.load(f)
                for k,v in voices_data.items():
                    self._mission_voices[k] = v

    def mission_voice_config(self, voice):
        if not self._mission_voices:
            self.load_mission_voices()
        return self._mission_voices.get(voice, None)

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
