import requests
import json
from flask import Flask, request, jsonify, send_from_directory, make_response, Response
from flask_cors import CORS
import os
import io
import base64
from dotenv import load_dotenv
from openai import OpenAI
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF for image extraction
import urllib.parse
from datetime import datetime, date, time
import re
from functools import wraps
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
from google.oauth2 import id_token

# Load environment variables
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')

# Debug: Print first 200 chars of the env var to verify content
print("[DEBUG] FIREBASE_SERVICE_ACCOUNT_JSON (first 200 chars):", (service_account_json or '')[:200])

if not service_account_json:
    raise ValueError("Environment variable FIREBASE_SERVICE_ACCOUNT_JSON not set")

# Parse JSON string into a dict
cred_dict = json.loads(service_account_json)

# Initialize Firebase Admin with Cloud Storage bucket
if not firebase_admin._apps:
    firebase_admin.initialize_app(
        credentials.Certificate(cred_dict),
        {'storageBucket': os.environ.get('FIREBASE_STORAGE_BUCKET', 'liftoff.appspot.com')}
    )
print("[DEBUG] Using Firebase Storage bucket:", os.environ.get('FIREBASE_STORAGE_BUCKET'))
db = firestore.client()
bucket = storage.bucket()

app = Flask(__name__)
CORS(app)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================================================
# SUBSCRIPTION & USAGE TRACKING SYSTEM
# ============================================================================

SUBSCRIPTION_LIMITS = {
    'free': {
        'note_generations': 1,
        'note_regenerations': 2,
        'tests': 2,
        'flashcards': 3,
        'flowcharts': 2,
        'flowchart_regenerations': 1,
        'aviator_messages': 10,
        'advanced_mode': False,
        'all_themes': False,
        'no_ads': False
    },
    'pro': {
        'note_generations': 15,
        'note_regenerations': 50,
        'tests': 30,
        'flashcards': 20,
        'flowcharts': 20,
        'flowchart_regenerations': 50,
        'aviator_messages': float('inf'),
        'advanced_mode': True,
        'all_themes': True,
        'no_ads': True
    },
    'ultra': {
        'note_generations': float('inf'),
        'note_regenerations': float('inf'),
        'tests': float('inf'),
        'flashcards': float('inf'),
        'flowcharts': float('inf'),
        'flowchart_regenerations': float('inf'),
        'aviator_messages': float('inf'),
        'advanced_mode': True,
        'all_themes': True,
        'no_ads': True
    }
}

# In-memory usage tracking (use a file for persistence in production)
usage_tracker = {}

def get_user_tier_from_request():
    """Get subscription tier from request headers"""
    tier = request.headers.get('X-User-Tier', 'free').lower()
    if tier not in SUBSCRIPTION_LIMITS:
        tier = 'free'
    return tier

def get_or_create_user_id():
    """Get user ID from headers or create a session ID"""
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        # Fall back to IP + User-Agent for anonymous users
        user_id = f"{request.remote_addr}_{hash(request.headers.get('User-Agent', ''))}"
    return user_id

def get_usage_key(user_id, feature):
    """Get the usage tracking key for a user and feature"""
    today = date.today().isoformat()
    return f"{user_id}_{feature}_{today}"

def increment_usage(user_id, feature):
    """Increment usage count for a feature"""
    key = get_usage_key(user_id, feature)
    if key not in usage_tracker:
        usage_tracker[key] = 0
    usage_tracker[key] += 1
    return usage_tracker[key]

def get_usage_count(user_id, feature):
    """Get current usage count for a feature"""
    key = get_usage_key(user_id, feature)
    return usage_tracker.get(key, 0)

def check_limit(user_id, tier, feature):
    """
    Check if user has reached their limit for a feature
    Returns: (allowed, remaining, limit)
    """
    limit = SUBSCRIPTION_LIMITS[tier].get(feature, 0)
    usage = get_usage_count(user_id, feature)
    
    if limit == float('inf'):
        return True, float('inf'), float('inf')
    
    allowed = usage < limit
    remaining = max(0, limit - usage)
    return allowed, remaining, limit

def require_subscription(feature):
    """Decorator to check subscription limits before executing endpoint"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = get_or_create_user_id()
            tier = get_user_tier_from_request()
            
            allowed, remaining, limit = check_limit(user_id, tier, feature)
            
            if not allowed:
                return jsonify({
                    "error": f"Daily limit reached for {feature.replace('_', ' ')}",
                    "tier": tier,
                    "limit": limit if limit != float('inf') else "Unlimited",
                    "feature": feature
                }), 429  # Too Many Requests
            
            # Increment usage
            increment_usage(user_id, feature)
            
            # Store tier info in request for later use
            request.user_tier = tier
            request.user_id = user_id
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ============================================================================
# HTML FILE SERVING (with proper UTF-8 encoding)
# ============================================================================
@app.route('/')
@app.route('/dashboard')
@app.route('/dashboard.html')
def serve_dashboard():
    print("BASE_DIR:", BASE_DIR)
    print("Looking for:", os.path.join(BASE_DIR, 'dashboard.html'))    
    return serve_html('dashboard.html')

@app.route('/flowchart.html')
def serve_flowchart():
    return serve_html('flowchart.html')

@app.route('/tests.html')
def serve_tests():
    return serve_html('tests.html')

@app.route('/pdf-to-notes.html')
def serve_pdf_notes():
    return serve_html('pdf-to-notes.html')

@app.route('/aviator.html')
def serve_aviator():
    return serve_html('aviator.html')

@app.route('/flashcards.html')
def serve_flashcards():
    return serve_html('flashcards.html')

@app.route('/login.html')
def serve_login():
    return serve_html('login.html')

@app.route('/signup.html')
def serve_signup():
    return serve_html('signup.html')
@app.route("/debug-files")
def debug_files():
    return jsonify(os.listdir(BASE_DIR))

def serve_html(filename):
    """Serve HTML files with proper UTF-8 encoding"""
    try:
        file_path = os.path.join(BASE_DIR, filename)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        response = make_response(content)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    except FileNotFoundError:
        return jsonify({"error": f"{filename} not found"}), 404

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files (CSS, JS, images, etc)"""
    if os.path.exists(filename):
        response = send_from_directory('.', filename)
        # Prevent caching for all static files
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    return jsonify({"error": f"{filename} not found"}), 404

# Data directory for user files
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


def check_pdf_quality(text, min_words=30, min_word_ratio=0.4):
    """
    Check if extracted PDF text is readable enough to generate content from.
    Returns (is_ok: bool, reason: str)
    
    Checks:
    1. Minimum word count
    2. Ratio of real English words (>=2 chars, mostly alpha) vs garbage tokens
    3. Average word length sanity (garbage OCR produces very short or very long tokens)
    """
    if not text or not text.strip():
        return False, "The PDF appears to be empty or contains no extractable text. It may be a scanned image without OCR."
    
    words = text.split()
    if len(words) < min_words:
        return False, f"The PDF contains too little readable text ({len(words)} words found). The content may be handwritten, a scanned image, or in a language we can't process."
    
    # Count "real" words: at least 2 chars, mostly alphabetic
    real_words = 0
    for w in words:
        cleaned = ''.join(c for c in w if c.isalpha())
        if len(cleaned) >= 2:
            real_words += 1
    
    ratio = real_words / len(words) if words else 0
    if ratio < min_word_ratio:
        return False, "The PDF text quality is too low — most of the content couldn't be read clearly. This may be due to poor handwriting, low scan quality, or image-based content without proper text."
    
    # Average word length check (garbage tends to be very short fragments)
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len < 2.0:
        return False, "The PDF content appears to be fragmented or corrupted. Please try a clearer version of the document."
    
    return True, "OK"

def get_current_user_id():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    token = auth_header.split("Bearer ")[-1]

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            grequests.Request(),
            os.getenv("GOOGLE_CLIENT_ID") 
        )

        return idinfo["sub"]

    except Exception as e:
        print("Token verification failed:", e)
        return None
#=========================================================
# PDF MANAGEMENT ROUTES
# ============================================================================
@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    user_id = get_current_user_id()
    print("Upload PDF request from user:", user_id)
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file provided"}), 400
    
    file = request.files['pdf']
    pdf_name = request.form.get('pdf_name', file.filename)

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    try:
        # Read bytes for processing
        file_bytes = file.read()
        file.seek(0)

        # Extract text & images
        pdf_text = extract_pdf_text(file)
        extracted_images = extract_pdf_images(file_bytes)
        chunks = chunk_text(pdf_text)

        # Upload PDF to Firebase Storage
        blob = bucket.blob(f'users/{user_id}/pdfs/{pdf_name}')
        blob.upload_from_string(file_bytes, content_type='application/pdf')
        # Optional: get public URL
        file_url = blob.generate_signed_url(expiration=3600*24*7)  # 7-day signed URL

        # Save metadata to Firestore
        pdf_ref = db.collection('users').document(user_id).collection('pdfs').document(pdf_name)
        pdf_ref.set({
            "filename": file.filename,
            "pdfText": pdf_text,
            "chunks": chunks,
            "images": extracted_images,
            "storagePath": f'users/{user_id}/pdfs/{pdf_name}',
            "fileUrl": file_url,
            "uploadedAt": firestore.SERVER_TIMESTAMP
        })

        return jsonify({
            "success": True,
            "pdf_name": pdf_name,
            "image_count": len(extracted_images),
            "message": f"PDF '{pdf_name}' uploaded successfully for user '{user_id}'"
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-notes', methods=['POST'])
@require_subscription('note_generations')
def generate_notes():
    data = request.json
    pdf_name = data.get('pdf_name')
    level = data.get('level', 'beginner')
    user_id = get_current_user_id()

    if not pdf_name:
        return jsonify({"error": "Missing pdf_name"}), 400
    print("USER:", user_id)
    print("PDF:", pdf_name)
    try:
        # 🔥 Fetch from Firestore
        pdf_ref = db.collection('users').document(user_id).collection('pdfs').document(pdf_name)
        pdf_doc = pdf_ref.get()

        if not pdf_doc.exists:
            return jsonify({"error": f"PDF '{pdf_name}' not found"}), 404

        pdf_data = pdf_doc.to_dict()
        pdf_content = pdf_data.get("pdfText", "")
        images = pdf_data.get("images", [])

        # ── Quality check ──
        is_ok, reason = check_pdf_quality(pdf_content)
        if not is_ok:
            return jsonify({"error": reason}), 400

        num_images = len(images)
        content_length = len(pdf_content)

        # Split content into chunks
        CHUNK_SIZE = 4000
        chunks = [pdf_content[i:i + CHUNK_SIZE] for i in range(0, content_length, CHUNK_SIZE)]

        if len(chunks) > 15:
            step = len(chunks) / 15
            chunks = [chunks[int(i * step)] for i in range(15)]

        num_chunks = len(chunks)
        print(f"📄 PDF has {content_length} chars, split into {num_chunks} chunks")

        def get_images_for_chunk(chunk_idx, total_chunks, total_images):
            if total_images == 0:
                return []
            images_per_chunk = total_images / total_chunks
            start_img = int(chunk_idx * images_per_chunk)
            end_img = int((chunk_idx + 1) * images_per_chunk)
            return list(range(start_img, min(end_img, total_images)))

        # -------- PROMPTS (unchanged) ----------
        level_instructions = {
            "beginner": "Create SIMPLE and EASY-TO-UNDERSTAND notes.",
            "intermediate": "Create DETAILED and COMPREHENSIVE notes.",
            "advanced": "Create DEEP and ANALYTICAL notes."
        }

        system_prompt = f"You are an expert educational note-taking assistant.\n{level_instructions.get(level)}"

        # Generate notes
        all_notes = []
        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_images = get_images_for_chunk(chunk_idx, num_chunks, num_images)

            img_instruction = ""
            if chunk_images:
                img_refs = ", ".join([f"[PDF_IMG:{i}]" for i in chunk_images])
                img_instruction = f"\nUse images: {img_refs}"

            chunk_message = f"""
Write detailed study notes ({level} level).
Section {chunk_idx+1}/{num_chunks}.
{img_instruction}

CONTENT:
{chunk_text}
"""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chunk_message}
                ],
                temperature=0.7,
                max_tokens=4096
            )

            all_notes.append(response.choices[0].message.content)

        notes = "\n\n".join(all_notes)

        # 🔥 Save notes back to Firestore
        pdf_ref.update({
            "notes": notes,
            "notes_level": level,
            "notesGeneratedAt": firestore.SERVER_TIMESTAMP
        })

        return jsonify({
            "success": True,
            "notes": notes,
            "pdf_name": pdf_name,
            "level": level
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500
    
@app.route('/api/list-pdfs', methods=['GET'])
def list_pdfs():
    """List all uploaded PDFs for the current user"""
    try:
        user_id = get_current_user_id()

        pdfs_ref = db.collection('users').document(user_id).collection('pdfs')
        docs = pdfs_ref.stream()

        pdf_names = [doc.id for doc in docs]

        return jsonify({"pdfs": pdf_names}), 200

    except Exception as e:
        print(f"List PDFs error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def extract_pdf_images(file_bytes):
    """Render each PDF page as a high-quality image using PyMuPDF.
    Skips pages that only contain URLs/links or very little meaningful text."""
    images = []
    try:
        import re
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Check page text - skip pages that are mostly just URLs or near-empty
            page_text = page.get_text().strip()
            # Remove common watermarks/headers
            clean_text = re.sub(r'(oalevelnotes\.com|dalevelnotes\.com|made with gamma)', '', page_text, flags=re.IGNORECASE).strip()
            # Check if remaining text is mostly URLs
            non_url_text = re.sub(r'https?://\S+|www\.\S+', '', clean_text).strip()
            
            if len(non_url_text) < 20:
                print(f"  Skipping page {page_num+1} (only URLs or near-empty)")
                continue
            
            # Render page at 2x zoom for good quality (default is 72 DPI, 2x = 144 DPI)
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PNG bytes
            image_data = pix.tobytes("png")
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            images.append({
                "data": image_b64,
                "ext": "png",
                "width": pix.width,
                "height": pix.height,
                "page": page_num + 1
            })
            print(f"  Rendered page {page_num+1} as image: {pix.width}x{pix.height}")
        
        doc.close()
    except Exception as e:
        print(f"Error rendering PDF pages: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return images



@app.route('/api/pdf-image/<pdf_name>/<int:image_index>')
def serve_pdf_image(pdf_name, image_index):
    """Serve an extracted image from a PDF (Firestore version)"""
    try:
        user_id = get_current_user_id()

        # Fetch PDF doc
        pdf_ref = db.collection('users').document(user_id).collection('pdfs').document(pdf_name)
        pdf_doc = pdf_ref.get()

        if not pdf_doc.exists:
            return jsonify({"error": "PDF not found"}), 404

        pdf_data = pdf_doc.to_dict()
        images = pdf_data.get("images", [])

        # Bounds check
        if image_index < 0 or image_index >= len(images):
            return jsonify({"error": "Image index out of range"}), 404

        img = images[image_index]
        image_data = base64.b64decode(img["data"])

        # MIME detection
        ext_to_mime = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "tiff": "image/tiff",
            "webp": "image/webp"
        }
        mime_type = ext_to_mime.get(img.get("ext", "png").lower(), "image/png")

        return Response(image_data, mimetype=mime_type)

    except Exception as e:
        print(f"Serve PDF image error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/pdf-image-count/<pdf_name>')
def get_pdf_image_count(pdf_name):
    """Get image metadata for a PDF (Firestore version)"""
    try:
        user_id = get_current_user_id()

        # Fetch PDF document
        pdf_ref = db.collection('users').document(user_id).collection('pdfs').document(pdf_name)
        pdf_doc = pdf_ref.get()

        if not pdf_doc.exists:
            return jsonify({"error": "PDF not found"}), 404

        pdf_data = pdf_doc.to_dict()
        images = pdf_data.get("images", [])

        image_info = []
        for i, img in enumerate(images):
            image_info.append({
                "index": i,
                "width": img.get("width"),
                "height": img.get("height"),
                "page": img.get("page"),
                "url": f"/api/pdf-image/{pdf_name}/{i}"
            })

        return jsonify({
            "count": len(images),
            "images": image_info
        }), 200

    except Exception as e:
        print(f"PDF image count error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ============================================================================
# NOTES GENERATION ROUTES
# ============================================================================

@app.route('/api/regenerate-notes', methods=['POST'])
@require_subscription('note_regenerations')
def regenerate_notes():
    data = request.json
    pdf_name = data.get('pdf_name')
    level = data.get('level', 'beginner')
    previous_notes = data.get('previous_notes', '')

    if not pdf_name:
        return jsonify({"error": "Missing pdf_name"}), 400

    user_id = get_current_user_id()
    pdf_ref = db.collection('users').document(user_id).collection('pdfs').document(pdf_name)
    pdf_doc = pdf_ref.get()

    if not pdf_doc.exists:
        return jsonify({"error": f"PDF '{pdf_name}' not found"}), 404

    try:
        pdf_data = pdf_doc.to_dict()

        # ✅ FIX 1 — correct field name
        pdf_content = pdf_data.get("pdfText", "")
        images = pdf_data.get("images", [])

        # ── Quality check ──
        is_ok, reason = check_pdf_quality(pdf_content)
        if not is_ok:
            return jsonify({"error": reason}), 400

        num_images = len(images)
        content_length = len(pdf_content)

        # Split content into chunks
        CHUNK_SIZE = 4000
        chunks = [pdf_content[i:i + CHUNK_SIZE] for i in range(0, content_length, CHUNK_SIZE)]

        if len(chunks) > 15:
            step = len(chunks) / 15
            chunks = [chunks[int(i * step)] for i in range(15)]

        num_chunks = len(chunks)

        def get_images_for_chunk(chunk_idx, total_chunks, total_images):
            if total_images == 0:
                return []
            images_per_chunk = total_images / total_chunks
            start_img = int(chunk_idx * images_per_chunk)
            end_img = int((chunk_idx + 1) * images_per_chunk)
            return list(range(start_img, min(end_img, total_images)))

        level_instructions = {
            "beginner": "Create SIMPLE notes with a DIFFERENT approach than before.",
            "intermediate": "Create DETAILED notes using a DIFFERENT structure.",
            "advanced": "Create DIFFERENT DEEP and ANALYTICAL notes."
        }

        system_prompt = f"""You are an expert educational note-taking assistant.
Write COMPLETELY DIFFERENT, ALTERNATIVE study notes.

{level_instructions.get(level, level_instructions['beginner'])}

Write in NATURAL FLOWING PARAGRAPHS.
Use headings (##, ###). No glossary format."""

        all_notes = []
        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_images = get_images_for_chunk(chunk_idx, num_chunks, num_images)

            if chunk_images:
                img_refs = ", ".join([f"[PDF_IMG:{i}]" for i in chunk_images])
                img_instruction = f"\nIMAGES: {img_refs}"
            else:
                img_instruction = ""

            chunk_message = f"""Write COMPLETELY DIFFERENT study notes.
Section {chunk_idx + 1} of {num_chunks}.
{img_instruction}

CONTENT:
{chunk_text}"""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chunk_message}
                ],
                temperature=0.8,
                max_tokens=4096
            )

            all_notes.append(response.choices[0].message.content)

        notes = "\n\n".join(all_notes)

        # ✅ FIX 3 — store back to Firestore
        pdf_ref.update({
            "notes": notes,
            "notes_level": level,
            "regeneratedAt": firestore.SERVER_TIMESTAMP
        })

        return jsonify({
            "success": True,
            "notes": notes,
            "pdf_name": pdf_name,
            "level": level
        }), 200

    except Exception as e:
        print(f"Notes Regeneration Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# ============================================================================
# CHAT WITH PDF ROUTES
# ============================================================================

@app.route('/api/chat', methods=['POST'])
def chat_with_pdf():
    """
    Chat with a selected PDF
    """
    data = request.json or {}

    pdf_name = data.get('pdf_name')
    question = data.get('question')
    model = data.get('model', 'gpt-3.5-turbo')

    if not pdf_name or not question:
        return jsonify({"error": "Missing pdf_name or question"}), 400

    try:
        user_id = get_current_user_id()

        # 🔥 Fetch PDF from Firestore
        pdf_ref = db.collection('users') \
                    .document(user_id) \
                    .collection('pdfs') \
                    .document(pdf_name)

        pdf_doc = pdf_ref.get()

        if not pdf_doc.exists:
            return jsonify({"error": f"PDF '{pdf_name}' not found"}), 404

        pdf_data = pdf_doc.to_dict()
        pdf_content = pdf_data.get("content", "")

        if not pdf_content:
            return jsonify({"error": "PDF content is empty"}), 400

        # 🔥 Find relevant chunks
        relevant_chunks = find_relevant_chunks(pdf_content, question, top_k=3)

        system_prompt = (
            "You are a helpful AI assistant that answers questions based on provided PDF content. "
            "Answer only using the PDF content. "
            "If the answer is not present, clearly say it is not found."
        )

        user_message = (
            "PDF Content (relevant excerpts):\n"
            f"{relevant_chunks}\n\n"
            f"Question: {question}\n\n"
            "Answer based only on the content above."
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        return jsonify({
            "success": True,
            "answer": response.choices[0].message.content,
            "pdf_name": pdf_name,
            "question": question,
            "model": model
        }), 200

    except Exception as e:
        print(f"❌ Chat Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_pdf_text(file):
    """Extract text from PDF file"""
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    except:
        # Fallback to pdfplumber if PyPDF2 fails
        file.seek(0)
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    
    return text

def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into chunks with overlap"""
    chunks = []
    words = text.split()
    
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    
    return chunks

def find_relevant_chunks(text, query, top_k=3):
    """
    Simple relevance matching using keyword overlap
    (In production, use embeddings/vector search)
    """
    chunks = chunk_text(text)
    query_words = set(query.lower().split())
    
    # Score chunks by word overlap
    scored_chunks = []
    for chunk in chunks:
        chunk_words = set(chunk.lower().split())
        overlap = len(query_words & chunk_words)
        if overlap > 0:
            scored_chunks.append((overlap, chunk))
    
    # Return top-k chunks
    scored_chunks.sort(reverse=True)
    relevant = [chunk for _, chunk in scored_chunks[:top_k]]
    
    return "\n---\n".join(relevant) if relevant else text[:2000]

# ============================================================================
# TEST GENERATION ROUTES
# ============================================================================
@app.route('/api/generate-test', methods=['POST'])
@require_subscription('tests')
def generate_test():
    """
    Generate MCQ test from PDF content
    """
    data = request.json or {}
    pdf_name = data.get('pdf_name')
    difficulty = data.get('difficulty', 'normal')

    if not pdf_name:
        return jsonify({"error": "Missing pdf_name"}), 400

    try:
        user_id = get_current_user_id()

        # 🔥 Fetch PDF from Firestore
        pdf_ref = db.collection('users') \
                    .document(user_id) \
                    .collection('pdfs') \
                    .document(pdf_name)

        pdf_doc = pdf_ref.get()

        if not pdf_doc.exists:
            return jsonify({"error": "PDF not found"}), 400

        pdf_data = pdf_doc.to_dict()
        pdf_content = pdf_data.get('content', '')

        if not pdf_content:
            return jsonify({"error": "PDF content empty"}), 400

        # ── Quality check ──
        is_ok, reason = check_pdf_quality(pdf_content)
        if not is_ok:
            return jsonify({"error": reason}), 400

        # ─────────────────────────────────────
        # Difficulty prompts
        # ─────────────────────────────────────
        difficulty_prompts = {
            'easy': """EASY DIFFICULTY - Focus on basic recall and simple comprehension""",
            'normal': """NORMAL DIFFICULTY - Balance recall with basic application""",
            'hard': """HARD DIFFICULTY - Focus on analysis and reasoning"""
        }

        difficulty_instruction = difficulty_prompts.get(difficulty, difficulty_prompts['normal'])

        prompt = f"""Generate exactly 30 MCQs from the content below.

CONTENT:
{pdf_content[:4000]}

Return ONLY valid JSON array of questions.

Each question must have:
id, question, options(4), correct_answer_index, explanation, wrong_explanation
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096
        )

        response_text = response.choices[0].message.content.strip()

        # Remove markdown
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        questions = json.loads(response_text)

        if not isinstance(questions, list) or len(questions) < 5:
            return jsonify({"error": "Too few questions generated"}), 500

        # Normalize fields
        for q in questions:
            if 'wrong_explanation' not in q:
                q['wrong_explanation'] = q.get('explanation', '')

        # ─────────────────────────────────────
        # 🔥 Store Test in Firestore
        # ─────────────────────────────────────
        test_id = f"{pdf_name}_test_{difficulty}_{int(time.time())}"

        test_ref = db.collection('users') \
                     .document(user_id) \
                     .collection('tests') \
                     .document(test_id)

        test_ref.set({
            "pdf_name": pdf_name,
            "difficulty": difficulty,
            "questions": questions,
            "created_at": firestore.SERVER_TIMESTAMP
        })

        # ─────────────────────────────────────
        # Return safe questions (no answers)
        # ─────────────────────────────────────
        safe_questions = [
            {
                'id': q['id'],
                'question': q['question'],
                'options': q['options']
            } for q in questions
        ]

        return jsonify({
            "test_id": test_id,
            "difficulty": difficulty,
            "total_questions": len(safe_questions),
            "questions": safe_questions
        }), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid AI response format"}), 500
    except Exception as e:
        print(f"Error generating test: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.route('/api/check-answer', methods=['POST'])
def check_answer():
    """
    Check if answer is correct and provide explanation
    Expected JSON:
    {
        "test_id": "abc123",
        "question_id": 5,
        "selected_answer_index": 2
    }
    """
    data = request.json or {}

    test_id = data.get('test_id')
    question_id = data.get('question_id')
    selected_index = data.get('selected_answer_index')

    if not test_id:
        return jsonify({"error": "Missing test_id"}), 400

    try:
        user_id = get_current_user_id()

        # 🔥 Fetch test from Firestore
        test_ref = db.collection('users') \
                     .document(user_id) \
                     .collection('tests') \
                     .document(test_id)

        test_doc = test_ref.get()

        if not test_doc.exists:
            return jsonify({"error": "Test not found"}), 404

        test_data = test_doc.to_dict()
        questions = test_data.get('questions', [])

        # Find question
        question = next((q for q in questions if q['id'] == question_id), None)

        if not question:
            return jsonify({"error": "Question not found"}), 404

        correct_index = question['correct_answer_index']
        is_correct = selected_index == correct_index

        if is_correct:
            return jsonify({
                "is_correct": True,
                "message": "✅ Correct!",
                "explanation": question.get('explanation', 'Well done!')
            }), 200

        # ❌ Incorrect case
        wrong_answer_text = question['options'][selected_index]
        correct_answer_text = question['options'][correct_index]

        explanation = question.get(
            'wrong_explanation',
            question.get('explanation', 'That answer is incorrect.')
        )

        # Normalize formatting
        if not explanation.lower().startswith('your answer'):
            explanation = f"Your answer '{wrong_answer_text}' is incorrect. {explanation}"

        return jsonify({
            "is_correct": False,
            "message": "❌ Incorrect",
            "your_answer": wrong_answer_text,
            "correct_answer": correct_answer_text,
            "explanation": explanation
        }), 200

    except Exception as e:
        print(f"Error checking answer: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/regenerate-explanation', methods=['POST'])
@require_subscription('tests')
def regenerate_explanation():
    """
    Regenerate explanation with simpler language
    Expected: JSON with question, student_answer, correct_answer
    """
    data = request.json
    question = data.get('question')
    student_answer = data.get('student_answer')
    correct_answer = data.get('correct_answer')
    
    if not question or not student_answer or not correct_answer:
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        prompt = f"""Provide a simpler, clearer explanation for this question:

Question: {question}
Student's answer: {student_answer}
Correct answer: {correct_answer}

Explain in the simplest possible way:
1. Why '{student_answer}' is incorrect
2. Why '{correct_answer}' is the right answer
3. Use a simple analogy if helpful

Be direct - no greetings. Use very simple vocabulary. Short sentences."""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=400
        )
        
        simpler_explanation = response.choices[0].message.content.strip()
        
        if not simpler_explanation:
            return jsonify({"error": "Empty explanation received"}), 500
        
        return jsonify({
            "success": True,
            "explanation": simpler_explanation
        }), 200
    
    except Exception as e:
        print(f"Error regenerating explanation: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to regenerate explanation: {str(e)}"}), 500

# ============================================================================
# HEALTH CHECK
# ============================================================================



# ============================================================================
# TEST HISTORY ROUTES
# ============================================================================

@app.route('/api/save-test-history', methods=['POST'])
def save_test_history():
    """
    Save a test completion record for a user
    Expected: JSON with username and testRecord
    """
    try:
        data = request.get_json()
        username = data.get('username')
        test_record = data.get('testRecord')
        
        if not username or not test_record:
            return jsonify({"error": "Username and testRecord required"}), 400
        
        # Create user history file path
        user_history_file = os.path.join(DATA_DIR, f"{username}_test_history.json")
        
        # Load existing history or create new
        if os.path.exists(user_history_file):
            with open(user_history_file, 'r') as f:
                history = json.load(f)
        else:
            history = []
        
        # Add new test record
        history.insert(0, test_record)  # Add to beginning
        
        # Save updated history
        with open(user_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        return jsonify({"success": True, "message": "Test history saved"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/get-test-history', methods=['POST'])
def get_test_history():
    """
    Retrieve test history for a user
    Expected: JSON with username
    """
    try:
        data = request.get_json()
        username = data.get('username')
        
        if not username:
            return jsonify({"error": "Username required"}), 400
        
        # Create user history file path
        user_history_file = os.path.join(DATA_DIR, f"{username}_test_history.json")
        
        # Load history if exists
        if os.path.exists(user_history_file):
            with open(user_history_file, 'r') as f:
                history = json.load(f)
            return jsonify({"history": history}), 200
        else:
            return jsonify({"history": []}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/aviator-chat', methods=['POST'])
@require_subscription('aviator_messages')
def aviator_chat():
    """
    Chat with Aviator AI tutor with access to user's learning history or flowchart context
    Expected: JSON with either (username + question) OR (message + context) + optional chat history
    """
    data = request.get_json()
    
    # Support both parameter names: question/message
    question = data.get('question') or data.get('message')
    username = data.get('username')
    context_topic = data.get('context')  # For flowchart context
    chat_history = data.get('history', [])  # Get previous messages for context
    model = data.get('model', 'gpt-3.5-turbo')
    
    # Debug logging
    print(f"DEBUG: Question: {question}")
    print(f"DEBUG: Chat history length: {len(chat_history)}")
    if chat_history:
        print(f"DEBUG: Chat history content:")
        for i, msg in enumerate(chat_history):
            print(f"  [{i}] {msg['role']}: {msg['content'][:50]}...")
    
    if not question:
        return jsonify({"error": "Question or message required"}), 400
    
    try:
        # Build context - either from test history (if username provided) or flowchart context
        context = ""
        
        if username:
            # Load user's test history for personalized response
            user_history_file = os.path.join(DATA_DIR, f"{username}_test_history.json")
            test_history = []
            if os.path.exists(user_history_file):
                with open(user_history_file, 'r') as f:
                    test_history = json.load(f)
            
            if test_history:
                total_tests = len(test_history)
                avg_score = sum(t.get('percentage', 0) for t in test_history) / total_tests
                best_score = max(t.get('percentage', 0) for t in test_history)
                total_questions = sum(t.get('totalQuestions', 0) for t in test_history)
                
                # Get difficulty distribution
                difficulties = [t.get('difficulty', 'unknown') for t in test_history]
                easy_count = difficulties.count('easy')
                normal_count = difficulties.count('normal')
                hard_count = difficulties.count('hard')
                
                context = f"""User's Learning Profile:
- Tests Completed: {total_tests}
- Average Score: {avg_score:.1f}%
- Best Score: {best_score}%
- Total Questions Answered: {total_questions}
- Test Distribution: Easy ({easy_count}), Normal ({normal_count}), Hard ({hard_count})
- Recent Tests:"""
                
                # Add last 3 tests for context
                for i, test in enumerate(test_history[:3]):
                    pdf_name = test.get('pdfName', 'Unknown')
                    difficulty = test.get('difficulty', 'unknown')
                    percentage = test.get('percentage', 0)
                    score = test.get('score', 0)
                    total = test.get('totalQuestions', 0)
                    context += f"\n  * {pdf_name} ({difficulty}): {score}/{total} ({percentage}%)"
            else:
                context = "This is a new user with no test history yet."
        elif context_topic:
            # Flowchart context
            context = f"The user is working with a flowchart about: {context_topic}"
        else:
            context = "General knowledge assistant"
        
        # Create system prompt
        if username:
            system_prompt = f"""You are Aviator, a helpful AI tutor at LiftOff learning platform. You have access to this user's learning history:

{context}

Your role is to:
1. Answer questions about their learning journey
2. Provide personalized study advice based on their performance
3. Help clarify concepts they're struggling with
4. Motivate and encourage them
5. Suggest areas for improvement based on test history

IMPORTANT: When writing mathematical expressions:
- DO NOT use LaTeX notation (no backslashes)
- NEVER use ^ (caret) for exponents - use Unicode superscript: ², ³, ⁴, ⁵, ⁶, ⁷, ⁸, ⁹
- NEVER use * (asterisk) for multiplication - just write terms together or use × symbol
- Example CORRECT: p(x) = 3x² + 2x + 1 (not 3*x^2 + 2*x + 1)
- Example CORRECT: √x or ∛x for roots
- Write math exactly as it appears in textbooks students use

Be friendly, encouraging, and provide specific, actionable advice when relevant. Reference their test performance when helpful."""
        else:
            system_prompt = f"""You are Aviator, a helpful AI assistant for explaining and discussing concepts. 
{context}

IMPORTANT: When writing mathematical expressions:
- DO NOT use LaTeX notation (no backslashes)
- NEVER use ^ (caret) for exponents - use Unicode superscript: ², ³, ⁴, ⁵, ⁶, ⁷, ⁸, ⁹
- NEVER use * (asterisk) for multiplication - just write terms together or use × symbol
- Example CORRECT: p(x) = 3x² + 2x + 1 (not 3*x^2 + 2*x + 1)
- Example CORRECT: √x or ∛x for roots
- Write math exactly as it appears in textbooks students use

Keep responses concise (2-3 sentences max) and conversational. Be friendly and helpful."""
        
        # Build messages array with chat history + current message
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add previous messages from chat history if available
        if chat_history:
            messages.extend(chat_history)
        
        # Add current user message
        messages.append({"role": "user", "content": question})
        
        print(f"DEBUG: Total messages to send to OpenAI: {len(messages)}")
        print(f"DEBUG: Message roles: {[m['role'] for m in messages]}")
        for i, msg in enumerate(messages):
            if msg['role'] != 'system':
                print(f"  [{i}] {msg['role']}: {msg['content'][:60]}...")
        
        # Call OpenAI API with full conversation context
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return jsonify({
            "success": True,
            "answer": response.choices[0].message.content,
            "response": response.choices[0].message.content,  # Support both response formats
            "username": username
        }), 200
    
    except Exception as e:
        print(f"❌ Aviator Chat Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# ============================================================================
# FLASHCARD GENERATION
# ============================================================================

@app.route('/api/generate-flashcards', methods=['POST'])
@require_subscription('flashcards')
def generate_flashcards():
    """
    Generate flashcards from PDF content
    Expected JSON:
    {
        "pdf_name": "example.pdf"
    }
    """
    data = request.get_json() or {}
    pdf_name = data.get('pdf_name')

    if not pdf_name:
        return jsonify({"error": "Missing pdf_name"}), 400

    try:
        user_id = get_current_user_id()

        # 🔥 Fetch PDF from Firestore
        pdf_ref = db.collection('users') \
                    .document(user_id) \
                    .collection('pdfs') \
                    .document(pdf_name)

        pdf_doc = pdf_ref.get()

        if not pdf_doc.exists:
            return jsonify({"error": "PDF not found"}), 404

        pdf_data = pdf_doc.to_dict()
        pdf_content = pdf_data.get("content", "")

        if not pdf_content:
            return jsonify({"error": "PDF content is empty"}), 400

        # ── Quality check ──
        is_ok, reason = check_pdf_quality(pdf_content)
        if not is_ok:
            return jsonify({"error": reason}), 400

        # Use up to 6000 chars
        content = pdf_content[:6000]

        prompt = f"""Read the following content and generate flashcards.

Content:
{content}

Generate 15-25 flashcards as JSON array:
Each flashcard must have:
- "term"
- "definition"

Return ONLY valid JSON array.
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You generate educational flashcards. Return ONLY valid JSON arrays."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3500
        )

        response_text = response.choices[0].message.content.strip()

        # Remove markdown
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()

        cards_data = json.loads(response_text)

        if not isinstance(cards_data, list) or len(cards_data) < 5:
            return jsonify({"error": "Could not generate enough flashcards"}), 500

        # Validate cards
        valid_cards = [
            {
                "term": card["term"],
                "definition": card["definition"]
            }
            for card in cards_data
            if "term" in card and "definition" in card
        ]

        if len(valid_cards) < 5:
            return jsonify({"error": "Invalid flashcards generated"}), 500

        # 🔥 Store flashcards in Firestore
        flashcard_id = f"{pdf_name}_flashcards_{int(time.time())}"

        flashcard_ref = db.collection('users') \
                          .document(user_id) \
                          .collection('flashcards') \
                          .document(flashcard_id)

        flashcard_ref.set({
            "pdf_name": pdf_name,
            "flashcards": valid_cards,
            "created_at": firestore.SERVER_TIMESTAMP
        })

        return jsonify({
            "success": True,
            "flashcard_id": flashcard_id,
            "count": len(valid_cards),
            "flashcards": valid_cards
        }), 200

    except json.JSONDecodeError:
        return jsonify({"error": "Invalid AI response format"}), 500
    except Exception as e:
        print(f"❌ Flashcard Generation Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/generate-flowchart', methods=['POST'])
@require_subscription('flowcharts')
def generate_flowchart():
    """
    Generate a professional flowchart using Mermaid syntax
    Expected JSON:
    {
        "pdf_name": "example.pdf" (optional),
        "subject": "Photosynthesis" (optional),
        "model": "gpt-3.5-turbo" (optional)
    }
    """
    data = request.get_json() or {}
    pdf_name = data.get('pdf_name')
    subject = data.get('subject')
    model = data.get('model', 'gpt-3.5-turbo')

    if not pdf_name and not subject:
        return jsonify({"error": "Either pdf_name or subject required"}), 400

    try:
        content = ""

        # 🔥 Fetch from Firestore if PDF provided
        if pdf_name:
            user_id = get_current_user_id()

            pdf_ref = db.collection('users') \
                        .document(user_id) \
                        .collection('pdfs') \
                        .document(pdf_name)

            pdf_doc = pdf_ref.get()

            if not pdf_doc.exists:
                return jsonify({"error": "PDF not found"}), 404

            pdf_data = pdf_doc.to_dict()
            pdf_content = pdf_data.get("content", "")

            if not pdf_content:
                return jsonify({"error": "PDF content is empty"}), 400

            # ── Quality check ──
            is_ok, reason = check_pdf_quality(pdf_content)
            if not is_ok:
                return jsonify({"error": reason}), 400

            # Truncate for tokens
            truncated = pdf_content[:6000]
            content = f"PDF Content:\n{truncated}"

        elif subject:
            content = f"Topic: {subject}"

        # Mermaid prompt
        mermaid_prompt = f"""Create a DETAILED Mermaid flowchart.

Content:
{content}

RULES:
1. Extract ALL key concepts and relationships
2. Use FULL words (no truncation)
3. Use graph TD layout
4. 12–20 nodes
5. Mix node shapes:
   - [Rectangle] concepts
   - {{Diamond}} decisions
   - ([Rounded]) processes
6. Label arrows where meaningful

Return ONLY Mermaid code.

Example:
graph TD
    A[Life Processes] --> B[Nutrition]
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You generate professional Mermaid diagrams."
                },
                {"role": "user", "content": mermaid_prompt}
            ],
            temperature=0.7,
            max_tokens=2500
        )

        mermaid_code = response.choices[0].message.content.strip()

        # Remove markdown wrapping
        if mermaid_code.startswith('```'):
            mermaid_code = mermaid_code.split('```')[1]
            if mermaid_code.startswith('mermaid\n'):
                mermaid_code = mermaid_code[8:]
            elif mermaid_code.startswith('mermaid'):
                mermaid_code = mermaid_code[7:]
            mermaid_code = mermaid_code.strip()

        # Sanitize quotes (Mermaid breaks easily)
        import re
        mermaid_code = re.sub(r'"', "'", mermaid_code)

        return jsonify({
            "success": True,
            "mermaid_code": mermaid_code,
            "source": pdf_name or subject
        }), 200

    except Exception as e:
        print(f"❌ Flowchart Generation Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    api_key_set = os.getenv("OPENAI_API_KEY") is not None
    return jsonify({
        "status": "ok",
        "openai_key_set": api_key_set
    }), 200


# ============================================================================
# ENHANCED NOTES: IMAGE & DEFINITION FETCHING
# ============================================================================

@app.route('/api/fetch-image', methods=['POST'])
def fetch_image():
    """
    Fetch image URL - supports both Wikipedia articles and generic searches
    Expected JSON: 
    - {"query": "Wikipedia:Yeti", ...} OR
    - {"query": "Himalayan mountains", ...}
    """
    data = request.get_json()
    query = data.get('query', '').strip()
    context = data.get('context', '')
    
    if not query:
        return jsonify({"error": "Query required"}), 400
    
    try:
        print(f"📸 Attempting to fetch image for: {query}")
        
        # Check if this is a Wikipedia reference
        if query.startswith('Wikipedia:'):
            # Extract Wikipedia article title
            wiki_title = query.replace('Wikipedia:', '').strip()
            print(f"📖 Fetching from Wikipedia article: {wiki_title}")
            
            # Get Wikipedia page and find its main image
            wiki_api_url = "https://en.wikipedia.org/w/api.php"
            
            # Step 1: Get the page
            params = {
                "action": "query",
                "titles": wiki_title,
                "prop": "pageimages",
                "pithumbsize": "500",
                "format": "json"
            }
            
            response = requests.get(wiki_api_url, params=params, timeout=5)
            wiki_data = response.json()
            
            # Extract image from pages
            for page_id, page_data in wiki_data.get('query', {}).get('pages', {}).items():
                if 'thumbnail' in page_data:
                    image_url = page_data['thumbnail']['source']
                    print(f"✅ Found Wikipedia image: {image_url}")
                    return jsonify({
                        "success": True,
                        "image_url": image_url,
                        "source": "wikipedia",
                        "credits": f"Image from Wikipedia article: {wiki_title}"
                    }), 200
            
            # If no thumbnail, try to get pageimage
            params = {
                "action": "query",
                "titles": wiki_title,
                "prop": "pageprops",
                "format": "json"
            }
            response = requests.get(wiki_api_url, params=params, timeout=5)
            wiki_data = response.json()
            
            for page_id, page_data in wiki_data.get('query', {}).get('pages', {}).items():
                if 'pageimage' in page_data:
                    # Get the full image info
                    image_title = page_data['pageimage']
                    img_params = {
                        "action": "query",
                        "titles": f"File:{image_title}",
                        "prop": "imageinfo",
                        "iiprop": "url",
                        "format": "json"
                    }
                    img_response = requests.get(wiki_api_url, params=img_params, timeout=5)
                    img_data = img_response.json()
                    
                    for img_page in img_data.get('query', {}).get('pages', {}).values():
                        if 'imageinfo' in img_page:
                            image_url = img_page['imageinfo'][0]['url']
                            print(f"✅ Found Wikipedia image: {image_url}")
                            return jsonify({
                                "success": True,
                                "image_url": image_url,
                                "source": "wikipedia",
                                "credits": f"Image from Wikipedia article: {wiki_title}"
                            }), 200
        
        # Fallback: If Wikipedia lookup fails or not a Wikipedia query,
        # use a seeded image for consistency
        query_hash = str(hash(query) & 0x7FFFFFFF)
        picsum_url = f"https://picsum.photos/800/600?random={query_hash}"
        print(f"Using Picsum fallback with seed")
        return jsonify({
            "success": True,
            "image_url": picsum_url,
            "source": "picsum",
            "credits": "Image placeholder"
        }), 200
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout fetching image for {query}")
        query_hash = str(hash(query) & 0x7FFFFFFF)
        picsum_url = f"https://picsum.photos/800/600?random={query_hash}"
        return jsonify({
            "success": True,
            "image_url": picsum_url,
            "source": "picsum-fallback",
            "credits": "Image placeholder"
        }), 200
    except Exception as e:
        print(f"❌ Error fetching image: {str(e)}")
        import traceback
        traceback.print_exc()
        query_hash = str(hash(query) & 0x7FFFFFFF)
        picsum_url = f"https://picsum.photos/800/600?random={query_hash}"
        return jsonify({
            "success": True,
            "image_url": picsum_url,
            "source": "picsum-error",
            "credits": "Image placeholder"
        }), 200


@app.route('/api/fetch-definition', methods=['POST'])
def fetch_definition():
    """
    Fetch definition for a term from Wikipedia or AI explanation
    Expected JSON: {"term": "Napoleon", "context": "French Revolution", "pdf_content": "..."}
    """
    data = request.get_json()
    term = data.get('term', '').strip()
    context = data.get('context', '')
    pdf_content = data.get('pdf_content', '')
    
    if not term:
        return jsonify({"error": "Term required"}), 400
    
    print(f"📚 Fetching definition for: {term}")
    
    try:
        # First, try to find definition in PDF content
        if pdf_content and len(pdf_content) > 20:
            # Simple search: look for the term followed by explanation in PDF
            lower_pdf = pdf_content.lower()
            lower_term = term.lower()
            
            if lower_term in lower_pdf:
                # Find sentences containing the term
                sentences = pdf_content.split('. ')
                relevant_sentences = [s.strip() for s in sentences if lower_term in s.lower()][:2]
                if relevant_sentences:
                    definition = '. '.join(relevant_sentences[:2]) + '.'
                    if len(definition) > 10:  # Make sure we got real content
                        print(f"✅ Found definition from PDF: {definition[:80]}...")
                        return jsonify({
                            "success": True,
                            "definition": definition[:300],  # Limit length
                            "source": "pdf"
                        }), 200
        
        print(f"Trying Wikipedia for: {term}")
        
        # Try Wikipedia API
        wiki_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(term)
        response = requests.get(wiki_url, timeout=5)
        
        print(f"Wikipedia response status: {response.status_code}")
        
        if response.status_code == 200:
            wiki_data = response.json()
            if 'extract' in wiki_data and wiki_data['extract']:
                # Get first 200 chars of Wikipedia extract
                definition = wiki_data['extract'][:300]
                print(f"✅ Found definition from Wikipedia: {definition[:80]}...")
                return jsonify({
                    "success": True,
                    "definition": definition,
                    "source": "wikipedia"
                }), 200
        
        print(f"Generating AI definition for: {term}")
        
        # Fallback: Use AI to generate definition
        ai_definition = generate_term_definition(term, context)
        return jsonify({
            "success": True,
            "definition": ai_definition,
            "source": "ai"
        }), 200
        
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout fetching definition for {term}")
        # Fallback to AI
        ai_definition = generate_term_definition(term, context)
        return jsonify({
            "success": True,
            "definition": ai_definition,
            "source": "ai"
        }), 200
    except Exception as e:
        print(f"❌ Error fetching definition: {str(e)}")
        # Fallback to AI
        ai_definition = generate_term_definition(term, context)
        return jsonify({
            "success": True,
            "definition": ai_definition,
            "source": "ai"
        }), 200


def generate_term_definition(term, context):
    """Generate a concise definition using OpenAI"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Define the term '{term}' in 1-2 sentences. Context: {context}\n\nDefinition:"
            }],
            max_tokens=100,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except:
        return f"Definition of {term} not available"

@app.route('/api/verify_token', methods=['POST'])
def verify_token():
    data = request.json
    token = data.get("id_token")
    if not token:
        return jsonify({"success": False, "error": "No token provided"}), 400
    try:
        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(token, grequests.Request(), os.getenv("GOOGLE_CLIENT_ID"))
        # idinfo now contains info about the user
        # e.g., idinfo['email'], idinfo['name'], idinfo['sub']
        return jsonify({"success": True, "email": idinfo.get("email")})
    except ValueError as e:
        # invalid token
        return jsonify({"success": False, "error": str(e)}), 400

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 LiftOff AI Backend starting on 0.0.0.0:{port}")
    # Only run locally
    if os.getenv("RENDER") is None:  # Render sets this env automatically
        print(f"🚀 LiftOff AI Backend starting on localhost :{port}")
        app.run(host="0.0.0.0", port=port, debug=True)

