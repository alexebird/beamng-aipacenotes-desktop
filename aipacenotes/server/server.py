from flask import Flask, jsonify

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

        @self.app.route('/recordings/actions/start')
        def recording_actions_start():
            self.callback_obj._on_recording_start()
            return jsonify({"msg": "recording was started"})

        @self.app.route('/recordings/actions/stop')
        def recording_actions_stop():
            self.callback_obj._on_recording_stop()
            return jsonify({"msg": "recording was stopped"})

        @self.app.route('/recordings/actions/cut')
        def recording_actions_cut():
            self.callback_obj._on_recording_cut()
            return jsonify({"msg": "recording was cut"})

    def run(self, debug=True):
        self.app.run(port=self.port, debug=debug, use_reloader=False)

if __name__ == '__main__':
    server = Server()
    server.run(debug=True)