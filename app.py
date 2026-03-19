import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = "supersecretkey"

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024 # 50MB max upload

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'document' not in request.files:
        return jsonify({"error": "No document provided"}), 400
    
    file = request.files['document']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
        
    if file and file.filename.endswith('.pdf'):
        original_name = secure_filename(file.filename)
        filename = f"{uuid.uuid4().hex}_{original_name}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
            import rag_engine
            chunks = rag_engine.process_pdf(filepath)
            
            # Safe to auto-delete since Endee has the vector data
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
                
            return jsonify({
                "message": "File uploaded and indexed successfully", 
                "chunks_processed": chunks,
                "filename": filename
            })
        except Exception as e:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            return jsonify({"error": str(e)}), 400
    
    return jsonify({"error": "Invalid file format. Please upload a PDF."}), 400

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or 'query' not in data or 'filename' not in data:
        return jsonify({"error": "No query or filename provided"}), 400
    
    user_query = data['query']
    filename = data['filename']
    
    try:
        import rag_engine
        answer = rag_engine.query_pdf(user_query, filename)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    if 'document' not in request.files:
        return jsonify({"error": "No document provided"}), 400
    
    file = request.files['document']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
        
    if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
            import csv_engine
            stats = csv_engine.process_csv(filepath)
            return jsonify({
                "message": "CSV uploaded and analyzed successfully", 
                "stats": stats,
                "filename": filename
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    return jsonify({"error": "Invalid file format. Please upload a .csv or .xlsx file."}), 400

@app.route('/api/chat-csv', methods=['POST'])
def chat_csv():
    data = request.json
    if not data or 'query' not in data or 'filename' not in data:
        return jsonify({"error": "Missing query or filename"}), 400
        
    user_query = data['query']
    filename = secure_filename(data['filename'])
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(filepath):
         return jsonify({"error": "File not found on server. Please re-upload."}), 404
    
    try:
        import csv_engine
        answer = csv_engine.query_csv(user_query, filepath)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/recommendations', methods=['POST'])
def recommendations():
    data = request.json
    if not data or 'filename' not in data:
        return jsonify({"questions": []}), 200

    filename = data['filename']
    mode = data.get('mode', 'pdf')

    try:
        if mode == 'csv':
            import csv_engine
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
            if os.path.exists(filepath):
                questions = csv_engine.get_csv_recommendations(filepath)
                return jsonify({"questions": questions})
        # For PDF and URL modes, return empty (no recommendations logic yet)
        return jsonify({"questions": []})
    except Exception:
        return jsonify({"questions": []})

# ─── URL SCRAPER ENDPOINTS ───────────────────────────────────────────────────

# In-memory store for scraped page context (keyed by session token)
_url_sessions = {}

@app.route('/api/scrape-url', methods=['POST'])
def scrape_url():
    data = request.json
    if not data or 'url' not in data:
        return jsonify({"error": "No URL provided"}), 400

    try:
        raw_url = data['url'].strip()
        if not raw_url.startswith(('http://', 'https://')):
            raw_url = 'https://' + raw_url

        import url_engine
        result = url_engine.scrape_url(raw_url)
        # Store scraped content in memory with the URL as key
        _url_sessions[raw_url] = result
        return jsonify({
            "message": "Page scraped successfully",
            "title": result['title'],
            "word_count": result['word_count'],
            "filename": raw_url   # reuse 'filename' field so frontend stays consistent
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 400


@app.route('/api/chat-url', methods=['POST'])
def chat_url():
    data = request.json
    if not data or 'query' not in data or 'filename' not in data:
        return jsonify({"error": "Missing query or URL"}), 400

    user_query = data['query']
    page_url   = data['filename']   # frontend sends 'filename' = url

    session = _url_sessions.get(page_url)
    if not session:
        return jsonify({"error": "Page session expired. Please re-submit the URL."}), 404

    try:
        import url_engine
        answer = url_engine.query_url(
            user_query,
            session['text'],
            session['title'],
            session['url']
        )
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    # Use the PORT environment variable provided by Render, default to 5000 for local dev
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
