# backend/utils/canvas_requests.py
"""
Canvas API helper utilities.

Environment variables (put in backend/.env):
- CANVAS_BASE_URL   e.g. https://canvas.instructure.com (no trailing '/')
- CANVAS_API_TOKEN  your Canvas personal access token

Functions:
- get_user_courses(user_id='self') -> list
- get_course_assignments(course_id, params=None) -> list
- get_assignment(course_id, assignment_id) -> dict
- get_course_files(course_id, params=None) -> list
- get_assignment_submissions(course_id, assignment_id, params=None) -> list

These functions return parsed JSON (Python dict/list) or raise an Exception on HTTP errors.
"""

import os
import math
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, parse_qs, urlparse

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()  # load .env from backend/

CANVAS_BASE_URL = os.getenv("CANVAS_BASE_URL")
CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN")

if not CANVAS_BASE_URL or not CANVAS_API_TOKEN:
    raise EnvironmentError(
        "Missing CANVAS_BASE_URL or CANVAS_API_TOKEN in environment. "
        "Add them to your .env file in the backend folder."
    )

# Create a session with retries and default headers
_session = requests.Session()
_session.headers.update(
    {
        "Authorization": f"Bearer {CANVAS_API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "CanvasHelper/1.0",
    }
)

# Retry strategy for transient errors / rate limiting
_retry_strategy = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"]),
)
_adapter = HTTPAdapter(max_retries=_retry_strategy)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)


def _raise_for_status(resp: requests.Response) -> None:
    if not resp.ok:
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        raise RuntimeError(f"Canvas API error {resp.status_code}: {body}")


def _parse_link_header(link_header: str) -> Dict[str, str]:
    """
    Parse RFC5988 Link header into a dict of rel->url.
    Example:
      Link: <https://...&page=2>; rel="next", <...&page=10>; rel="last"
    """
    links: Dict[str, str] = {}
    if not link_header:
        return links
    parts = link_header.split(",")
    for p in parts:
        if ";" not in p:
            continue
        url_part, rel_part = p.split(";", 1)
        url = url_part.strip().strip("<>").strip()
        rel = rel_part.strip().split("=")[-1].strip('"')
        links[rel] = url
    return links


def _get_paginated(endpoint: str, params: Optional[Dict[str, Any]] = None) -> List[Any]:
    """
    GET helper that follows Canvas pagination (Link headers) and returns concatenated results.
    """
    url = urljoin(CANVAS_BASE_URL + "/", endpoint.lstrip("/"))
    params = params.copy() if params else {}
    # Canvas default per_page is small, set a high per_page but still use pagination defensively
    params.setdefault("per_page", 100)
    results: List[Any] = []

    while url:
        resp = _session.get(url, params=params, timeout=30)
        _raise_for_status(resp)
        try:
            page_json = resp.json()
        except ValueError:
            # non-json response
            raise RuntimeError("Canvas returned non-JSON response")
        # If the endpoint returns an object (e.g., single page result), append directly
        if isinstance(page_json, list):
            results.extend(page_json)
        else:
            # Some Canvas endpoints return dicts (not lists). For consistency, append the dict.
            results.append(page_json)

        link_header = resp.headers.get("Link") or resp.headers.get("link")
        if not link_header:
            break
        links = _parse_link_header(link_header)
        next_url = links.get("next")
        if next_url:
            # subsequent pages: reset params (Canvas encodes them into the next_url)
            url = next_url
            params = None
        else:
            break

    return results


# Public helper functions ---------------------------------------------------


def get_user_courses(user_id: str = "self") -> List[Dict[str, Any]]:
    """
    Get list of courses for a user. Use 'self' for the token owner.
    Returns a list of course dicts.
    """
    endpoint = f"/api/v1/users/{user_id}/courses"
    return _get_paginated(endpoint, params={"per_page": 100})


def get_course_assignments(course_id: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Get all assignments for a given course_id (handles pagination).
    params: optional dict for Canvas query params (e.g., {"include[]": "submission"}).
    """
    endpoint = f"/api/v1/courses/{course_id}/assignments"
    return _get_paginated(endpoint, params=params)


def get_assignment(course_id: int, assignment_id: int) -> Dict[str, Any]:
    """
    Get a single assignment for a course.
    """
    endpoint = f"/api/v1/courses/{course_id}/assignments/{assignment_id}"
    url = urljoin(CANVAS_BASE_URL + "/", endpoint.lstrip("/"))
    resp = _session.get(url, timeout=30)
    _raise_for_status(resp)
    return resp.json()


def get_course_files(course_id: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    List files for a course (course-level files), paginated.
    """
    endpoint = f"/api/v1/courses/{course_id}/files"
    return _get_paginated(endpoint, params=params)


def get_assignment_submissions(course_id: int, assignment_id: int, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Get submissions for a particular assignment (may be large).
    """
    endpoint = f"/api/v1/courses/{course_id}/assignments/{assignment_id}/submissions"
    return _get_paginated(endpoint, params=params)


def download_file(file_url: str, dest_path: str) -> None:
    """
    Download a file (Canvas file url). The file_url is usually an absolute URL returned
    in the 'url' field of a file object from the API. Writes to dest_path.
    """
    resp = _session.get(file_url, stream=True, timeout=60)
    _raise_for_status(resp)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)


# Convenience: fetch assignments and optionally parse them using your canvas_parser
def get_parsed_course_assignments(course_id: int, parse: bool = True) -> List[Dict[str, Any]]:
    """
    Fetch assignments for a course and optionally run the parser (utils.canvas_parser.parse_canvas_assignment)
    to standardize fields. Returns list of parsed dicts if parse=True, else raw JSON list.
    """
    raw = get_course_assignments(course_id)
    if not parse:
        return raw

    try:
        # local import to avoid circular import issues
        from .canvas_parser import parse_canvas_assignment
    except Exception:
        # try absolute import (if utils is package)
        try:
            from utils.canvas_parser import parse_canvas_assignment  # type: ignore
        except Exception:
            raise RuntimeError("Could not import parse_canvas_assignment from utils.canvas_parser")

    parsed = [parse_canvas_assignment(a) for a in raw]
    return parsed
