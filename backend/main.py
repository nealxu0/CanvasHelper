# backend/main.py
"""
CanvasHelper Flask API - Integrated version with:
 - Canvas endpoints (courses, assignments, files, submissions)
 - RAG endpoints (ingest, QA) via ingest.py and query.py (LangChain + Chroma + Ollama)
 - Sklearn schedule model endpoints: train, predict, reload
 - Uses backend/config.py, backend/utils/*, backend/ingest.py, backend/query.py, backend/train_model.py

Drop this file into backend/main.py and run with your venv active.
Make sure backend/.env contains your CANVAS and optional OLLAMA settings.
"""

from __future__ import annotations
import logging
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS

# standard libs for model loading
import joblib
import json

# config & helpers (assumes backend/ is current package)
from config import (
    ensure_dirs,
    MODELS_DIR,
    SCHEDULE_MODEL_PATH,
)

# Canvas utils & parser (helpers placed under backend/utils/)
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

# RAG / ingestion / training modules
from ingest import run_ingest
from query import query_rag
import train_model  # train_model.main() will retrain & persist model (as implemented)

# ---- App init ----
load_dotenv()  # load backend/.env if present
ensure_dirs()

app = Flask(__name__)
CORS(app, origins="*")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("canvashelper")

# ---- Model holder and utilities ----
SCHEDULE_MODEL = None  # global to hold loaded sklearn pipeline


def load_schedule_model() -> Optional[str]:
    """
    Load schedule model pipeline saved by train_model into global SCHEDULE_MODEL.
    Returns model path on success, None on failure.
    """
    global SCHEDULE_MODEL
    try:
        if Path(SCHEDULE_MODEL_PATH).exists():
            SCHEDULE_MODEL = joblib.load(SCHEDULE_MODEL_PATH)
            logger.info("Loaded schedule model from %s", SCHEDULE_MODEL_PATH)
            return str(SCHEDULE_MODEL_PATH)
        else:
            SCHEDULE_MODEL = None
            logger.info("No schedule model file found at %s", SCHEDULE_MODEL_PATH)
            return None
    except Exception as e:
        SCHEDULE_MODEL = None
        logger.exception("Failed to load schedule model: %s", e)
        return None


# load on startup (best-effort)
load_schedule_model()


# ---- JSON helpers ----
def _json_ok(payload: Dict[str, Any]):
    return jsonify(payload), 200


def _json_error(message: str, code: int = 500, details: Optional[str] = None):
    body: Dict[str, Any] = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), code


# ---- Health ----
@app.route("/api/health", methods=["GET"])
def health():
    return _json_ok({"status": "ok"})


# ---- Canvas endpoints ----
@app.route("/api/courses", methods=["GET"])
def route_get_courses():
    user_id = request.args.get("user_id", "self")
    try:
        courses = get_user_courses(user_id=user_id)
        return _json_ok({"courses": courses})
    except Exception as e:
        logger.exception("get_courses failed")
        return _json_error("Failed to fetch courses", 500, details=str(e))


@app.route("/api/assignments", methods=["GET"])
def route_get_assignments():
    course_id = request.args.get("course_id")
    if not course_id:
        return _json_error("Missing query parameter: course_id", 400)
    try:
        parsed = get_parsed_course_assignments(int(course_id), parse=True)
        return _json_ok({"assignments": parsed})
    except Exception as e:
        logger.exception("get_assignments failed")
        return _json_error("Failed to fetch parsed assignments", 500, details=str(e))


@app.route("/api/assignments/raw", methods=["GET"])
def route_get_assignments_raw():
    course_id = request.args.get("course_id")
    if not course_id:
        return _json_error("Missing query parameter: course_id", 400)
    try:
        raw = get_course_assignments(int(course_id))
        return _json_ok({"assignments_raw": raw})
    except Exception as e:
        logger.exception("get_assignments_raw failed")
        return _json_error("Failed to fetch raw assignments", 500, details=str(e))


@app.route("/api/assignment/<int:assignment_id>", methods=["GET"])
def route_get_assignment(assignment_id: int):
    course_id = request.args.get("course_id")
    if not course_id:
        return _json_error("Missing query parameter: course_id", 400)
    try:
        assignment = get_assignment(int(course_id), int(assignment_id))
        return _json_ok({"assignment": assignment})
    except Exception as e:
        logger.exception("get_assignment failed")
        return _json_error("Failed to fetch assignment", 500, details=str(e))


@app.route("/api/assignment/<int:assignment_id>/subs", methods=["GET"])
def route_get_assignment_submissions(assignment_id: int):
    course_id = request.args.get("course_id")
    if not course_id:
        return _json_error("Missing query parameter: course_id", 400)
    try:
        subs = get_assignment_submissions(int(course_id), int(assignment_id))
        return _json_ok({"submissions": subs})
    except Exception as e:
        logger.exception("get_assignment_submissions failed")
        return _json_error("Failed to fetch submissions", 500, details=str(e))


@app.route("/api/course/<int:course_id>/files", methods=["GET"])
def route_get_course_files(course_id: int):
    try:
        files = get_course_files(int(course_id))
        return _json_ok({"files": files})
    except Exception as e:
        logger.exception("get_course_files failed")
        return _json_error("Failed to fetch course files", 500, details=str(e))


@app.route("/api/parse_custom", methods=["POST"])
def route_parse_custom():
    body = request.get_json(silent=True)
    if not body or "assignments" not in body:
        return _json_error("Request JSON must contain 'assignments' field (list)", 400)
    raw_assignments = body["assignments"]
    try:
        parsed = [parse_canvas_assignment(a) for a in raw_assignments]
        summary_text = summarize_assignments(parsed)
        return _json_ok({"parsed": parsed, "summary": summary_text})
    except Exception as e:
        logger.exception("parse_custom failed")
        return _json_error("Failed to parse custom assignments", 500, details=str(e))


@app.route("/api/download_file", methods=["POST"])
def route_download_file():
    body = request.get_json(silent=True)
    if not body or "file_url" not in body:
        return _json_error("Request JSON must contain 'file_url'", 400)
    file_url = body["file_url"]
    dest_path = body.get("dest_path", "backend/tmp/downloaded_file")
    try:
        download_file(file_url, dest_path)
        return _json_ok({"downloaded_to": dest_path})
    except Exception as e:
        logger.exception("download_file failed")
        return _json_error("Failed to download file", 500, details=str(e))


# ---- RAG / LLM endpoints ----
@app.route("/api/ingest", methods=["POST"])
def route_ingest():
    """
    Trigger ingest pipeline (build / refresh vectorstore).
    JSON body (optional):
      { "source_dir": "...", "persist_dir": "...", "emb_model": "...", "chunk_size": 800, "chunk_overlap": 200 }
    """
    body = request.get_json(silent=True) or {}
    source_dir = body.get("source_dir", "backend/training_data")
    persist_dir = body.get("persist_dir", "backend/vectorstore")
    emb_model = body.get("emb_model", None)
    chunk_size = int(body.get("chunk_size", 800))
    chunk_overlap = int(body.get("chunk_overlap", 200))

    try:
        info = run_ingest(
            source_dir=source_dir,
            persist_dir=persist_dir,
            emb_model=emb_model or None,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return _json_ok({"ingest": info})
    except Exception as e:
        logger.exception("ingest failed")
        return _json_error("Ingest pipeline failed", 500, details=str(e))


@app.route("/api/qa", methods=["POST"])
def route_qa():
    """
    Run a RAG query. JSON body:
      { "question": "text", "top_k": 4, "model": "llama3", "return_sources": true }
    """
    body = request.get_json(silent=True)
    if not body or "question" not in body:
        return _json_error("Request JSON must contain 'question'", 400)

    question = body["question"]
    top_k = int(body.get("top_k", 4))
    model = body.get("model", "llama3")
    return_sources = bool(body.get("return_sources", True))

    try:
        out = query_rag(
            question=question,
            top_k=top_k,
            llm_model=model,
            return_sources=return_sources,
        )
        return _json_ok(out)
    except Exception as e:
        logger.exception("RAG query failed")
        tb = traceback.format_exc()
        return _json_error("RAG query failed", 500, details=tb)


# ---- Training endpoints ----
@app.route("/api/train", methods=["POST"])
def route_train():
    """
    Trigger model training pipeline (train_model.main).
    After training, train_model.main should persist the model and metrics into backend/models/.
    """
    try:
        # call training routine (synchronous)
        train_model.main()
        # reload model after training
        load_schedule_model()
        # return metrics if present
        metrics_fp = Path(MODELS_DIR) / "training_metrics.json"
        metrics = {}
        if metrics_fp.exists():
            try:
                metrics = json.loads(metrics_fp.read_text(encoding="utf-8"))
            except Exception:
                metrics = {}
        return _json_ok({"trained": True, "metrics": metrics})
    except Exception as e:
        logger.exception("train pipeline failed")
        tb = traceback.format_exc()
        return _json_error("Training pipeline failed", 500, details=tb)


@app.route("/api/reload_model", methods=["POST"])
def route_reload_model():
    try:
        model_path = load_schedule_model()
        if model_path is None:
            return _json_error("Model file not found or failed to load", 500)
        return _json_ok({"reloaded": True, "model_path": model_path})
    except Exception as e:
        logger.exception("reload_model failed")
        return _json_error("Failed to reload model", 500, details=str(e))


# ---- Prediction endpoint (uses loaded sklearn pipeline) ----
@app.route("/api/predict", methods=["POST"])
def route_predict():
    """
    Predict hours for a list of parsed assignments.
    Expected JSON:
    {
      "assignments": [
         { "assignment_id": "...", "assignment": "...", "course": "...", "weight": 10, "vle_count_total": 5, "past_avg_score": 78, "assessment_type": "Homework" },
         ...
      ]
    }
    Returns:
      { "predictions": [ {assignment_id, assignment, predicted_hours }, ... ] }
    """
    body = request.get_json(silent=True)
    if not body or "assignments" not in body:
        return _json_error("Request JSON must contain 'assignments' field (list)", 400)

    if SCHEDULE_MODEL is None:
        return _json_error("Schedule model not loaded. Train model first or call /api/reload_model.", 503)

    raw_assignments: List[Dict[str, Any]] = body["assignments"]
    rows: List[Dict[str, Any]] = []
    for a in raw_assignments:
        weight = a.get("weight", a.get("weight_percent", 0.0)) or 0.0
        vle = a.get("vle_count_total", a.get("vle_count", 0)) or 0
        past = a.get("past_avg_score", a.get("past_score", None))
        if past is None:
            past = a.get("student_past_avg", 50.0)
        assess_type = a.get("assessment_type", a.get("type", "unknown")) or "unknown"

        rows.append({
            "weight": float(weight),
            "vle_count_total": float(vle),
            "past_avg_score": float(past),
            "assessment_type": assess_type
        })

    import pandas as pd
    X = pd.DataFrame(rows)

    try:
        preds = SCHEDULE_MODEL.predict(X)  # pipeline handles preprocessing
    except Exception as e:
        logger.exception("Model prediction failed: %s", e)
        tb = traceback.format_exc()
        return _json_error("Model prediction failed", 500, details=tb)

    out = []
    for orig, p in zip(raw_assignments, preds):
        out.append({
            "assignment_id": orig.get("assignment_id") or orig.get("id") or orig.get("assignment"),
            "assignment": orig.get("assignment") or orig.get("name") or orig.get("assignment_name"),
            "predicted_hours": float(round(float(p), 2))
        })

    return _json_ok({"predictions": out})


# ---- Run server ----
if __name__ == "__main__":
    # For hackathon: debug on localhost. In production use gunicorn / waitress, and secure endpoints.
    app.run(host="127.0.0.1", port=5000, debug=True)
