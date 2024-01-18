import logging
import re
from flask import Flask, jsonify, request, has_request_context

class NoLoggingFilter(logging.Filter):
    pattern = r'^GET /transcripts/(\d+)'

    def filter(self, record):
        if record.args and len(record.args) > 0:
            path_arg = record.args[0]
            if re.search(self.pattern, path_arg):
                return False
        return True

class Server:
    def __init__(self, server_thread, port=27872):
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.addFilter(NoLoggingFilter())

        self.port = port
        self.app = Flask(__name__)
        self.server_thread = server_thread
        self.proxy_request_manager = self.server_thread.proxy_request_manager

        self.setup_test_routes()
        self.setup_proxy_routes()
        self.setup_recording_routes()

    def setup_test_routes(self):
        @self.app.route('/test')
        def test_endpoint():
            return jsonify({"hello": "world"})

    def setup_proxy_routes(self):
        @self.app.route('/proxy', methods=['POST'])
        def proxy_test():
            proxy_req = self.proxy_request_manager.add_request(request.json)
            return jsonify(proxy_req.response_json_for_game())

    def setup_recording_routes(self):
        @self.app.route('/recordings/actions/start', methods=['POST'])
        def recording_actions_start():
            if self.server_thread.transcribe_tab.recording_enabled():
                self.server_thread._on_recording_start()
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "recording is not enabled"})

        @self.app.route('/recordings/actions/stop', methods=['POST'])
        def recording_actions_stop():
            if self.server_thread.transcribe_tab.recording_enabled():
                create_transcript = False
                self.server_thread._on_recording_stop(create_transcript)
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "recording is not enabled"})

        @self.app.route('/recordings/actions/cut', methods=['POST'])
        def recording_actions_cut():
            if self.server_thread.transcribe_tab.recording_enabled():
                vehicle_data = request.json
                self.server_thread._on_recording_cut(vehicle_data)
                return jsonify({"ok": True})
            else:
                return jsonify({"ok": False, "error": "recording is not enabled"})

        # @self.app.route('/transcript/<id>')
        # def get_transcript(id):
        #     transcript_text = self.server_thread._on_get_transcript(id)
        #     return jsonify({"msg": f"got transcript with id={id}", "transcript": transcript_text})

        @self.app.route('/transcripts/<count>')
        def get_transcripts_latest(count):
            transcripts = self.server_thread.get_transcripts(count)
            return jsonify({
                'ok': True,
                'is_recording': self.server_thread.transcribe_tab.is_recording(),
                'transcripts': transcripts,
            })

    def run(self, debug=False):
        self.app.run(port=self.port, debug=debug, use_reloader=False)

if __name__ == '__main__':
    server = Server()
    server.run(debug=True)
