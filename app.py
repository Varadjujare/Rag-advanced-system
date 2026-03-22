import os
import sys
import traceback
import uuid
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

os.environ["GOOGLE_API_CORE_SUPPRESS_PYTHON_VERSION_WARNING"] = "1"

print("--- FLASK BOOTING ---", file=sys.stderr)

import rag_engine
import csv_engine
import url_engine

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

try:
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
except:
    pass

@app.errorhandler(Exception)
def handle_exception(e):
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return e
    tb = traceback.format_exc()
    print(f"CRITICAL ERROR: {tb}", file=sys.stderr)
    return f"<h1>Diagnostic Error</h1><pre>{tb}</pre>", 500

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    file = request.files.get('document')
    if not file or not file.filename.endswith('.pdf'):
        return jsonify({"error": "Invalid file"}), 400

    filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        file.save(filepath)
        chunks = rag_engine.process_pdf(filepath)
        os.remove(filepath)
        return jsonify({"message": "Success", "chunks_processed": chunks, "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    try:
        answer = rag_engine.query_pdf(data['query'], data['filename'])
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    file = request.files.get('document')
    if not file:
        return jsonify({"error": "No file"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        file.save(filepath)
        stats = csv_engine.process_csv(filepath)
        return jsonify({"message": "Success", "stats": stats, "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/chat-csv', methods=['POST'])
def chat_csv():
    data = request.json
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(data['filename']))
    try:
        answer = csv_engine.query_csv(data['query'], filepath)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/recommendations', methods=['POST'])
def recommendations():
    data = request.json
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(data['filename']))
        questions = csv_engine.get_csv_recommendations(filepath)
        return jsonify({"questions": questions})
    except:
        return jsonify({"questions": []})

_url_sessions = {}

@app.route('/api/scrape-url', methods=['POST'])
def scrape_url():
    data = request.json
    raw_url = data['url'].strip()

    if not raw_url.startswith(('http://', 'https://')):
        raw_url = 'https://' + raw_url

    try:
        result = url_engine.scrape_url(raw_url)
        _url_sessions[raw_url] = result

        return jsonify({
            "message": "Success",
            "title": result['title'],
            "filename": raw_url,
            "word_count": result.get("word_count", 0)   # ✅ FIX
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/chat-url', methods=['POST'])
def chat_url():
    data = request.json
    session = _url_sessions.get(data['filename'])

    if not session:
        return jsonify({"error": "Expired"}), 404

    try:
        answer = url_engine.query_url(
            data['query'],
            session['text'],
            session['title'],
            session['url']
        )
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

print("--- FLASK READY ---", file=sys.stderr)