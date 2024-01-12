import json
import logging
import time
import requests
import aipacenotes.settings

# TODO should be in settings.json
# BASE_URL = "http://localhost:8080"

# the flask app is mapped to the prefix `/f` by nginx.
BASE_URL = "https://aipacenotes.alxb.us/f"

create_pacenotes_audio_url = BASE_URL + '/pacenotes/audio/create'
healthcheck_url = BASE_URL + '/health'
transcribe_url = BASE_URL + '/transcribe'

last_healthcheck_ts = 0.0

def post_create_pacenotes_audio(pacenote_note, voice_config):
    data = {
        "note_text": pacenote_note,
        "voice_config": voice_config,
    }

    headers = {
        "Content-Type": "application/json",
        "aip-uuid": aipacenotes.settings.user_settings.get_uuid(),
    }

    # log_str = f"aip-client: POST {create_pacenotes_audio_url}"
    response = requests.post(create_pacenotes_audio_url, data=json.dumps(data), headers=headers)
    # logging.info(f"{log_str} -> {response.status_code}")

    return response

def get_healthcheck():
    global last_healthcheck_ts
    # log_str = f"aip-client: GET {healthcheck_url}"
    last_healthcheck_ts = time.time()
    headers = { "aip-uuid": aipacenotes.settings.user_settings.get_uuid() }
    response = requests.get(healthcheck_url, headers=headers, timeout=120)
    # logging.info(f"{log_str} -> {response.status_code}")

    if response.status_code == 200:
        return True
    else:
        return False

def get_healthcheck_rate_limited(rate_limit=50.0):
    if time.time() - last_healthcheck_ts > rate_limit:
        return get_healthcheck()
    else:
        return True

def post_transcribe(fname):
    with open(fname, 'rb') as f:
        files = {'audio': f}
        headers = {
            "aip-uuid": aipacenotes.settings.user_settings.get_uuid(),
        }
        # log_str = f"aip-client: POST {transcribe_url}"
        response = requests.post(transcribe_url, files=files, headers=headers)
        # logging.info(f"{log_str} -> {response.status_code}")
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return None
