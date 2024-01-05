import os
import time
from . import statuses

class Pacenote:
    dynamic_attrs = ['filesystem_status', 'network_status', 'updated_at']
    static_attrs = [
        'pacenotes_fname',
        'mission_id', 'mission_location',
        'authors', 'desc',
        'version_id', 'version_installed', 'version_name', 'language_code', 'voice', 'voice_name',
        'note_name', 'note_text',
        'audio_fname', 'audio_path',
    ]
    all_attrs = static_attrs + dynamic_attrs
    all_attr_set = set(all_attrs)

    def __init__(self):
        self.dirty = False
        for attr in self.all_attrs:
            setattr(self, attr, None)

    def touch(self):
        self.updated_at = time.time()

    def set_dirty(self):
        self.dirty = True

    def clear_dirty(self):
        self.dirty = False

    @property
    def id(self):
        return self.note_name + '+' + self.audio_path

    def set_data(self, data_dict):
        for key, value in data_dict.items():
            if key in self.static_attrs and hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"tried to set illegal attr on pacenote: {key}")

    def get_data(self, field):
        return getattr(self, field)

    def refresh_filesystem_status(self):
        # if self.dirty:
        #     print(f'pacenote is dirty, setting to NEEDS_SYNC')
        #     self.filesystem_status = statuses.PN_STATUS_NEEDS_SYNC
        #     # self.clear_dirty()
        if os.path.isfile(self.audio_path):
            # print(f'pacenote audio_path exists, setting to OK')
            self.filesystem_status = statuses.PN_STATUS_OK
        else:
            logging.info(f"pacenote needs sync. audio file doesnt exist: {self.audio_path}")
            self.filesystem_status = statuses.PN_STATUS_NEEDS_SYNC

    @property
    def status(self):
        return self.network_status or self.filesystem_status
