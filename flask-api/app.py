from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    return jsonify({"message": "Flask API is working!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)