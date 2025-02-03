from flask import Flask, request, jsonify
from flask_cors import CORS
import fitz  # PyMuPDF for PDF handling
import requests  # For Gemini API calls
from dotenv import load_dotenv
import os

app = Flask(__name__)
CORS(app)  # Allow frontend origin

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"  # Allow frontend origin
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DOCUMENT_TEXT = ""  # Global variable to store document text

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        return str(e)
    return text

def extract_text_from_txt(txt_path):
    """Reads text from a TXT file."""
    try:
        with open(txt_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        return str(e)

@app.route("/upload", methods=["POST"])
def upload_document():
    """Handles document upload and extracts text."""
    global DOCUMENT_TEXT
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file.mimetype not in ["application/pdf", "text/plain"]:
        return jsonify({"error": "Unsupported file format"}), 400

    if len(file.read()) > 10 * 1024 * 1024:  # 10MB limit
        return jsonify({"error": "File size exceeds the 10MB limit"}), 400
    
    file.seek(0)  # Reset file pointer after size check
    if file.filename.endswith(".pdf"):
        file_path = f"uploads/{file.filename}"
        file.save(file_path)
        DOCUMENT_TEXT = extract_text_from_pdf(file_path)
        os.remove(file_path)

    elif file.filename.endswith(".txt"):
        file_path = f"uploads/{file.filename}"
        file.save(file_path)
        DOCUMENT_TEXT = extract_text_from_txt(file_path)
        os.remove(file_path)

    print("Extracted Document Text:", DOCUMENT_TEXT[:1000])  # Print first 1000 characters for debugging
    return jsonify({"message": "Document uploaded successfully"}), 200




@app.route("/ask", methods=["POST"])
def ask_question():
    global DOCUMENT_TEXT
    if not DOCUMENT_TEXT:
        return jsonify({"error": "No document uploaded"}), 400

    data = request.get_json()
    question = data.get("question", "")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    prompt = f"Answer the question based on the following document:\n{DOCUMENT_TEXT}\n\nQuestion: {question}\nAnswer:"

    try:
        # Request to Gemini API
        response = requests.post(  
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
        )
        response.raise_for_status()  # Raise an exception for 4xx/5xx responses

        # Extract answer from the Gemini response
        gemini_response = response.json()
        answer = gemini_response.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No answer found.")
        print("Gemini response:", answer)  # Log the response for debugging
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True)


