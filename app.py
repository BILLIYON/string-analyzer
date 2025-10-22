from flask import Flask, request, jsonify
import hashlib
from datetime import datetime

app = Flask(__name__)
strings_db = {}

def analyze_string(value):
    value_clean = value.lower().replace(" ", "")
    return {
        "length": len(value),
        "is_palindrome": value_clean == value_clean[::-1],
        "unique_characters": len(set(value)),
        "word_count": len(value.split()),
        "sha256_hash": hashlib.sha256(value.encode()).hexdigest(),
        "character_frequency_map": {ch: value.count(ch) for ch in set(value)}
    }

@app.route('/strings', methods=['POST'])
def create_string():
    data = request.get_json()
    if not data or "value" not in data:
        return jsonify({"error": "Missing 'value' field"}), 400
    value = data["value"]
    if not isinstance(value, str):
        return jsonify({"error": "'value' must be a string"}), 422
    
    sha_hash = hashlib.sha256(value.encode()).hexdigest()
    if sha_hash in strings_db:
        return jsonify({"error": "String already exists"}), 409

    properties = analyze_string(value)
    strings_db[sha_hash] = {
        "id": sha_hash,
        "value": value,
        "properties": properties,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    return jsonify(strings_db[sha_hash]), 201

@app.route('/strings/<string_value>', methods=['GET'])
def get_string(string_value):
    for s in strings_db.values():
        if s["value"] == string_value:
            return jsonify(s), 200
    return jsonify({"error": "String not found"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
