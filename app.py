from flask import Flask, request, jsonify, send_from_directory, make_response, Response
from flask_cors import CORS
import os
import io
import base64
from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
import pdfplumber
import fitz  # PyMuPDF for image extraction
import json
import requests
import urllib.parse
from datetime import datetime, date
import re
from functools import wraps

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load environment variables
load_dotenv()

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
app.route('/verify_token', methods=['POST'])
def verify_token():
    data = request.json
    token = data.get("id_token")
    if not token:
        return jsonify({"success": False, "error": "No token provided"}), 400
    try:
        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
        # idinfo now contains info about the user
        # e.g., idinfo['email'], idinfo['name'], idinfo['sub']
        return jsonify({"success": True, "email": idinfo.get("email")})
    except ValueError as e:
        # invalid token
        return jsonify({"success": False, "error": str(e)}), 400
    
@app.route('/')
@app.route('/dashboard')
@app.route('/dashboard.html')
def serve_dashboard():
    return serve_html('dashboard.html')

@app.route('/dashboard.html')
def serve_dashboard_explicit():
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

# Store uploaded PDFs content in memory (for development)
pdf_store = {}

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


# ============================================================================
# PDF MANAGEMENT ROUTES
# ============================================================================

@app.route('/api/upload-pdf', methods=['POST'])
def upload_pdf():
    """
    Upload a PDF and extract text content
    Expected: Form data with 'pdf' file and 'pdf_name' field
    """
    if 'pdf' not in request.files:
        return jsonify({"error": "No PDF file provided"}), 400
    
    file = request.files['pdf']
    pdf_name = request.form.get('pdf_name', file.filename)
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    try:
        # Read file bytes for both text extraction and image extraction
        file_bytes = file.read()
        file.seek(0)  # Reset for text extraction
        
        # Extract text from PDF
        pdf_text = extract_pdf_text(file)
        
        # Extract images from PDF using PyMuPDF
        extracted_images = extract_pdf_images(file_bytes)
        print(f"📸 Extracted {len(extracted_images)} images from PDF '{pdf_name}'")
        
        # Store in memory (in production, use database)
        pdf_store[pdf_name] = {
            "content": pdf_text,
            "filename": file.filename,
            "chunks": chunk_text(pdf_text),
            "images": extracted_images  # List of {data: base64, ext: 'png', width, height}
        }
        
        return jsonify({
            "success": True,
            "pdf_name": pdf_name,
            "image_count": len(extracted_images),
            "message": f"PDF '{pdf_name}' uploaded successfully with {len(extracted_images)} images"
        }), 200
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/list-pdfs', methods=['GET'])
def list_pdfs():
    """List all uploaded PDFs"""
    pdfs = list(pdf_store.keys())
    return jsonify({"pdfs": pdfs}), 200


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
    """Serve an extracted image from a PDF"""
    if pdf_name not in pdf_store:
        return jsonify({"error": "PDF not found"}), 404
    
    images = pdf_store[pdf_name].get("images", [])
    if image_index < 0 or image_index >= len(images):
        return jsonify({"error": "Image index out of range"}), 404
    
    img = images[image_index]
    image_data = base64.b64decode(img["data"])
    
    # Determine content type
    ext_to_mime = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "webp": "image/webp"
    }
    mime_type = ext_to_mime.get(img["ext"].lower(), "image/png")
    
    return Response(image_data, mimetype=mime_type)


@app.route('/api/pdf-image-count/<pdf_name>')
def get_pdf_image_count(pdf_name):
    """Get the number of extracted images from a PDF"""
    if pdf_name not in pdf_store:
        return jsonify({"error": "PDF not found"}), 404
    
    images = pdf_store[pdf_name].get("images", [])
    image_info = []
    for i, img in enumerate(images):
        image_info.append({
            "index": i,
            "width": img["width"],
            "height": img["height"],
            "page": img["page"],
            "url": f"/api/pdf-image/{pdf_name}/{i}"
        })
    
    return jsonify({
        "count": len(images),
        "images": image_info
    }), 200

# ============================================================================
# NOTES GENERATION ROUTES
# ============================================================================

@app.route('/api/generate-notes', methods=['POST'])
@require_subscription('note_generations')
def generate_notes():
    """
    Generate study notes from PDF based on understanding level
    Expected JSON:
    {
        "pdf_name": "example.pdf",
        "level": "beginner" | "intermediate" | "advanced"
    }
    """
    data = request.json
    pdf_name = data.get('pdf_name')
    level = data.get('level', 'beginner')
    
    if not pdf_name:
        return jsonify({"error": "Missing pdf_name"}), 400
    
    if pdf_name not in pdf_store:
        return jsonify({"error": f"PDF '{pdf_name}' not found"}), 404
    
    try:
        pdf_content = pdf_store[pdf_name]["content"]
        
        # ── Quality check ──
        is_ok, reason = check_pdf_quality(pdf_content)
        if not is_ok:
            return jsonify({"error": reason}), 400
        
        num_images = len(pdf_store[pdf_name].get("images", []))
        content_length = len(pdf_content)
        
        # Split content into chunks for thorough coverage
        CHUNK_SIZE = 4000  # characters per chunk
        chunks = []
        for i in range(0, content_length, CHUNK_SIZE):
            chunks.append(pdf_content[i:i + CHUNK_SIZE])
        
        # Limit to reasonable number of chunks (max 15 API calls)
        if len(chunks) > 15:
            # Spread evenly across the content
            step = len(chunks) / 15
            selected = [chunks[int(i * step)] for i in range(15)]
            chunks = selected
        
        num_chunks = len(chunks)
        print(f"📄 PDF has {content_length} chars, split into {num_chunks} chunks")
        
        # Distribute images across chunks
        def get_images_for_chunk(chunk_idx, total_chunks, total_images):
            if total_images == 0:
                return []
            images_per_chunk = total_images / total_chunks
            start_img = int(chunk_idx * images_per_chunk)
            end_img = int((chunk_idx + 1) * images_per_chunk)
            return list(range(start_img, min(end_img, total_images)))
        
        # Create level-specific prompt
        level_instructions = {
            "beginner": """Create SIMPLE and EASY-TO-UNDERSTAND notes. 
            - Explain each concept in simple words
            - Define all technical terms clearly
            - Use everyday examples to explain ideas
            - Make it suitable for someone new to the topic""",
            
            "intermediate": """Create DETAILED and COMPREHENSIVE notes.
            - Explain concepts with depth but not overly complex
            - Include real-world examples and applications
            - Show connections between different concepts
            - Include key formulas, facts, and important points""",
            
            "advanced": """Create DEEP and ANALYTICAL notes.
            - Include advanced concepts and nuanced explanations
            - Discuss critical thinking and different perspectives
            - Connect concepts to broader fields
            - Include challenging questions and advanced applications"""
        }
        
        system_prompt = f"""You are an expert educational note-taking assistant. Write notes the way a TOP STUDENT writes in their notebook.

{level_instructions.get(level, level_instructions['beginner'])}

WRITING STYLE (THIS IS THE MOST IMPORTANT RULE):
You MUST write in NATURAL FLOWING PARAGRAPHS. Each paragraph should be 4-6 sentences that explain a concept thoroughly.

BAD FORMAT (NEVER DO THIS):
- Microphone Captures Sound: The microphone detects sound waves from the environment.
- Signal Conversion: Acoustic waves are converted into electrical signals.
This is a glossary/dictionary format. Students cannot learn from this.

GOOD FORMAT (ALWAYS DO THIS):
The first step in the hearing process begins when the **microphone** picks up sound waves from the **surrounding** environment. These **acoustic** waves are then converted into electrical signals that the device can work with. Once converted, the **amplifier** takes these weak electrical signals and **fortifies** their strength significantly, making them much louder and clearer. The human ear **perceives** frequencies within a wide **spectrum**, and the hearing aid is designed to **encompass** this entire range. Finally, the **speaker** transforms these **amplified** signals back into sound waves and channels them directly into the ear canal.

NOTICE: We bolded TWO types of words:
1. Technical terms: microphone, amplifier, speaker, acoustic
2. Uncommon vocabulary: fortifies, perceives, spectrum, encompass, surrounding
Do NOT bold common words like: sound, device, signals, loud, clear

FORMATTING RULES:
1. Use ## for main topics, ### for subtopics
2. Write PARAGRAPHS of 4-6 sentences under each heading
3. NEVER use bullet points to define terms
4. Bold BOTH technical terms AND uncommon vocabulary INLINE in paragraphs
5. Include examples and analogies

The notes should read like a textbook chapter, not a dictionary or glossary."""

        # Generate notes for each chunk
        all_notes = []
        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_images = get_images_for_chunk(chunk_idx, num_chunks, num_images)
            
            if chunk_images:
                img_refs = ", ".join([f"[PDF_IMG:{i}]" for i in chunk_images])
                img_instruction = f"""
IMAGES for this section: Place these image markers in your notes: {img_refs}
- Put each image IMMEDIATELY AFTER a ### heading, BEFORE the paragraph
- Use each EXACTLY ONCE"""
            else:
                img_instruction = ""
            
            chunk_message = f"""Write DETAILED study notes for this SECTION of a PDF ({level} level).
This is section {chunk_idx + 1} of {num_chunks}.

THE #1 RULE: Write in FLOWING PARAGRAPHS, not "Term: Definition" bullet lists.
- Bold BOTH technical terms AND uncommon vocabulary words
- Each section needs 2-3 paragraphs of 4-6 sentences each
{img_instruction}

SECTION CONTENT:
{chunk_text}

Write thorough notes covering ALL the content above. Start directly with headings and content."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chunk_message}
                ],
                temperature=0.7,
                max_tokens=4096
            )
            
            chunk_notes = response.choices[0].message.content
            all_notes.append(chunk_notes)
            print(f"  ✅ Chunk {chunk_idx + 1}/{num_chunks} done")
        
        # Combine all chunks
        notes = "\n\n".join(all_notes)
        
        # Store notes in memory
        pdf_store[pdf_name]["notes"] = notes
        pdf_store[pdf_name]["notes_level"] = level
        
        return jsonify({
            "success": True,
            "notes": notes,
            "pdf_name": pdf_name,
            "level": level
        }), 200
    
    except Exception as e:
        print(f"❌ Notes Generation Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/api/regenerate-notes', methods=['POST'])
@require_subscription('note_regenerations')
def regenerate_notes():
    """
    Regenerate different study notes from PDF
    Expected JSON:
    {
        "pdf_name": "example.pdf",
        "level": "beginner" | "intermediate" | "advanced",
        "previous_notes": "previously generated notes"
    }
    """
    data = request.json
    pdf_name = data.get('pdf_name')
    level = data.get('level', 'beginner')
    previous_notes = data.get('previous_notes', '')
    
    if not pdf_name:
        return jsonify({"error": "Missing pdf_name"}), 400
    
    if pdf_name not in pdf_store:
        return jsonify({"error": f"PDF '{pdf_name}' not found"}), 404
    
    try:
        pdf_content = pdf_store[pdf_name]["content"]
        
        # ── Quality check ──
        is_ok, reason = check_pdf_quality(pdf_content)
        if not is_ok:
            return jsonify({"error": reason}), 400
        
        num_images = len(pdf_store[pdf_name].get("images", []))
        content_length = len(pdf_content)
        
        # Split content into chunks
        CHUNK_SIZE = 4000
        chunks = []
        for i in range(0, content_length, CHUNK_SIZE):
            chunks.append(pdf_content[i:i + CHUNK_SIZE])
        
        if len(chunks) > 15:
            step = len(chunks) / 15
            selected = [chunks[int(i * step)] for i in range(15)]
            chunks = selected
        
        num_chunks = len(chunks)
        
        def get_images_for_chunk(chunk_idx, total_chunks, total_images):
            if total_images == 0:
                return []
            images_per_chunk = total_images / total_chunks
            start_img = int(chunk_idx * images_per_chunk)
            end_img = int((chunk_idx + 1) * images_per_chunk)
            return list(range(start_img, min(end_img, total_images)))
        
        level_instructions = {
            "beginner": """Create SIMPLE and EASY-TO-UNDERSTAND notes with a DIFFERENT approach than before.
            - Explain concepts in simple words with different wording
            - Use DIFFERENT everyday examples
            - Make it suitable for someone new to the topic""",
            
            "intermediate": """Create DETAILED and COMPREHENSIVE notes using a DIFFERENT structure.
            - Explain concepts differently than the previous version
            - Use DIFFERENT examples and applications
            - Include different key facts and important points""",
            
            "advanced": """Create DIFFERENT DEEP and ANALYTICAL notes.
            - Include different advanced angles and perspectives
            - Discuss different critical thinking points
            - Include different challenging questions"""
        }
        
        system_prompt = f"""You are an expert educational note-taking assistant. Write COMPLETELY DIFFERENT, ALTERNATIVE study notes from the previous version.

{level_instructions.get(level, level_instructions['beginner'])}

WRITING STYLE (THIS IS THE MOST IMPORTANT RULE):
You MUST write in NATURAL FLOWING PARAGRAPHS. Each paragraph should be 4-6 sentences.

BAD FORMAT (NEVER DO THIS):
- Microphone: Detects sound waves from the environment.
- Signal Conversion: Acoustic waves are converted into electrical signals.
This is a glossary. Students cannot learn from this.

GOOD FORMAT (ALWAYS DO THIS):
The first step begins when the **microphone** picks up sound waves from the environment. These **acoustic** waves are converted into electrical signals that the device can process. The **amplifier** then **fortifies** these signals significantly, making them much louder and clearer. The device **encompasses** the full **spectrum** of **audible** frequencies that the human ear **perceives**. Finally, the **speaker** transforms the amplified signals back into sound and channels them into the ear canal.

NOTICE: Bold TWO types of words:
1. Technical terms: microphone, amplifier, speaker
2. Uncommon vocabulary: fortifies, perceives, spectrum, encompasses
Do NOT bold common words like: sound, device, signals

FORMATTING RULES:
1. Use ## for main topics, ### for subtopics
2. Write PARAGRAPHS of 4-6 sentences under each heading
3. NEVER use bullet points to define terms
4. Bold technical terms AND uncommon vocabulary INLINE in paragraphs

Use a DIFFERENT organizational structure and angle than the previous version."""

        # Generate notes for each chunk
        all_notes = []
        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_images = get_images_for_chunk(chunk_idx, num_chunks, num_images)
            
            if chunk_images:
                img_refs = ", ".join([f"[PDF_IMG:{i}]" for i in chunk_images])
                img_instruction = f"""
IMAGES for this section: {img_refs}
- Put each AFTER a ### heading, BEFORE the paragraph. Use each ONCE."""
            else:
                img_instruction = ""
            
            chunk_message = f"""Write COMPLETELY DIFFERENT study notes for this SECTION ({level} level).
Section {chunk_idx + 1} of {num_chunks}. Use DIFFERENT angle/structure than previous version.

Write in FLOWING PARAGRAPHS, not "Term: Definition" lists.
Bold BOTH technical terms AND uncommon vocabulary.
{img_instruction}

SECTION CONTENT:
{chunk_text}

Write thorough notes covering ALL content above. Start directly."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chunk_message}
                ],
                temperature=0.8,
                max_tokens=4096
            )
            
            chunk_notes = response.choices[0].message.content
            all_notes.append(chunk_notes)
        
        notes = "\n\n".join(all_notes)
        
        # Store updated notes
        pdf_store[pdf_name]["notes"] = notes
        
        return jsonify({
            "success": True,
            "notes": notes,
            "pdf_name": pdf_name,
            "level": level
        }), 200
    
    except Exception as e:
        print(f"   Notes Regeneration Error: {str(e)}")
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
    Expected JSON:
    {
        "pdf_name": "example.pdf",
        "question": "What is this about?",
        "model": "gpt-3.5-turbo" (optional)
    }
    """
    data = request.json
    pdf_name = data.get('pdf_name')
    question = data.get('question')
    model = data.get('model', 'gpt-3.5-turbo')
    
    if not pdf_name or not question:
        return jsonify({"error": "Missing pdf_name or question"}), 400
    
    if pdf_name not in pdf_store:
        return jsonify({"error": f"PDF '{pdf_name}' not found"}), 404
    
    try:
        # Get relevant context from PDF
        pdf_content = pdf_store[pdf_name]["content"]
        relevant_chunks = find_relevant_chunks(pdf_content, question, top_k=3)
        
        # Create prompt with context
        system_prompt = """You are a helpful AI assistant that answers questions based on provided PDF content. 
        Answer only based on the information in the PDF. If the answer is not in the PDF, say so clearly."""
        
        user_message = f"""PDF Content (relevant excerpts):
{relevant_chunks}

Question: {question}

Please answer based only on the PDF content provided above."""
        
        # Call OpenAI API
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
    Generate 30 MCQ test from PDF content
    Expected: JSON with pdf_name and difficulty (easy/normal/hard)
    """
    data = request.json
    pdf_name = data.get('pdf_name')
    difficulty = data.get('difficulty', 'normal')
    
    if not pdf_name or pdf_name not in pdf_store:
        return jsonify({"error": "PDF not found"}), 400
    
    pdf_content = pdf_store[pdf_name]['content']
    
    # ── Quality check ──
    is_ok, reason = check_pdf_quality(pdf_content)
    if not is_ok:
        return jsonify({"error": reason}), 400
    
    try:
        # Create difficulty-specific prompt
        difficulty_prompts = {
            'easy': """EASY DIFFICULTY - Focus on basic recall and simple comprehension:
- Questions should test ONLY basic definitions and facts
- Avoid any application or analysis
- Use straightforward, direct questions about key facts
- Distractors should be obviously wrong
- Test memory, not thinking""",
            
            'normal': """NORMAL DIFFICULTY - Balance recall with basic application:
- Questions should require understanding AND basic application
- Mix some factual questions with simple application scenarios
- Distractors should be plausible but clearly wrong on reflection
- Test comprehension and simple problem-solving""",
            
            'hard': """HARD DIFFICULTY - Focus on analysis, application, and synthesis:
- Questions MUST require deep understanding and critical thinking
- Include scenario-based questions requiring application to new situations
- Ask students to analyze relationships between concepts
- Include questions about WHY and HOW, not just WHAT
- Distractors should be very plausible - choices that seem right at first but are subtly wrong
- Test synthesis, analysis, and evaluation
- Avoid simple recall questions - EVERY question should require reasoning"""
        }
        
        difficulty_instruction = difficulty_prompts.get(difficulty, difficulty_prompts['normal'])
        
        prompt = f"""Based on the following content, generate exactly 30 multiple choice questions (MCQs) in JSON format.

IMPORTANT: Generate questions ONLY from the actual content provided below. Do NOT make up, assume, or fabricate questions about topics not present in the content. If the content is unclear, unreadable, or too fragmented to understand, respond with EXACTLY this JSON: {{"error": "unreadable"}}

CONTENT:
{pdf_content[:4000]}

DIFFICULTY LEVEL REQUIREMENTS:
{difficulty_instruction}

You MUST return ONLY valid JSON array, nothing else. NO markdown, NO code blocks, NO extra text.

[
  {{"id": 1, "question": "Question text here?", "options": ["Option A", "Option B", "Option C", "Option D"], "correct_answer_index": 0, "explanation": "Explanation of why correct answer is right", "wrong_explanation": "Explanation addressing why the student's choice was wrong and why the correct answer is right"}},
  {{"id": 2, "question": "Another question?", "options": ["A", "B", "C", "D"], "correct_answer_index": 1, "explanation": "Explain correct answer", "wrong_explanation": "Address wrong answers"}},
  ... continue for exactly 30 questions ...
]

CRITICAL REQUIREMENTS:
- EXACTLY 30 questions with id from 1 to 30
- For {difficulty} difficulty: {difficulty_instruction.split('-')[0].strip()}
- RANDOMIZE correct_answer_index: Distribute answers across 0, 1, 2, 3 - NOT always index 0
- Do NOT put correct answer in same position twice consecutively
- Vary the position: some questions 0, some 1, some 2, some 3
- Each question MUST have: id, question, options (exactly 4), correct_answer_index (0-3), explanation, wrong_explanation
- Return ONLY the JSON array, nothing else
- Do NOT include markdown code blocks or triple backticks
- Ensure all strings are properly quoted"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4096
        )
        
        # Parse response
        response_text = response.choices[0].message.content.strip()
        
        # Remove markdown formatting if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        # Try to parse JSON
        try:
            questions = json.loads(response_text)
        except json.JSONDecodeError:
            # If parsing fails, log the response and return error with more detail
            print(f"Failed to parse response: {response_text[:500]}")
            return jsonify({"error": "Backend API returned invalid format. Please try again."}), 500
        
        # Check if AI flagged content as unreadable
        if isinstance(questions, dict) and questions.get('error') == 'unreadable':
            return jsonify({"error": "The PDF content could not be understood well enough to generate a test. The text may be handwritten, blurry, or too fragmented. Please try a clearer PDF."}), 400
        
        # Ensure we have enough questions (accept 10+ instead of requiring exactly 30)
        if not isinstance(questions, list) or len(questions) < 5:
            return jsonify({"error": f"Too few questions generated ({len(questions) if isinstance(questions, list) else 'invalid format'}). Please try again."}), 500
        
        # Validate each question has required fields
        for q in questions:
            if not all(k in q for k in ['id', 'question', 'options', 'correct_answer_index', 'explanation']):
                return jsonify({"error": "Question missing required fields"}), 500
            # Add wrong_explanation if missing
            if 'wrong_explanation' not in q:
                q['wrong_explanation'] = q['explanation']
        
        # Store test in memory with pdf mapping
        test_id = f"{pdf_name}_test_{difficulty}"
        pdf_store[pdf_name][f'test_{difficulty}'] = {
            'questions': questions,
            'difficulty': difficulty
        }
        
        # Return questions WITHOUT revealing correct answer
        safe_questions = []
        for q in questions:
            safe_questions.append({
                'id': q['id'],
                'question': q['question'],
                'options': q['options']
            })
        
        return jsonify({
            "test_id": test_id,
            "difficulty": difficulty,
            "total_questions": len(safe_questions),
            "questions": safe_questions
        }), 200
    
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        return jsonify({"error": "Failed to parse test questions"}), 500
    except Exception as e:
        print(f"Error generating test: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/check-answer', methods=['POST'])
def check_answer():
    """
    Check if answer is correct and provide explanation
    Expected: JSON with pdf_name, difficulty, question_id, and selected_answer_index
    """
    data = request.json
    pdf_name = data.get('pdf_name')
    difficulty = data.get('difficulty')
    question_id = data.get('question_id')
    selected_index = data.get('selected_answer_index')
    
    if not pdf_name or pdf_name not in pdf_store:
        return jsonify({"error": "PDF not found"}), 400
    
    try:
        test_data = pdf_store[pdf_name].get(f'test_{difficulty}')
        if not test_data:
            return jsonify({"error": "Test not found"}), 400
        
        questions = test_data['questions']
        question = next((q for q in questions if q['id'] == question_id), None)
        
        if not question:
            return jsonify({"error": "Question not found"}), 400
        
        is_correct = selected_index == question['correct_answer_index']
        
        if is_correct:
            return jsonify({
                "is_correct": True,
                "message": "✅ Correct!",
                "explanation": question.get('explanation', 'Well done!')
            }), 200
        else:
            # Return pre-generated explanation (no API call needed - instant response)
            wrong_answer_text = question['options'][selected_index]
            correct_answer_text = question['options'][question['correct_answer_index']]
            
            # Use the pre-generated wrong_explanation
            explanation = question.get('wrong_explanation', question.get('explanation', 'That answer is incorrect.'))
            
            # Ensure proper formatting
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
    Expected: JSON with pdf_name
    """
    data = request.get_json()
    pdf_name = data.get('pdf_name')
    
    if not pdf_name or pdf_name not in pdf_store:
        return jsonify({"error": "PDF not found"}), 400
    
    try:
        pdf_content = pdf_store[pdf_name]["content"]
        
        # ── Quality check ──
        is_ok, reason = check_pdf_quality(pdf_content)
        if not is_ok:
            return jsonify({"error": reason}), 400
        
        # Use up to 6000 chars for comprehensive flashcard coverage
        content = pdf_content[:6000]
        
        prompt = f"""Read the following content and generate flashcards for studying. Extract the most important terms, concepts, processes, and facts.

Content:
{content}

Generate 15-25 flashcards as a JSON array. Each flashcard has a "term" (the concept/keyword) and a "definition" (clear, concise explanation in 1-3 sentences).

Rules:
- Cover ALL major topics from the content
- Terms should be specific: names, processes, concepts, formulas, vocabulary
- Definitions should be clear and student-friendly
- Do NOT repeat similar cards
- Include both factual recall and conceptual understanding cards

Return ONLY a valid JSON array, no markdown, no code blocks. Use this exact format:
[{{"term": "Example Term", "definition": "A clear explanation."}}]

Generate the flashcards NOW:"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You generate educational flashcards from study material. Return ONLY valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3500
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Clean markdown formatting
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        cards_data = json.loads(response_text)
        
        if not isinstance(cards_data, list) or len(cards_data) < 5:
            return jsonify({"error": "Could not generate enough flashcards. Please try again."}), 500
        
        # Ensure each card has term and definition
        valid_cards = []
        for card in cards_data:
            if 'term' in card and 'definition' in card:
                valid_cards.append({
                    'term': card['term'],
                    'definition': card['definition']
                })
        
        if len(valid_cards) < 5:
            return jsonify({"error": "Could not generate valid flashcards. Please try again."}), 500
        
        return jsonify({
            "success": True,
            "flashcards": valid_cards,
            "count": len(valid_cards)
        }), 200
    
    except Exception as e:
        print(f"❌ Flashcard Generation Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/api/generate-flowchart', methods=['POST'])
@require_subscription('flowcharts')
def generate_flowchart():
    """
    Generate a professional flowchart using Mermaid syntax
    Expected: JSON with either pdf_name or subject (or both)
    """
    data = request.get_json()
    pdf_name = data.get('pdf_name')
    subject = data.get('subject')
    model = data.get('model', 'gpt-3.5-turbo')
    
    if not pdf_name and not subject:
        return jsonify({"error": "Either pdf_name or subject required"}), 400
    
    try:
        # Get content to create flowchart from
        content = ""
        
        if pdf_name and pdf_name in pdf_store:
            # Use FULL PDF content (truncated to fit token limits)
            pdf_content = pdf_store[pdf_name]["content"]
            
            # ── Quality check ──
            is_ok, reason = check_pdf_quality(pdf_content)
            if not is_ok:
                return jsonify({"error": reason}), 400
            
            # Send up to 6000 chars of full content for comprehensive flowchart
            if len(pdf_content) > 6000:
                content = f"PDF Content (full chapter):\n{pdf_content[:6000]}"
            else:
                content = f"PDF Content (full chapter):\n{pdf_content}"
        elif subject:
            # Use subject text
            content = f"Topic: {subject}"
        else:
            return jsonify({"error": "PDF not found"}), 404
        
        # Create Mermaid flowchart generation prompt
        mermaid_prompt = f"""Read the following content carefully and create a DETAILED, ACCURATE Mermaid flowchart that captures ALL the key concepts, processes, and relationships.

Content:
{content}

IMPORTANT RULES:
1. Read the content THOROUGHLY - extract EVERY important concept, process, term, and relationship
2. Use FULL words in labels - NEVER abbreviate or truncate (write "Metabolism" not "Metabolis", write "Characteristics of Life Processes" not "Characteristics of Life P")
3. Keep node labels SHORT but COMPLETE - if a label is too long, split into multiple lines using <br/> OR simplify the wording while keeping meaning
4. Use graph TD (top-down layout)
5. Show the main topic at the top, then branch into sub-topics and details
6. Include 12-20 nodes for comprehensive coverage
7. Use different node shapes: A[Rectangle] for concepts, A{{Diamond}} for decisions, A([Rounded]) for processes
8. Label arrows with relationships: A -->|type| B
9. Cover ALL major topics from the content, not just the first few

Return ONLY valid Mermaid code, no explanations. Example:
```
graph TD
    A[Life Processes] --> B[Nutrition]
    A --> C[Respiration]
    A --> D[Transportation]
    B --> E[Autotrophic Nutrition]
    B --> F[Heterotrophic Nutrition]
```

Generate the complete Mermaid flowchart NOW:"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert at creating beautiful, professional flowcharts using Mermaid.js syntax. Generate clean, well-organized Mermaid code that renders as professional diagrams."},
                {"role": "user", "content": mermaid_prompt}
            ],
            temperature=0.7,
            max_tokens=2500
        )
        
        mermaid_code = response.choices[0].message.content.strip()
        
        # Clean up if wrapped in markdown code blocks
        if mermaid_code.startswith('```'):
            mermaid_code = mermaid_code.split('```')[1]
            if mermaid_code.startswith('mermaid\n'):
                mermaid_code = mermaid_code[8:]
            elif mermaid_code.startswith('mermaid'):
                mermaid_code = mermaid_code[7:]
            mermaid_code = mermaid_code.strip()
        
        # Sanitize mermaid code: remove quotes within node labels to avoid syntax errors
        import re
        # Replace quotes inside square brackets with apostrophes or remove them
        mermaid_code = re.sub(r'\[([^[\]]*)"([^[\]]*)"([^[\]]*)\]', r'[\1\2\3]', mermaid_code)
        # Handle multiple quotes in same label
        mermaid_code = re.sub(r'"', "'", mermaid_code)
        
        return jsonify({
            "success": True,
            "mermaid_code": mermaid_code,
            "subject": subject or pdf_name
        }), 200
    
    except Exception as e:
        print(f"❌ Flowchart Generation Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

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

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == '__main__':
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  WARNING: OPENAI_API_KEY not set!")
        print("Create a .env file with: OPENAI_API_KEY=your_key_here\n")
    
    print("🚀 LiftOff AI Backend starting on http://localhost:5000")
    app.run(debug=True, port=5000)
