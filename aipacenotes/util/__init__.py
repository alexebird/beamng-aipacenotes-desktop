import os
import re
# import requests
import zipfile

UNKNOWN_PLACEHOLDER = '[unknown]'

def normalize_path(in_path):
    return os.path.normpath(in_path).replace("\\", "/")

def clean_name_for_path(a_string):
    a_string = re.sub(r'[^a-zA-Z0-9]', '_', a_string)  # Replace everything but letters and numbers with '_'
    a_string = re.sub(r'_+', '_', a_string)            # Replace multiple consecutive '_' with a single '_'
    return a_string

# def fetch_json_data(url):
#     response = requests.get(url)
#
#     if response.status_code == 200:
#         return response.json()
#     else:
#         return None
#
# DEFAULT_VOICES_URL = "https://raw.githubusercontent.com/alexebird/beamng-aipacenotes-mod/master/settings/aipacenotes/default.voices.json"
# def fetch_default_voices():
#     return fetch_json_data(DEFAULT_VOICES_URL)

def read_file_from_zip(zip_path, file_name):
    try:
        # Open the zip file
        with zipfile.ZipFile(zip_path, 'r') as z:
            # Try to open the specific file within the zip file
            try:
                with z.open(file_name) as f:
                    # Read the file contents
                    contents = f.read()
                    # Return or process the contents
                    return contents
            except KeyError:
                # Handle the case where the file isn't found in the zip archive
                print(f"Error: The file '{file_name}' does not exist in the zip archive.")
                return None
            except zipfile.BadZipFile:
                # Handle other zipfile related errors (e.g., corrupted file)
                print("Error: Bad zip file.")
                return None
    except FileNotFoundError:
        # Handle the case where the zip file itself isn't found
        print(f"Error: The zip file '{zip_path}' does not exist.")
        return None
