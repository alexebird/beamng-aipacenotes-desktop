from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/test.json')
def test_endpoint():
    return jsonify({"hello": "world"})

if __name__ == '__main__':
    app.run(debug=True)