import json
# import os
import time
import requests
from urllib.parse import urljoin

# TODO should be in settings.json
# base_url = "https://pacenotes-concurrent-mo5q6vt2ea-uw.a.run.app"
# base_url = "http://localhost:8080"
base_url = "https://aipacenotes.alxb.us"
prefix = 'f'

create_pacenotes_audio_url = urljoin(base_url, 'f/pacenotes/audio/create')
healthcheck_url = urljoin(base_url, 'f/health')
transcribe_url = urljoin(base_url, 'f/transcribe')

last_healthcheck_ts = 0.0

def post_create_pacenotes_audio(pacenote_note, voice_config):
    data = {
        "note_text": pacenote_note,
        "voice_config": voice_config,
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(create_pacenotes_audio_url, data=json.dumps(data), headers=headers)

    return response

def get_healthcheck():
    global last_healthcheck_ts
    log_str = f"aip-client: GET {healthcheck_url}"
    last_healthcheck_ts = time.time()
    response = requests.get(healthcheck_url, timeout=120)
    print(f"{log_str} -> {response.status_code}")

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
    # data = {
    #     "note_text": pacenote.note_text,
    #     "voice_name": pacenote.voice_name,
    #     "language_code": pacenote.language_code,
    # }

    # headers = {
    #     "Content-Type": "application/json"
    # }

    with open(fname, 'rb') as f:
        files = {'audio': f}
        response = requests.post(transcribe_url, files=files)
        # response = requests.post(create_pacenotes_audio_url, data=json.dumps(data), headers=headers)
        # if response.status_code == 200:
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return None