from flask import Flask, jsonify, request

class Server:
    def __init__(self, callback_obj, port=27872):
        self.port = port
        self.app = Flask(__name__)
        self.callback_obj = callback_obj
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/test')
        def test_endpoint():
            return jsonify({"hello": "world"})

        @self.app.route('/recordings/actions/start', methods=['POST'])
        def recording_actions_start():
            vehicle_pos = request.json
            self.callback_obj._on_recording_start(vehicle_pos)
            return jsonify({"msg": "recording was started"})

        @self.app.route('/recordings/actions/stop', methods=['POST'])
        def recording_actions_stop():
            vehicle_pos = request.json
            self.callback_obj._on_recording_stop(vehicle_pos)
            return jsonify({"msg": "recording was stopped"})

        @self.app.route('/recordings/actions/cut', methods=['POST'])
        def recording_actions_cut():
            vehicle_pos = request.json
            self.callback_obj._on_recording_cut(vehicle_pos)
            return jsonify({"msg": "recording was cut"})

        @self.app.route('/transcript/<id>')
        def get_transcript(id):
            transcript_text = self.callback_obj._on_get_transcript(id)
            return jsonify({"msg": f"got transcript with id={id}", "transcript": transcript_text})

    def run(self, debug):
        self.app.run(port=self.port, debug=debug, use_reloader=False)

if __name__ == '__main__':
    server = Server()
    server.run(debug=True)
