# app.py
# Simple String Analyzer Service implementing Stage 1 spec
# Run: pip install -r requirements.txt
# Then: FLASK_APP=app.py flask run --host=0.0.0.0 --port=5000

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

from flask import Flask, request, jsonify, abort, make_response, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

# --- Config ---
APP_NAME = "String Analyzer Service"
DB_PATH = "sqlite:///strings.db"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- Models ---
class StringRecord(db.Model):
    __tablename__ = "strings"
    id = db.Column(db.String(64), primary_key=True)  # sha256 hex
    value = db.Column(db.Text, nullable=False, unique=True)
    properties = db.Column(db.Text, nullable=False)  # JSON string
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "value": self.value,
            "properties": json.loads(self.properties),
            "created_at": self.created_at.isoformat()
        }


# --- Utility functions ---
def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def analyze_string(s: str) -> Dict[str, Any]:
    length = len(s)
    cleaned = s.lower()
    is_pal = cleaned == cleaned[::-1]
    unique_characters = len(set(s))
    # word_count -> split on whitespace
    word_count = len(s.split())
    h = sha256_hex(s)
    # character frequency map - characters are taken as-is (case-sensitive)
    freq: Dict[str, int] = {}
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


def get_record_by_value(value: str) -> Optional[StringRecord]:
    return StringRecord.query.filter(func.lower(StringRecord.value) == value.lower()).first()


# --- Natural language parser (basic heuristics) ---
def parse_nl_query(q: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Try to parse simple natural-language queries into filters.
    Returns (filters_dict, error_message_or_None)
    Supports examples in spec:
      - "all single word palindromic strings" -> {"word_count": 1, "is_palindrome": True}
      - "strings longer than 10 characters" -> {"min_length": 11}
      - "palindromic strings that contain the first vowel" -> is_palindrome True, contains_character='a' (heuristic)
      - "strings containing the letter z" -> contains_character='z'
    This is heuristic-based; complex sentences may fail.
    """
    q_lower = q.lower().strip()
    filters: Dict[str, Any] = {}

    try:
        # single word
        if "single word" in q_lower or "one word" in q_lower:
            filters['word_count'] = 1

        # palindrome
        if "palindrom" in q_lower or "palindromic" in q_lower:
            filters['is_palindrome'] = True

        # longer than N characters
        import re
        m = re.search(r'longer than (\d+)', q_lower)
        if m:
            n = int(m.group(1))
            filters['min_length'] = n + 1

        m2 = re.search(r'longer than or equal to (\d+)', q_lower)
        if m2:
            n = int(m2.group(1))
            filters['min_length'] = n

        # strings longer than 10 characters -> interpreted as min_length 11 (spec example)
        m3 = re.search(r'longer than (\d+)\s*characters', q_lower)
        if m3:
            n = int(m3.group(1))
            filters['min_length'] = n + 1

        # exact word count mention: "word(s) = N" or "word count 2"
        m_wc = re.search(r'(\b|\D)word[s]?\s*(count)?\s*(is|=)?\s*(\d+)', q_lower)
        if m_wc:
            # get last capturing group
            n = int(m_wc.group(4))
            filters['word_count'] = n

        # containing the letter x / containing the letter 'z'
        m_char = re.search(r"containing the letter\s+'?([a-zA-Z])'?", q_lower)
        if m_char:
            filters['contains_character'] = m_char.group(1).lower()
        else:
            m_char2 = re.search(r"contain(?:s|ing)?\s+the\s+([a-zA-Z])\b", q_lower)
            if m_char2:
                filters['contains_character'] = m_char2.group(1).lower()
            # "contain the first vowel" heuristic
            if "first vowel" in q_lower:
                filters['contains_character'] = 'a'  # heuristic: choose 'a'

        # If nothing found, error
        if not filters:
            return {}, "Unable to parse natural language query."
        return filters, None
    except Exception as exc:
        return {}, f"Parser failed: {str(exc)}"


# --- Filtering helper ---
def apply_filters(query, params: Dict[str, Any]):
    # params: is_palindrome (bool), min_length, max_length, word_count, contains_character
    # We will filter in python after retrieving results for simplicity (data small).
    results = query.all()
    def keep(rec: StringRecord) -> bool:
        props = json.loads(rec.properties)
        if 'is_palindrome' in params and props.get('is_palindrome') != params['is_palindrome']:
            return False
        if 'min_length' in params and props.get('length', 0) < int(params['min_length']):
            return False
        if 'max_length' in params and props.get('length', 0) > int(params['max_length']):
            return False
        if 'word_count' in params and props.get('word_count') != int(params['word_count']):
            return False
        if 'contains_character' in params:
            ch = params['contains_character']
            # search case-insensitive
            if ch.lower() not in rec.value.lower():
                return False
        return True
    return [r for r in results if keep(r)]


# --- Routes ---

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": APP_NAME})


@app.route("/strings", methods=["POST"])
def create_string():
    if not request.is_json:
        return make_response(jsonify({"message": "Invalid request body (must be JSON)"}), 400)
    data = request.get_json()
    if 'value' not in data:
        return make_response(jsonify({"message": "Missing 'value' field"}), 400)
    if not isinstance(data['value'], str):
        return make_response(jsonify({"message": "'value' must be a string"}), 422)
    value: str = data['value']
    # compute props
    props = analyze_string(value)
    srchash = props['sha256_hash']

    # Check existence (case-insensitive)
    existing = get_record_by_value(value)
    if existing:
        return make_response(jsonify({"message": "String already exists"}), 409)

    rec = StringRecord(id=srchash, value=value, properties=json.dumps(props), created_at=datetime.now(timezone.utc))
    db.session.add(rec)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return make_response(jsonify({"message": "String already exists (hash conflict)"}), 409)

    resp = rec.to_dict()
    return make_response(jsonify(resp), 201)


@app.route("/strings/<path:string_value>", methods=["GET"])
def get_string(string_value: str):
    rec = get_record_by_value(string_value)
    if not rec:
        return make_response(jsonify({"message": "String not found"}), 404)
    return jsonify(rec.to_dict())


@app.route("/strings", methods=["GET"])
def list_strings():
    # Query params: is_palindrome, min_length, max_length, word_count, contains_character
    params: Dict[str, Any] = {}
    if 'is_palindrome' in request.args:
        v = request.args.get('is_palindrome').lower()
        if v not in ('true', 'false'):
            return make_response(jsonify({"message": "is_palindrome must be true or false"}), 400)
        params['is_palindrome'] = (v == 'true')
    for p in ('min_length', 'max_length', 'word_count'):
        if p in request.args:
            try:
                params[p] = int(request.args.get(p))
            except ValueError:
                return make_response(jsonify({"message": f"{p} must be an integer"}), 400)
    if 'contains_character' in request.args:
        ch = request.args.get('contains_character')
        if not ch or len(ch) != 1:
            return make_response(jsonify({"message": "contains_character must be a single character"}), 400)
        params['contains_character'] = ch.lower()

    query = StringRecord.query
    filtered = apply_filters(query, params)
    data = [r.to_dict() for r in filtered]
    return jsonify({
        "data": data,
        "count": len(data),
        "filters_applied": params
    })


@app.route("/strings/filter-by-natural-language", methods=["GET"])
def filter_by_nl():
    q = request.args.get('query')
    if not q:
        return make_response(jsonify({"message": "query parameter is required"}), 400)
    parsed, err = parse_nl_query(q)
    if err:
        return make_response(jsonify({"message": "Unable to parse natural language query", "error": err}), 400)
    # Now apply parsed filters
    query = StringRecord.query
    filtered = apply_filters(query, parsed)
    data = [r.to_dict() for r in filtered]
    return jsonify({
        "data": data,
        "count": len(data),
        "interpreted_query": {
            "original": q,
            "parsed_filters": parsed
        }
    })


@app.route("/strings/<path:string_value>", methods=["DELETE"])
def delete_string(string_value: str):
    rec = get_record_by_value(string_value)
    if not rec:
        return make_response(jsonify({"message": "String not found"}), 404)
    db.session.delete(rec)
    db.session.commit()
    return ("", 204)


# --- Initialize DB helper ---
def init_db():
    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
