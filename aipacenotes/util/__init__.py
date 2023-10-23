import os

def normalize_path(in_path):
    return os.path.normpath(in_path).replace("\\", "/")