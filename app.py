# app.py
from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
from typing import Dict, Any, List

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Global cache of days -> dict(username -> record)
DAYS: Dict[int, Dict[str, Dict[str, Any]]] = {}
DAY_LIST: List[int] = []

def load_data():
    global DAYS, DAY_LIST
    DAYS = {}
    DAY_LIST = []
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR)
    for fname in os.listdir(DATA_DIR):
        if fname.lower().endswith(".json"):
            if fname == "index.json": 
                continue
            path = os.path.join(DATA_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # filename patterns allowed: day1.json or day_1.json or day-1.json
                import re
                m = re.search(r"(\d+)", fname)
                if m:
                    day = int(m.group(1))
                    # ensure usernames are lowercase keys for searching
                    normalized = {k.lower(): v for k, v in data.items()}
                    DAYS[day] = normalized
                    DAY_LIST.append(day)
            except Exception as e:
                print("Failed to read", fname, e)
    DAY_LIST.sort()

# initial load
load_data()

@app.route("/")
def index():
    return render_template("index.html", days=DAY_LIST)

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            return redirect(url_for("index"))
        username_norm = username.lower()
        # search across days
        found = []
        for day in DAY_LIST:
            day_data = DAYS.get(day, {})
            if username_norm in day_data:
                rec = day_data[username_norm].copy()
                rec.setdefault("day", day)
                rec.setdefault("username", username)
                found.append(rec)
        return render_template("result.html", username=username, results=found, days=DAY_LIST)
    else:
        # GET - maybe user supplied ?username=...
        username = request.args.get("username", "").strip()
        if username:
            return redirect(url_for("search"))  # force POST flow for simplicity
        return redirect(url_for("index"))

@app.route("/leaderboard/<int:day>")
def leaderboard(day):
    day_data = DAYS.get(day)
    if not day_data:
        return render_template("leaderboard.html", day=day, rows=[], days=DAY_LIST, message="No data for that day.")
    # day_data is {username_lower: record}, we want to sort by rank ascending
    rows = []
    for uname_lower, rec in day_data.items():
        rows.append({
            "username": rec.get("username", uname_lower),
            "rank": rec.get("rank"),
            "power": rec.get("power"),
            "extra": rec.get("extra", "")
        })
    rows_sorted = sorted(rows, key=lambda r: (r["rank"] if r["rank"] is not None else 1e9))
    return render_template("leaderboard.html", day=day, rows=rows_sorted, days=DAY_LIST, message=None)

# Simple API endpoints
@app.route("/api/search")
def api_search():
    username = request.args.get("q", "").strip().lower()
    if not username:
        return jsonify({"error": "missing q parameter"}), 400
    found = []
    for day in DAY_LIST:
        day_data = DAYS.get(day, {})
        if username in day_data:
            rec = day_data[username].copy()
            rec.setdefault("day", day)
            found.append(rec)
    return jsonify({"username": username, "results": found})

@app.route("/api/leaderboard/<int:day>")
def api_leaderboard(day):
    day_data = DAYS.get(day)
    if not day_data:
        return jsonify({"error": "no data for day"}), 404
    rows = []
    for uname_lower, rec in day_data.items():
        rows.append({"username": rec.get("username", uname_lower), "rank": rec.get("rank"), "power": rec.get("power")})
    rows_sorted = sorted(rows, key=lambda r: (r["rank"] if r["rank"] is not None else 1e9))
    return jsonify({"day": day, "rows": rows_sorted})

# Admin-lite reload endpoint (no auth) - ok for small private deploys; remove or protect on public server
@app.route("/admin/reload", methods=["POST"])
def admin_reload():
    load_data()
    return jsonify({"status": "reloaded", "days": DAY_LIST})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)

