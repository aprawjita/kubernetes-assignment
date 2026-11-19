import os
from datetime import datetime

from flask import Flask, jsonify, request
from pymongo import MongoClient


app = Flask(__name__)

mongodb_uri = os.environ.get(
    "MONGODB_URI",
    "mongodb://localhost:27017/",
)
client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
db = client.flask_db
collection = db.data


@app.route("/", methods=["GET"])
def index():
    return f"Welcome to the Flask app! The current time is: {datetime.now()}"


@app.route("/data", methods=["GET", "POST"])
def data():
    if request.method == "POST":
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "A JSON object is required"}), 400

        collection.insert_one(payload)
        return jsonify({"status": "Data inserted"}), 201

    documents = list(collection.find({}, {"_id": 0}))
    return jsonify(documents), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
