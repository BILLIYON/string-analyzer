# app.py — String Analyzer Service (Stage 1 spec compliant)
# Run: python3 app.py
# Requirements: Flask, Flask_SQLAlchemy
# pip install Flask Flask-SQLAlchemy

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///strings.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# --- Model ---
class StringRecord(db.Model):
    __tablename__ = "strings"
    id = db.Column(db.String(64), primary_key=True)  # sha256 hex
    value = db.Column(db.Text, nullable=False, unique=True)  # store original case
    properties = db.Column(db.Text, nullable=False)  # JSON-encoded
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "value": self.value,
            "properties": json.loads(self.properties),
            "created_at": self.created_at.isoformat()
        }


# --- Utilities ---
def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def analyze_string(s: str) -> Dict[str, Any]:
    length = len(s)
    cleaned_for_palindrome = s.lower()
    is_pal = cleaned_for_palindrome == cleaned_for_palindrome[::-1]
    unique_characters = len(set(s))
    word_count = len(s.split())
    h = sha256_hex(s)
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    props = {
        "length": length,
        "is_palindrome": is_pal,
        "unique_characters": unique_characters,
        "word_count": word_count,
        "sha256_hash": h,
        "character_frequency_map": freq
    }
    return props


def get_by_value_case_insensitive(value: str) -> Optional[StringRecord]:
    # use SQL lower comparison to find existing string case-insensitively
    return StringRecord.query.filter(func.lower(StringRecord.value) == value.lower()).first()


# --- Natural language parser (basic heuristics) ---
def parse_nl_query(q: str) -> Tuple[Dict[str, Any], Optional[str]]:
    ql = q.lower().strip()
    filters = {}
    try:
        # single / one word
        if re.search(r"\b(single word|one word)\b", ql):
            filters["word_count"] = 1

        # palindrome
        if "palindrom" in ql:
            filters["is_palindrome"] = True

        # longer than N characters -> min_length = N+1 per spec example
        m = re.search(r"longer than (\d+)", ql)
        if m:
            n = int(m.group(1))
            filters["min_length"] = n + 1

        # strings longer than or equal -> min_length = n
        m2 = re.search(r"longer than or equal to (\d+)", ql)
        if m2:
            filters["min_length"] = int(m2.group(1))

        # specific "containing the letter z" or "containing the letter 'z'"
        m3 = re.search(r"containing the letter '?([a-zA-Z])'?", ql)
        if m3:
            filters["contains_character"] = m3.group(1).lower()
        else:
            # "contain the first vowel" heuristic -> choose 'a'
            if "first vowel" in ql:
                filters["contains_character"] = "a"

        # words like "strings containing the letter z"
        if "containing the letter" in ql and "contains_character" not in filters:
            # fallback: find any single letter mention
            m4 = re.search(r"letter\s+([a-z])", ql)
            if m4:
                filters["contains_character"] = m4.group(1).lower()

        # exact word count expressed directly (e.g., "word count 2")
        m_wc = re.search(r"word(?: |-)?count\s*(?:is|=)?\s*(\d+)", ql)
        if m_wc:
            filters["word_count"] = int(m_wc.group(1))

        if not filters:
            return {}, "Unable to parse natural language query."
        return filters, None
    except Exception as e:
        return {}, f"Parser error: {str(e)}"


# --- Filtering helper (applies parsed filters to all records) ---
def apply_filters_to_list(records, params: Dict[str, Any]):
    results = []
    for rec in records:
        props = json.loads(rec.properties)
        keep = True
        if "is_palindrome" in params and props.get("is_palindrome") != params["is_palindrome"]:
            keep = False
        if "min_length" in params and props.get("length", 0) < int(params["min_length"]):
            keep = False
        if "max_length" in params and props.get("length", 0) > int(params["max_length"]):
            keep = False
        if "word_count" in params and props.get("word_count") != int(params["word_count"]):
            keep = False
        if "contains_character" in params:
            ch = params["contains_character"].lower()
            if ch not in rec.value.lower():
                keep = False
        if keep:
            results.append(rec)
    return results


# --- Routes ---

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


# 1. Create/Analyze String - POST /strings
@app.route("/strings", methods=["POST"])
def create_string():
    if not request.is_json:
        return jsonify({"message": "Invalid request body (must be JSON)"}), 400
    data = request.get_json()
    if "value" not in data:
        return jsonify({"message": "Missing 'value' field"}), 400
    value = data["value"]
    if not isinstance(value, str):
        return jsonify({"message": "'value' must be a string"}), 422

    # Check duplicate (case-insensitive)
    existing = get_by_value_case_insensitive(value)
    if existing:
        return jsonify({"message": "String already exists"}), 409

    props = analyze_string(value)
    rec = StringRecord(id=props["sha256_hash"], value=value, properties=json.dumps(props),
                       created_at=datetime.now(timezone.utc))
    db.session.add(rec)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": "String already exists (conflict)"}), 409

    return jsonify(rec.to_dict()), 201


# 2. Get Specific String - GET /strings/{string_value}
# Using path converter to accept slashes/encoded characters if necessary
@app.route("/strings/<path:string_value>", methods=["GET"])
def get_string(string_value: str):
    rec = get_by_value_case_insensitive(string_value)
    if not rec:
        return jsonify({"message": "String not found"}), 404
    return jsonify(rec.to_dict()), 200


# 3. Get All Strings with Filtering - GET /strings
@app.route("/strings", methods=["GET"])
def list_strings():
    # parse query params
    params: Dict[str, Any] = {}
    if "is_palindrome" in request.args:
        v = request.args.get("is_palindrome")
        if v is None or v.lower() not in ("true", "false"):
            return jsonify({"message": "is_palindrome must be true or false"}), 400
        params["is_palindrome"] = True if v.lower() == "true" else False
    if "min_length" in request.args:
        try:
            params["min_length"] = int(request.args.get("min_length"))
        except Exception:
            return jsonify({"message": "min_length must be integer"}), 400
    if "max_length" in request.args:
        try:
            params["max_length"] = int(request.args.get("max_length"))
        except Exception:
            return jsonify({"message": "max_length must be integer"}), 400
    if "word_count" in request.args:
        try:
            params["word_count"] = int(request.args.get("word_count"))
        except Exception:
            return jsonify({"message": "word_count must be integer"}), 400
    if "contains_character" in request.args:
        ch = request.args.get("contains_character")
        if not ch or len(ch) != 1:
            return jsonify({"message": "contains_character must be a single character"}), 400
        params["contains_character"] = ch.lower()

    all_records = StringRecord.query.all()
    filtered = apply_filters_to_list(all_records, params)
    data = [r.to_dict() for r in filtered]
    return jsonify({"data": data, "count": len(data), "filters_applied": params}), 200


# 4. Natural Language Filtering - GET /strings/filter-by-natural-language?query=...
@app.route("/strings/filter-by-natural-language", methods=["GET"])
def filter_by_nl():
    q = request.args.get("query")
    if not q:
        return jsonify({"message": "query parameter is required"}), 400
    parsed, err = parse_nl_query(q)
    if err:
        return jsonify({"message": "Unable to parse natural language query", "error": err}), 400
    all_records = StringRecord.query.all()
    filtered = apply_filters_to_list(all_records, parsed)
    data = [r.to_dict() for r in filtered]
    return jsonify({
        "data": data,
        "count": len(data),
        "interpreted_query": {
            "original": q,
            "parsed_filters": parsed
        }
    }), 200


# 5. Delete String - DELETE /strings/{string_value}
@app.route("/strings/<path:string_value>", methods=["DELETE"])
def delete_string(string_value: str):
    rec = get_by_value_case_insensitive(string_value)
    if not rec:
        return jsonify({"message": "String not found"}), 404
    db.session.delete(rec)
    db.session.commit()
    # per spec 204 No Content, empty body
    return ("", 204)


# --- Initialize DB ---
def init_db():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
