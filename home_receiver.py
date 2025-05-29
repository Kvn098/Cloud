from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "job_data.json")

@app.route("/", methods=["GET"])
def health_check():
    return "✅ Shift Receiver Running"

@app.route("/apply", methods=["POST"])
def receive_shift():
    data = request.get_json()
    if not data or "jobId" not in data or "scheduleId" not in data:
        return "❌ Invalid shift data", 400

    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

    print(f"[📥] Received shift: {data['jobId']} | {data['scheduleId']}")
    return "✅ Shift saved", 200

if __name__ == "__main__":
    app.run(port=5000)
