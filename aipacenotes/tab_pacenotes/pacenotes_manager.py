import os
import re
import time
import json
import pathlib

from aipacenotes.tab_pacenotes import (
    statuses,
    Pacenote,
)

class Database():
    def __init__(self):
        self.pacenotes = []
        # unique index pacenotes on id
        self.unique_index_pn_id = {}
    
    def select(self, pnid):
        if pnid in self.unique_index_pn_id:
            return self.unique_index_pn_id[pnid]
        else:
            return None
    
    def insert(self, pacenote):
        pnid = pacenote.id
        if pnid in self.unique_index_pn_id:
            raise ValueError(f'insert: pacenote exists with id={pnid}')
        self.pacenotes.append(pacenote)
        self.unique_index_pn_id[pnid] = pacenote
        # pacenote.set_dirty()
        pacenote.touch()
        return pacenote
    
    def upsert(self, pacenote):
        pnid = pacenote.id
        if pnid in self.unique_index_pn_id:
            return self.update(pacenote)
        else:
            return self.insert(pacenote)
    
    def update(self, pacenote):
        pnid = pacenote.id
        existing = self.unique_index_pn_id[pnid]
        if existing is None:
            raise ValueError(f'update: pacenote doesnt exist with id={pnid}')

        def update_attrs(attrs):
            update_made = False
            for attr in attrs:
                old_val = getattr(existing, attr)
                new_val = getattr(pacenote, attr)
                if new_val != old_val:
                    setattr(pacenote, attr, new_val)
                    print(f'updated field {attr} from {old_val} to {new_val}')
                    update_made = True
            return update_made

        if update_attrs(Pacenote.static_attrs):
            existing.touch()
            existing.set_dirty()
        # update_attrs(Pacenote.dynamic_attrs)
        return existing

class PacenotesManager():
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.pacenotes_network_cache = {}
        self.db = Database()

    # db changes:
    # - delete pacenotes that dont exist in the scan, that arent pending network activity
    # - upsert all scanned pacenotes
    # - dont change network status
    def reconcile_fs_scan(self, scanned_pacenotes):
        for scan_pacenote in scanned_pacenotes:
            pacenote = self.db.upsert(scan_pacenote)
            if pacenote is None:
                raise ValueError("couldnt find pacenote after upsert. this shouldnt happen")

            pacenote.refresh_filesystem_status()

            # if pacenote.filesystem_status == statuses.PN_STATUS_OK and new_fs_status == statuses.PN_STATUS_NEEDS_SYNC:

            # pacenote.filesystem_status = new_fs_status

            # nw_status = pacenote.network_status
            # if nw_status is not None:
            #     pacenote.status = nw_status
            # else:
            #     pacenote.status = pacenote.filesystem_status

    def scan_pacenotes_files(self, pacenotes_files):
        scan_data = []

        def load_pacenotes_file(fname):
            with open(fname) as f:
                return (fname, json.load(f))
        
        for fname in pacenotes_files:
            rv = load_pacenotes_file(fname)
            scan_data.append(rv)

        scanned_objs = self.pacenotes_json_to_obj(scan_data)
        self.reconcile_fs_scan(scanned_objs)

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
                print(f"deleted {deleteme}")


    def pacenotes_json_to_obj(self, pacenotes_json):
        objs = []

        for fname, single_file_json in pacenotes_json:
            # print(fname)

            mission_id = self.get_mission_id_from_path(fname)
            mission_location = self.get_mission_location_from_path(fname)

            for version in single_file_json['versions']:
                authors = version['authors']
                desc = version['description']
                version_id = version['id']
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
                    data_dict['pacenotes'] = pacenotes

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

    def build_pacenotes_audio_file_path(self, pacenotes_json_fname, version_id, pacenote_fname):
        pacenotes_dir = os.path.dirname(pacenotes_json_fname)
        ver_str = f'version{version_id}'
        fname = os.path.join(pacenotes_dir, 'pacenotes', ver_str, pacenote_fname)
        return fname
    
    # also needs to be changed in the private repo, and in the custom lua flowgraph code.
    def normalize_pacenote_text(self, input):
        # Convert the input to lower case
        input = input.lower()

        # Substitute any non-alphanumeric character with a hyphen
        input = re.sub(r'\W', '-', input)

        # Remove any consecutive hyphens
        input = re.sub(r'-+', '-', input)

        # Remove any leading or trailing hyphens
        input = re.sub(r'^-', '', input)
        input = re.sub(r'-$', '', input)

        return input
    
    def get_mission_id_from_path(self, fname):
        pattern = r"missions\\([^\\]+\\[^\\]+\\[^\\]+)"
        match = re.search(pattern, fname)

        if match:
            return match.group(1)
        else:
            raise ValueError(f"couldnt extract mission id from: {fname}")

    def get_mission_location_from_path(self, fname):
        # pattern = r"BeamNG\.drive\\\d\.\d+\\(.*)\\gameplay"
        pattern = r"BeamNG\.drive\\\d\.\d+\\(?:.*?)gameplay\\missions\\(.+)\\pacenotes.pacenotes.json"
        match = re.search(pattern, fname)
        # print(f"checking for mission id: {fname}")

        if match:
            m = match.group(1)
            # print(f"found: {m}")
            return m
        else:
            raise ValueError(f"couldnt extract mission id from: {fname}")
    