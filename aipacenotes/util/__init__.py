import os
import uuid
import platform
import re
import uuid
import zipfile
import logging

AUTOFILL_BLOCKER = '#'
UNKNOWN_PLACEHOLDER = '[unknown]'
APP_NAME = 'AiPacenotesDesktop'

def create_uuid_file():
    if platform.system() == 'Windows':
        write_uuid_to_appdata()
        return read_uuid_from_appdata() or "heh"
    else:
        return uuid.uuid4()

THE_UUID = str(create_uuid_file())

def is_dev():
    return os.environ.get('AIP_DEV', 'f') == 't'

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
                logging.error(f"Error: The file '{file_name}' does not exist in the zip archive.")
                return None
            except zipfile.BadZipFile:
                # Handle other zipfile related errors (e.g., corrupted file)
                logging.error("Error: Bad zip file.")
                return None
    except FileNotFoundError:
        # Handle the case where the zip file itself isn't found
        logging.error(f"Error: The zip file '{zip_path}' does not exist.")
        return None

def open_file_explorer(file_path):
    if os.path.isfile(file_path):
        file_path = os.path.dirname(file_path)
    logging.info(f"opening {file_path}")
    os.startfile(file_path)

def write_uuid_to_appdata():
    appdata_dir = os.getenv('APPDATA')
    app_dir = os.path.join(appdata_dir, APP_NAME)
    file_path = os.path.join(app_dir, 'uuid.txt')

    os.makedirs(app_dir, exist_ok=True)

    if not os.path.exists(file_path):
        random_uuid = uuid.uuid4()
        with open(file_path, 'w') as file:
            file.write(str(random_uuid))

    return file_path

def read_uuid_from_appdata():
    appdata_dir = os.getenv('APPDATA')
    file_path = os.path.join(appdata_dir, APP_NAME, 'uuid.txt')

    try:
        with open(file_path, 'r') as file:
            uuid_str = file.read()
            return uuid_str
    except FileNotFoundError:
        return None

def api_key():
    return os.environ.get('API_KEY', 'set_API_KEY')
