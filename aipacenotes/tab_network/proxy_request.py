import json
import requests
import time
from datetime import datetime
import uuid

import aipacenotes.util
import aipacenotes.settings

if aipacenotes.util.is_dev() and aipacenotes.util.is_mac():
    BASE_URL = 'http://localhost:3000'
else:
    BASE_URL = 'https://aipacenotes.alxb.us'

# BASE_URL = 'http://192.168.1.76:3000'

headers = [
    { 'name': 'http status', 'width': 200 },
    { 'name': 'duration', 'width': 100 },
    # { 'name': 'created_at', 'width': 200 },
    { 'name': 'method', 'width': 100 },
    { 'name': 'path', 'width': 500 },
    { 'name': 'request_size', 'width': 100 },
    { 'name': 'response_size', 'width': 100 },
]

class ProxyRequest:
    def __init__(self, request_body, api_key=None):
        self.completed = False
        self.api_key = api_key or aipacenotes.settings.user_settings.get_api_key()
        self.uuid = str(uuid.uuid4())
        self._col_cache = []
        self.request_body = request_body
        self.response = None
        self.response_json = None
        self.duration_ms = None
        self._request_size = None

    @staticmethod
    def do_healthcheck(api_key):
        req = ProxyRequest({
            'created_at': datetime.now().isoformat(),
            'method': 'GET',
            'path': '/api/healthcheck',
            'body': {},
        }, api_key)
        req.execute()
        return req

    def execute(self):
        self.completed = True
        start_time = time.time()

        request_process_ts = datetime.now().isoformat()

        url = f"{BASE_URL}{self.path()}"
        headers = {
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key,
            'X-Aip-Client-UUID': aipacenotes.settings.user_settings.get_uuid(),
        }

        params = {
            "proxied_at": request_process_ts,
            "beamng_created_at": self.created_at(),
            "uuid": self.uuid,
        }

        if self.method() == 'GET':
            self._request_size = 0
            self.response = requests.get(url, headers=headers, params=params)
        if self.method() == 'POST':
            request_body = json.dumps(self.body()).encode('utf-8')
            self._request_size = len(request_body)
            self.response = requests.post(url, data=request_body, headers=headers, params=params)

        if self.response:
            self.response_json = self.response.json()

        end_time = time.time()
        self.duration_ms = (end_time - start_time) * 1000

        self.clear_col_cache()

    def clear_col_cache(self):
        self._col_cache = None

    def cache_column(self):
        if not self._col_cache:
            self._col_cache = [
                self.response_status(),
                self.duration_col(),
                # self.created_at(),
                self.method(),
                self.path(),
                aipacenotes.util.byte_str(self.request_size()),
                aipacenotes.util.byte_str(self.response_size()),
            ]

    def request_size(self):
        return self._request_size

    def response_size(self):
        if self.response:
            return len(self.response.content)
        else:
            return '-'

    def response_status(self):
        if self.response:
            return f"{self.response.reason} ({self.response.status_code})"
        else:
            return '-'

    def duration_col(self):
        if self.duration_ms:
            return f"{self.duration_ms:.2f}ms"
        else:
            return ''

    def cols(self, col):
        self.cache_column()
        return self._col_cache[col]

    def response_json_for_game(self):
        return {'ok': True}

    def created_at(self):
        return self.request_body['created_at']

    def method(self):
        return self.request_body['method']

    def path(self):
        return self.request_body['path']

    def body(self):
        return self.request_body['body']

    def response_body_tooltip_text(self):
        if self.response:
            if 'application/json' in self.response.headers.get('Content-Type', ''):
                formatted_json = json.dumps(self.response_json, indent=4)
                return formatted_json
            else:
                return self.response.text
        else:
            return "n/a"
