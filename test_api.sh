#!/usr/bin/env bash
# test_api.sh — Local test suite for your Flask String Analyzer API
# Make sure your app is running first:
#   flask run --host=0.0.0.0 --port=5000
# Run this script in another terminal:
#   bash test_api.sh

BASE_URL="http://127.0.0.1:5000"

echo "=== 🩺 HEALTH CHECK ==="
curl -i $BASE_URL/health
echo -e "\n"

echo "=== 🆕 TEST: POST valid string (expect 201) ==="
curl -i -X POST $BASE_URL/strings \
     -H "Content-Type: application/json" \
     -d '{"value": "madam"}'
echo -e "\n"

echo "=== 🔁 TEST: Duplicate string (expect 409) ==="
curl -i -X POST $BASE_URL/strings \
     -H "Content-Type: application/json" \
     -d '{"value": "madam"}'
echo -e "\n"

echo "=== ⚠️ TEST: Missing value field (expect 400) ==="
curl -i -X POST $BASE_URL/strings \
     -H "Content-Type: application/json" \
     -d '{}'
echo -e "\n"

echo "=== 🚫 TEST: Invalid data type (expect 422) ==="
curl -i -X POST $BASE_URL/strings \
     -H "Content-Type: application/json" \
     -d '{"value": 1234}'
echo -e "\n"

echo "=== 🔍 TEST: Get existing string (expect 200) ==="
curl -i $BASE_URL/strings/madam
echo -e "\n"

echo "=== 🔎 TEST: Get non-existing string (expect 404) ==="
curl -i $BASE_URL/strings/nonexistent
echo -e "\n"

echo "=== 🧹 TEST: Delete existing string (expect 204) ==="
curl -i -X DELETE $BASE_URL/strings/madam
echo -e "\n"

echo "=== ❌ TEST: Delete non-existing string (expect 404) ==="
curl -i -X DELETE $BASE_URL/strings/madam
echo -e "\n"

echo "=== 🧮 TEST: Filter (expect 200) ==="
curl -i "$BASE_URL/strings?is_palindrome=false&min_length=3"
echo -e "\n"

echo "=== 🗣️ TEST: Natural language filter (expect 200) ==="
curl -i "$BASE_URL/strings/filter-by-natural-language?query=strings%20longer%20than%205%20characters"
echo -e "\n"

echo "✅ All test calls executed. Review the status codes above."
