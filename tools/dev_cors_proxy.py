# server.py

from flask import Flask, jsonify, request
import random
import time
from flask_cors import CORS
import json
from requests import get, post

app = Flask(__name__)

cors = CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
)

sensor_url = "http://192.168.156.177"


@app.route("/api/v1/sensor_meta", methods=["GET"])
def proxy_sensor_meta():
    return get(f"{sensor_url}/api/v1/sensor_meta").json()


@app.route("/api/v1/sensor_data", methods=["GET"])
def proxy_sensor_data():
    sensor_index = request.args.get("sensor_index")
    return get(
        f"{sensor_url}/api/v1/sensor_data?sensor_index={sensor_index}"
    ).json()


@app.route("/api/v1/led", methods=["POST"])
def proxy_led():
    data = request.json
    return post(f"{sensor_url}/api/v1/led", json=data).json()

@app.route("/api/v1/sensor_name", methods=["POST"])
def proxy_sensor_name():
    sensor_index = request.args.get("sensor_index")
    data = request.json
    return post(f"{sensor_url}/api/v1/sensor_name?sensor_index={sensor_index}", json=data).json()


@app.route("/api/v1/led", methods=["GET"])
def proxy_get_led():
    return get(f"{sensor_url}/api/v1/led").json()


if __name__ == "__main__":
    app.run(debug=True, port=5123)
