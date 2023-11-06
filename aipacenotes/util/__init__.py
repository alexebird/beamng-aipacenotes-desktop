import os
import re

def normalize_path(in_path):
    return os.path.normpath(in_path).replace("\\", "/")

def clean_name_for_path(a_string):
    a_string = re.sub(r'[^a-zA-Z0-9]', '_', a_string)  # Replace everything but letters and numbers with '_'
    a_string = re.sub(r'_+', '_', a_string)            # Replace multiple consecutive '_' with a single '_'
    return a_string