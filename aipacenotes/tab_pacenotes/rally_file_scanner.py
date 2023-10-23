import pathlib
import logging

from .rally_file import RallyFile

class SearchPath:
    def __init__(self, fname):
        self.fname = fname
        self.rally_files = []

    def __str__(self):
        return self.fname

class RallyFileScanner:
    pattern =  '*.rally.json'

    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
        self.search_paths = []

    def scan(self):
        self.search_paths = []

        for search_path in self.settings_manager.get_pacenotes_search_paths():
            sp = SearchPath(search_path)
            logging.info(f'scanning {search_path} for {self.pattern}')
            matches = pathlib.Path(search_path).rglob(self.pattern)

            for match in matches:
                rally = RallyFile(match)
                rally.load()
                sp.rally_files.append(rally)
            
            self.search_paths.append(sp)