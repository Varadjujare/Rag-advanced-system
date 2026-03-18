import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import rag_engine
import csv_engine
import url_engine

app = Flask(__name__)
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
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            chunks = rag_engine.process_pdf(filepath)
            
            # Safe to auto-delete since Endee has the vector data
            if os.path.exists(filepath):
                os.remove(filepath)
                
            return jsonify({
                "message": "File uploaded and indexed successfully", 
                "chunks_processed": chunks
            })
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Invalid file format. Please upload a PDF."}), 400

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "No query provided"}), 400
        
    user_query = data['query']
    
    try:
        answer = rag_engine.query_pdf(user_query)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        file.save(filepath)
        
        try:
            stats = csv_engine.process_csv(filepath)
            return jsonify({
                "message": "CSV uploaded and analyzed successfully", 
                "stats": stats,
                "filename": filename
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
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
        answer = csv_engine.query_csv(user_query, filepath)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── URL SCRAPER ENDPOINTS ───────────────────────────────────────────────────

# In-memory store for scraped page context (keyed by session token)
_url_sessions = {}

@app.route('/api/scrape-url', methods=['POST'])
def scrape_url():
    data = request.json
    if not data or 'url' not in data:
        return jsonify({"error": "No URL provided"}), 400

    raw_url = data['url'].strip()
    if not raw_url.startswith(('http://', 'https://')):
        raw_url = 'https://' + raw_url

    try:
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
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500


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
        answer = url_engine.query_url(
            user_query,
            session['text'],
            session['title'],
            session['url']
        )
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
