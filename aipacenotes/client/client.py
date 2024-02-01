import json
import logging
import requests
import aipacenotes.settings

HEADER_UUID = 'X-Aip-Client-UUID'

# healthcheck_url = '/healthcheck'
create_pacenotes_audio_url = '/pacenotes/audio/create'
transcribe_url = '/transcribe'
translate_all_url = '/translate_all'

def mkurl(suffix):
    if aipacenotes.settings.get_local_vocalizer():
        base_url = "http://localhost:8080"
    else:
        # the flask app is mapped to the prefix `/f` by nginx.
        base_url = "https://aipacenotes.alxb.us/f"
    return base_url + suffix


# last_healthcheck_ts = 0.0

# def get_healthcheck():
#     global last_healthcheck_ts
#     last_healthcheck_ts = time.time()
#     headers = {
#         HEADER_UUID: aipacenotes.settings.user_settings.get_uuid(),
#     }
#     response = requests.get(mkurl(healthcheck_url), headers=headers, timeout=120)
#
#     if response.status_code == 200:
#         return True
#     else:
#         return False
#
# def get_healthcheck_rate_limited(rate_limit=50.0):
#     if time.time() - last_healthcheck_ts > rate_limit:
#         return get_healthcheck()
#     else:
#         return True

def post_create_pacenote_audio(note_name, note_text, voice_config):
    data = {
        "note_name": note_name,
        "note_text": note_text,
        "voice_config": voice_config,
    }

    headers = {
        "Content-Type": "application/json",
        HEADER_UUID: aipacenotes.settings.user_settings.get_uuid(),
    }

    response = requests.post(mkurl(create_pacenotes_audio_url), data=json.dumps(data), headers=headers)

    return response

def post_transcribe(fname):
    with open(fname, 'rb') as f:
        files = {'audio': f}
        headers = {
            HEADER_UUID: aipacenotes.settings.user_settings.get_uuid(),
        }
        response = requests.post(mkurl(transcribe_url), files=files, headers=headers)

        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return None

def post_translate_all(body):
    data = body

    headers = {
        "Content-Type": "application/json",
        HEADER_UUID: aipacenotes.settings.user_settings.get_uuid(),
    }

    response = requests.post(mkurl(translate_all_url), data=json.dumps(data), headers=headers)

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {'ok': False, 'msg': 'couldnt decode json on client side'}
