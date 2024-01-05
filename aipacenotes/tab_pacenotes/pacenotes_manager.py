import os
import logging
import re
import json
import pathlib

from . import (
    Pacenote,
    Database,
)

class PacenotesManager():
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.pacenotes_network_cache = {}
        self.db = Database()

    def delete_stale_pacenotes(self, fname, scanned_pacenotes):
        pnids = set([pn.id for pn in scanned_pacenotes])

        existing_db_notes = self.db.select_with_fname(fname)

        i = 0
        while i < len(existing_db_notes):
            existing = existing_db_notes[i]

            if existing.id not in pnids:
                self.db.delete(existing.id)

            i += 1

    def reconcile_fs_scan(self, scanned_pacenotes):
        for scan_pacenote in scanned_pacenotes:
            pacenote = self.db.upsert(scan_pacenote)
            if pacenote is None:
                raise ValueError("couldnt find pacenote after upsert. this shouldnt happen")

            pacenote.refresh_filesystem_status()

    # db changes:
    # - delete pacenotes that dont exist in the scan, that arent pending network activity
    # - upsert all scanned pacenotes
    # - dont change network status
    def scan_pacenotes_files(self, pacenotes_files, rally_files):
        scan_data_pacenotes = []
        scan_data_rally = []

        def load_file(fname):
            with open(fname) as f:
                return (fname, json.load(f))

        for fname in pacenotes_files:
            rv = load_file(fname)
            scan_data_pacenotes.append(rv)

        for fname in rally_files:
            rv = load_file(fname)
            scan_data_rally.append(rv)

        scanned_objs_pacenotes = self.pacenotes_json_to_obj(scan_data_pacenotes)
        scanned_objs_rally = self.rally_json_to_obj(scan_data_rally)

        for fname in pacenotes_files:
            self.delete_stale_pacenotes(fname, scanned_objs_pacenotes)
        for fname in rally_files:
            self.delete_stale_pacenotes(fname, scanned_objs_rally)

        self.reconcile_fs_scan(scanned_objs_pacenotes)
        self.reconcile_fs_scan(scanned_objs_rally)

    def clean_up_orphaned_audio(self):
        # get the expected audio file names from the in-memory pacenotes list.
        pacenote_expected_audio_files = set()
        for pacenote in self.db.pacenotes:
            audio_path = pacenote.audio_path
            pacenote_expected_audio_files.add(audio_path)

        # in the search paths, get all the existing ogg files.
        for root_path in self.settings_manager.get_pacenotes_search_paths():
            ogg_search_path = pathlib.Path(root_path)
            paths = ogg_search_path.rglob('pacenotes/*/pacenote_*.ogg')
            found_oggs = set()
            for ogg in paths:
                ogg = str(ogg)
                found_oggs.add(ogg)

            to_delete = found_oggs - pacenote_expected_audio_files

            for deleteme in to_delete:
                os.remove(deleteme)
                logging.info(f"deleted {deleteme}")

    def pacenotes_json_to_obj(self, pacenotes_json):
        objs = []

        for fname, single_file_json in pacenotes_json:
            # print(fname)

            mission_id = self.get_mission_id_from_path(fname)
            mission_location = self.get_mission_location_from_path(fname)

            for version in single_file_json['versions']:
                authors = version['authors']
                desc = version['description']
                version_id = f"version{version['id']}"
                version_installed = version['installed']
                language_code = version['language_code']
                version_name = version['name']
                voice = version['voice']
                voice_name = version['voice_name']
                pacenotes = version['pacenotes']

                for pacenote in pacenotes:
                    note_name = pacenote['name']
                    note_text = pacenote['note']
                    audio_fname = f'pacenote_{self.normalize_pacenote_text(note_text)}.ogg'
                    # audio_path acts as the pacenote id
                    audio_path = self.build_pacenotes_audio_file_path(fname, version_id, audio_fname)

                    data_dict = {}
                    data_dict['pacenotes_fname'] = fname
                    data_dict['mission_id'] = mission_id
                    data_dict['mission_location'] = mission_location

                    data_dict['authors'] = authors
                    data_dict['desc'] = desc
                    data_dict['version_id'] = version_id
                    data_dict['version_installed'] = version_installed
                    data_dict['language_code'] = language_code
                    data_dict['version_name'] = version_name
                    data_dict['voice'] = voice
                    data_dict['voice_name'] = voice_name

                    data_dict['note_name'] = note_name
                    data_dict['note_text'] = note_text
                    data_dict['audio_fname'] = audio_fname
                    data_dict['audio_path'] = audio_path

                    # data_dict['filesystem_status'] = statuses.PN_STATUS_UNKNOWN
                    # data_dict['network_status'] = None
                    # data_dict['updated_at'] = time.time()

                    pn = Pacenote()
                    pn.set_data(data_dict)

                    objs.append(pn)

        return objs

    def rally_json_to_obj(self, rally_json):
        objs = []

        for fname, single_file_json in rally_json:
            # print(fname)

            mission_id = self.get_mission_id_from_path(fname)
            mission_location = self.get_mission_location_from_path(fname)

            # 1. iterate over notebooks
            # 2. get the pacenotes field
            # 3. iterate over pacenotes

            for notebook in single_file_json['notebooks']:
                authors = notebook['authors']
                description = notebook['description']
                notebook_name = notebook['name']
                notebook_oldId = notebook['oldId']
                installed = notebook['installed']
                pacenotes = notebook['pacenotes']
                voice = notebook['voice']

                for pacenote in pacenotes:
                    pacenote_name = pacenote['name']
                    note = pacenote['note']
                    waypoints = pacenote['pacenoteWaypoints']

                    audio_fname = f'pacenote_{self.normalize_pacenote_text(note)}.ogg'
                    audio_path = self.build_rally_audio_file_path(fname, notebook_name, audio_fname)

                    data_dict = {}
                    data_dict['pacenotes_fname'] = fname
                    data_dict['mission_id'] = mission_id
                    data_dict['mission_location'] = mission_location

                    data_dict['authors'] = authors
                    data_dict['desc'] = description
                    data_dict['version_id'] = str(notebook_oldId)
                    data_dict['version_installed'] = installed
                    data_dict['version_name'] = notebook_name

                    voice_config = self.settings_manager.voices[voice]
                    def name_with_cloud(cloud, field):
                        return "_".join([cloud, field])
                    cloud = 'gcp'
                    data_dict['language_code'] = voice_config[name_with_cloud(cloud, 'language_code')]
                    data_dict['voice_name'] = voice_config[name_with_cloud(cloud, 'voice_name')]
                    data_dict['voice'] = voice

                    data_dict['note_name'] = pacenote_name
                    data_dict['note_text'] = note
                    data_dict['audio_fname'] = audio_fname
                    data_dict['audio_path'] = audio_path

                    pn = Pacenote()
                    pn.set_data(data_dict)

                    if note != "":
                        objs.append(pn)

        return objs

    def build_pacenotes_audio_file_path(self, pacenotes_json_fname, version_id, pacenote_fname):
        pacenotes_dir = os.path.dirname(pacenotes_json_fname)
        fname = os.path.join(pacenotes_dir, 'pacenotes', version_id, pacenote_fname)
        return fname

    def build_rally_audio_file_path(self, rally_json_fname, notebook_name, pacenote_fname):

        def clean_string(s):
            s = re.sub(r'[^a-zA-Z0-9]', '_', s)  # Replace everything but letters and numbers with '_'
            s = re.sub(r'_+', '_', s)            # Replace multiple consecutive '_' with a single '_'
            return s

        pacenotes_dir = os.path.dirname(rally_json_fname)
        fname = os.path.join(pacenotes_dir, 'pacenotes', clean_string(notebook_name), pacenote_fname)
        return fname

    # also needs to be changed in the private repo, and in the custom lua flowgraph code.
    # def normalize_pacenote_text(self, input):
    #     # Convert the input to lower case
    #     input = input.lower()

    #     # special char subs
    #     input = input.replace(',', 'C')
    #     input = input.replace('?', 'Q')
    #     input = input.replace('.', 'P')
    #     input = input.replace(';', 'S')
    #     input = input.replace('!', 'E')

    #     # Substitute any non-alphanumeric character with a hyphen
    #     input = re.sub(r'\W', '-', input)


    #     # Remove any consecutive hyphens
    #     input = re.sub(r'-+', '-', input)

    #     # Remove any leading or trailing hyphens
    #     input = re.sub(r'^-', '', input)
    #     input = re.sub(r'-$', '', input)

    #     return input

    def normalize_pacenote_text(self, s):
        hash_value = 0
        for char in s:
            hash_value = (hash_value * 33 + ord(char)) % 2_147_483_647
        return hash_value

    def get_mission_id_from_path(self, fname):
        pattern = r"missions\\([^\\]+\\[^\\]+\\[^\\]+)"
        match = re.search(pattern, fname)

        if match:
            return match.group(1)
        else:
            raise ValueError(f"couldnt extract mission id from: {fname}")

    def get_mission_location_from_path(self, fname):
        # pattern = r"BeamNG\.drive\\\d\.\d+\\(.*)\\gameplay"
        pattern = r"BeamNG\.drive\\\d\.\d+\\(?:.*?)gameplay\\missions\\(.+)\\(pacenotes|rally).(pacenotes|rally).json"
        match = re.search(pattern, fname)
        # print(f"checking for mission id: {fname}")

        if match:
            m = match.group(1)
            # print(f"found: {m}")
            return m
        else:
            raise ValueError(f"couldnt extract mission location from: {fname}")

