import pathlib
import logging

from .rally_file import NotebookFile

class SearchPath:
    def __init__(self, fname):
        self.fname = fname
        self.rally_files = []

    def __str__(self):
        if not self.fname.endswith('/'):
            return self.fname + '/'
        return self.fname

    def file_explorer_path(self):
        return self.fname

class RallyFileScanner:
    pattern =  '*.notebook.json'

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
                rally = NotebookFile(match)
                rally.load()
                sp.rally_files.append(rally)
            
            self.search_paths.append(sp)