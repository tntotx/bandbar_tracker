from flask import Flask, render_template, request, jsonify
import json
from datetime import datetime
import os
import platform
from pathlib import Path
import csv
import uuid

if platform.system() == "Windows":
    DATA_DIR = Path(os.environ["APPDATA"]) / "BandBarTracker"
else:
    DATA_DIR = Path.home() / ".bandbar_tracker"

DATA_DIR.mkdir(exist_ok=True)
WORKOUT_FILE = DATA_DIR / "workout_log.json"
TEMPLATE_FILE = DATA_DIR / "templates.json"

app = Flask(__name__, static_folder='static', template_folder='templates')

from flask_cors import CORS
CORS(app)

def load_data(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/manifest.json")
def manifest():
    return jsonify({"name": "Band Bar Tracker", "short_name": "BandBar", "start_url": "/", "display": "standalone", "background_color": "#1e1e1e", "theme_color": "#1e1e1e", "icons": [{"src": 
"https://cdn-icons-png.flaticon.com/512/2966/2966288.png", "sizes": "192x192", "type": "image/png"}]})

@app.route("/api/templates", methods=["GET"])
def get_templates():
    return jsonify(load_data(TEMPLATE_FILE))

@app.route("/api/templates", methods=["POST"])
def create_template():
    data = request.json
    templates = load_data(TEMPLATE_FILE)
    templates.append(data)
    save_data(TEMPLATE_FILE, templates)
    return jsonify(data), 201

@app.route("/api/templates/<id>", methods=["PUT"])
def update_template(id):
    data = request.json
    templates = load_data(TEMPLATE_FILE)
    for i, t in enumerate(templates):
        if t.get("id") == id:
            templates[i] = data
            save_data(TEMPLATE_FILE, templates)
            return jsonify(data)
    return jsonify({"error": "Template not found"}), 404

@app.route("/api/templates/<id>", methods=["DELETE"])
def delete_template(id):
    templates = load_data(TEMPLATE_FILE)
    templates = [t for t in templates if t.get("id") != id]
    save_data(TEMPLATE_FILE, templates)
    return jsonify({"status": "deleted"})

@app.route("/api/workouts", methods=["GET"])
def get_workouts():
    workouts = load_data(WORKOUT_FILE)
    workouts.sort(key=lambda x: x["date"], reverse=True)
    return jsonify(workouts)

@app.route("/api/workouts", methods=["POST"])
def create_workout():
    data = request.json
    workouts = load_data(WORKOUT_FILE)
    data["id"] = str(uuid.uuid4())
    data["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    workouts.append(data)
    save_data(WORKOUT_FILE, workouts)
    return jsonify(data), 201

@app.route("/api/workouts/<id>", methods=["PUT"])
def update_workout(id):
    data = request.json
    workouts = load_data(WORKOUT_FILE)
    for i, w in enumerate(workouts):
        if w.get("id") == id:
            workouts[i] = data
            save_data(WORKOUT_FILE, workouts)
            return jsonify(data)
    return jsonify({"error": "Workout not found"}), 404

@app.route("/api/workouts/<id>", methods=["DELETE"])
def delete_workout(id):
    workouts = load_data(WORKOUT_FILE)
    workouts = [w for w in workouts if w.get("id") != id]
    save_data(WORKOUT_FILE, workouts)
    return jsonify({"status": "deleted"})

@app.route("/api/progress", methods=["GET"])
def get_progress():
    workouts = load_data(WORKOUT_FILE)
    if not workouts:
        return jsonify([])
    pr_full, pr_partial = {}, {}
    for workout in workouts:
        for ex in workout["exercises"]:
            f = sum(int(s.get("reps", 0)) for s in ex["sets"])
            p = 0
            if ex.get("partials"):
                for part in ex.get("partials", "").split("+"):
                    digits = ''.join(c if c.isdigit() else "" for c in part)
                    if digits:
                        p += int(digits)
            pr_full[ex["exercise"]] = max(pr_full.get(ex["exercise"], 0), f)
            pr_partial[ex["exercise"]] = max(pr_partial.get(ex["exercise"], 0), p)
    progress = []
    for workout in workouts:
        for ex in workout["exercises"]:
            f = sum(int(s.get("reps", 0)) for s in ex["sets"])
            p = 0
            if ex.get("partials"):
                for part in ex.get("partials", "").split("+"):
                    digits = ''.join(c if c.isdigit() else "" for c in part)
                    if digits:
                        p += int(digits)
            tags = []
            if f == pr_full.get(ex["exercise"], 0) and p == pr_partial.get(ex["exercise"], 0):
                tags = ["pr_both"]
            elif f == pr_full.get(ex["exercise"], 0):
                tags = ["pr_full"]
            elif p == pr_partial.get(ex["exercise"], 0):
                tags = ["pr_partial"]
            if tags:
                progress.append({"date": workout["date"], "exercise": ex["exercise"], "full": f, "partial": p, "tags": tags})
    return jsonify(progress)

@app.route("/api/export", methods=["GET"])
def export_csv():
    workouts = load_data(WORKOUT_FILE)
    from io import StringIO
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Workout ID', 'Date', 'Exercise', 'Band', 'Full Reps', 'Partial Reps'])
    for i, workout in enumerate(workouts):
        for j, ex in enumerate(workout["exercises"]):
            for k, s in enumerate(ex["sets"]):
                writer.writerow([i + 1, workout["date"], ex["exercise"], s.get("band", ""), s.get("reps", 0), s.get("partials", "")])
    output.seek(0)
    return output.getvalue()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
