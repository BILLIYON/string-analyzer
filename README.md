## 🧠 String Analyzer API  
A RESTful Flask API that analyzes strings and stores their computed properties.  
Built as part of **Backend Wizards — Stage 1 Task**.

---

## 🚀 Features
For each analyzed string, the API computes and stores:
- **length** → Number of characters in the string  
- **is_palindrome** → True if the string reads the same backward (case-insensitive)  
- **unique_characters** → Count of distinct characters  
- **word_count** → Number of words separated by whitespace  
- **sha256_hash** → Unique SHA-256 hash of the string  
- **character_frequency_map** → Dictionary of each character and its frequency  

---

## 🧩 Endpoints

### 1️⃣ Create / Analyze String
**POST** `/strings`

**Request Body:**
```json
{
  "value": "madam"
}
````

**Success Response (201):**

```json
{
  "id": "sha256_hash_value",
  "value": "madam",
  "properties": {
    "length": 5,
    "is_palindrome": true,
    "unique_characters": 3,
    "word_count": 1,
    "sha256_hash": "abc123...",
    "character_frequency_map": {
      "m": 2,
      "a": 2,
      "d": 1
    }
  },
  "created_at": "2025-10-22T12:00:00Z"
}
```

---

### 2️⃣ Get Specific String

**GET** `/strings/{string_value}`
Example:

```
GET /strings/madam
```

**Response (200):**

```json
{
  "id": "sha256_hash_value",
  "value": "madam",
  "properties": { ... },
  "created_at": "2025-10-22T12:00:00Z"
}
```

---

### 3️⃣ (Coming Soon)

* `GET /strings` → Filter and list all stored strings
* `GET /strings/filter-by-natural-language?query=...` → Search using natural language
* `DELETE /strings/{string_value}` → Delete a stored string

---

## ⚙️ Installation and Setup (Local)

### Requirements

* Python 3.8+
* Flask

### Steps

1. **Clone the repository**

   ```bash
   git clone https://github.com/<your-username>/string-analyzer.git
   cd string-analyzer
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   venv\Scripts\activate   # For Windows
   # OR
   source venv/bin/activate  # For Linux/Mac
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**

   ```bash
   python app.py
   ```

5. **Test locally**
   Open Postman or your browser:

   ```
   http://127.0.0.1:5000/strings
   ```

---

## ☁️ Deploying to AWS EC2 (Ubuntu)

1. **SSH into your instance**

   ```bash
   ssh -i "your-key.pem" ubuntu@<EC2-public-IP>
   ```

2. **Install dependencies**

   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install python3-pip python3-venv git -y
   ```

3. **Clone your repo**

   ```bash
   git clone https://github.com/<your-username>/string-analyzer.git
   cd string-analyzer
   ```

4. **Set up and run**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python3 app.py
   ```

5. **Access the API**

   ```
   http://<EC2-public-IP>:5000
   ```

---

## 🧪 Example Test (cURL)

```bash
curl -X POST http://127.0.0.1:5000/strings \
     -H "Content-Type: application/json" \
     -d '{"value": "racecar"}'
```

---

## 🧰 Tech Stack

* **Language:** Python
* **Framework:** Flask
* **Deployment:** AWS EC2 (Ubuntu)
* **Hashing:** hashlib (SHA-256)

---

## 👨‍💻 Author

**John Abioye (John Billon)**
Backend Wizards — Stage 1
📧 Email: [your.email@example.com](mailto:your.email@example.com)
🌐 GitHub: [@your-username](https://github.com/your-username)
