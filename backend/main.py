# backend/main.py
"""
Flask API entrypoint for CanvasHelper.

Routes:
- GET  /api/courses?user_id=...                -> list courses for a user (default 'self')
- GET  /api/assignments?course_id=...          -> parsed assignments for a course
- GET  /api/assignments/raw?course_id=...      -> raw assignments JSON (no parsing)
- GET  /api/assignment/<assignment_id>?course_id=...
                                               -> single assignment detail
- GET  /api/assignment/<assignment_id>/subs?course_id=...
                                               -> submissions for an assignment
- GET  /api/course/<course_id>/files           -> course files
- POST /api/parse_custom                        -> send raw assignment list JSON to parser + summary
- POST /api/download_file                       -> download a file URL via backend session
"""

import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# Load .env from backend/
load_dotenv()

# utils (Canvas API + parser)
from utils.canvas_requests import (
    get_user_courses,
    get_parsed_course_assignments,
    get_course_assignments,
    get_assignment,
    get_course_files,
    get_assignment_submissions,
    download_file,
)
from utils.canvas_parser import parse_canvas_assignment, summarize_assignments

# Basic app setup
app = Flask(__name__)
CORS(app, origins="*")
logging.basicConfig(level=logging.INFO)


# -----------------------
# Helper: JSON error response
# -----------------------
def json_error(message: str, code: int = 500):
    return jsonify({"error": message}), code


# -----------------------
# Routes
# -----------------------
@app.route("/api/courses", methods=["GET"])
def route_get_courses():
    user_id = request.args.get("user_id", "self")
    try:
        courses = get_user_courses(user_id=user_id)
        return jsonify(courses)
    except Exception as e:
        logging.exception("Failed to fetch courses")
        return json_error(str(e), 500)


@app.route("/api/assignments", methods=["GET"])
def route_get_assignments():
    course_id = request.args.get("course_id")
    if not course_id:
        return json_error("Missing query parameter: course_id", 400)

    try:
        # get_parsed_course_assignments handles parsing internally if parse=True
        parsed = get_parsed_course_assignments(int(course_id), parse=True)
        return jsonify(parsed)
    except Exception as e:
        logging.exception("Failed to fetch parsed assignments")
        return json_error(str(e), 500)


@app.route("/api/assignments/raw", methods=["GET"])
def route_get_assignments_raw():
    course_id = request.args.get("course_id")
    if not course_id:
        return json_error("Missing query parameter: course_id", 400)
    try:
        raw = get_course_assignments(int(course_id))
        return jsonify(raw)
    except Exception as e:
        logging.exception("Failed to fetch raw assignments")
        return json_error(str(e), 500)


@app.route("/api/assignment/<int:assignment_id>", methods=["GET"])
def route_get_assignment(assignment_id: int):
    course_id = request.args.get("course_id")
    if not course_id:
        return json_error("Missing query parameter: course_id", 400)
    try:
        assignment = get_assignment(int(course_id), int(assignment_id))
        return jsonify(assignment)
    except Exception as e:
        logging.exception("Failed to fetch assignment")
        return json_error(str(e), 500)


@app.route("/api/assignment/<int:assignment_id>/subs", methods=["GET"])
def route_get_assignment_submissions(assignment_id: int):
    course_id = request.args.get("course_id")
    if not course_id:
        return json_error("Missing query parameter: course_id", 400)
    try:
        subs = get_assignment_submissions(int(course_id), int(assignment_id))
        return jsonify(subs)
    except Exception as e:
        logging.exception("Failed to fetch submissions")
        return json_error(str(e), 500)


@app.route("/api/course/<int:course_id>/files", methods=["GET"])
def route_get_course_files(course_id: int):
    try:
        files = get_course_files(int(course_id))
        return jsonify(files)
    except Exception as e:
        logging.exception("Failed to fetch course files")
        return json_error(str(e), 500)


@app.route("/api/parse_custom", methods=["POST"])
def route_parse_custom():
    """
    Accepts JSON body: { "assignments": [ ... ] }
    where each element is a raw Canvas assignment object (as returned by Canvas API).
    Returns { "parsed": [...], "summary": "..." }
    """
    body = request.get_json(silent=True)
    if not body or "assignments" not in body:
        return json_error("Request JSON must contain 'assignments' field (list)", 400)

    raw_assignments = body["assignments"]
    try:
        parsed = [parse_canvas_assignment(a) for a in raw_assignments]
        summary_text = summarize_assignments(parsed)
        return jsonify({"parsed": parsed, "summary": summary_text})
    except Exception as e:
        logging.exception("Failed to parse custom assignments")
        return json_error(str(e), 500)


@app.route("/api/download_file", methods=["POST"])
def route_download_file():
    """
    Body: { "file_url": "<url>", "dest_path": "backend/tmp/file.pdf" (optional) }
    Downloads the file server-side using the Canvas session (authenticated).
    """
    body = request.get_json(silent=True)
    if not body or "file_url" not in body:
        return json_error("Request JSON must contain 'file_url'", 400)

    file_url = body["file_url"]
    dest_path = body.get("dest_path", "backend/tmp/downloaded_file")
    try:
        download_file(file_url, dest_path)
        return jsonify({"downloaded_to": dest_path})
    except Exception as e:
        logging.exception("Failed to download file")
        return json_error(str(e), 500)


# -----------------------
# Health / ready checks
# -----------------------
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# -----------------------
# Run server
# -----------------------
if __name__ == "__main__":
    # Run in debug mode during hackathon. In production, use a proper WSGI server.
    app.run(host="127.0.0.1", port=5000, debug=True)
