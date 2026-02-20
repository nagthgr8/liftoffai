# LiftOff PDF Chat - OpenAI Integration Setup

## Quick Start Guide

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Up Your OpenAI API Key

1. Get your API key from: https://platform.openai.com/api-keys
2. Open the `.env` file in this folder
3. Replace `your_openai_api_key_here` with your actual API key:
   ```
   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxx
   ```

### Step 3: Start the Backend Server
```bash
python app.py
```

You should see:
```
🚀 LiftOff AI Backend starting on http://localhost:5000
```

### Step 4: Open the Chat Interface
Open your browser and go to:
```
file:///C:/Users/Akio/OneDrive/Documents/LiftOff/pdf-chat.html
```
(Or adjust the path to your actual location)

---

## How It Works

1. **Upload PDF**: Click "Upload PDF" button - can upload multiple PDFs
2. **Select PDF**: Click on any PDF from the list to select it
3. **Ask Questions**: Type your question and press Enter or click Send
4. **Get Answers**: AI analyzes the PDF and answers based on its content

---

## API Endpoints

### 1. Upload a PDF
```
POST /api/upload-pdf
Content-Type: multipart/form-data

Form Data:
- pdf: (file)
- pdf_name: (string, optional)

Response:
{
    "success": true,
    "pdf_name": "example.pdf",
    "message": "PDF uploaded successfully"
}
```

### 2. List Uploaded PDFs
```
GET /api/list-pdfs

Response:
{
    "pdfs": ["file1.pdf", "file2.pdf"]
}
```

### 3. Chat with a PDF
```
POST /api/chat
Content-Type: application/json

Body:
{
    "pdf_name": "example.pdf",
    "question": "What is this about?"
}

Response:
{
    "success": true,
    "answer": "Based on the PDF...",
    "pdf_name": "example.pdf",
    "question": "What is this about?",
    "model": "gpt-3.5-turbo"
}
```

### 4. Health Check
```
GET /api/health

Response:
{
    "status": "ok",
    "openai_key_set": true
}
```

---

## File Structure

```
LiftOff/
├── app.py                 # Flask backend with OpenAI integration
├── pdf-chat.html         # Chat interface UI
├── requirements.txt      # Python dependencies
├── .env                  # Your API keys (KEEP SECRET!)
├── dashboard.html        # Original dashboard
└── README.md            # This file
```

---

## Troubleshooting

### Error: "OPENAI_API_KEY not set"
- Check your `.env` file has the correct API key
- Make sure `.env` is in the same folder as `app.py`
- Restart the server after updating `.env`

### Error: "CORS policy: No 'Access-Control-Allow-Origin'"
- This is expected if frontend and backend are on different ports
- The `Flask-CORS` library handles this automatically
- Make sure backend is running on http://localhost:5000

### PDF extraction failing
- The app tries PyPDF2 first, then falls back to pdfplumber
- Some PDFs might have encoding issues - try uploading a simpler PDF first

### Slow responses
- First request is slower (model loading)
- Long PDFs take time to process
- Consider upgrading to `gpt-4` in `app.py` for better quality (costs more)

---

## Next Steps

### Enhance the System:
1. **Database**: Replace in-memory storage with actual database (PostgreSQL + pgvector)
2. **Vector Embeddings**: Use OpenAI embeddings for better similarity search
3. **Authentication**: Add login/user management
4. **Usage Tracking**: Monitor API costs and student usage
5. **Better Chunking**: Implement smarter PDF chunking strategy

### Example Code for Vector Search (Future):
```python
from openai import OpenAI

# Generate embeddings
embedding = client.embeddings.create(
    input="student question here",
    model="text-embedding-3-small"
)
```

---

## Project Structure Preview

### What We Built:

**Backend (`app.py`)**:
- Flask server with CORS enabled
- PDF upload & text extraction
- Simple keyword-based chunk retrieval
- OpenAI API integration for chat
- In-memory PDF storage (development only)

**Frontend (`pdf-chat.html`)**:
- Beautiful dark theme UI
- PDF upload interface
- PDF selection sidebar
- Chat interface with messages
- Real-time conversation with AI

---

## Security Notes ⚠️

1. **Never commit `.env` to git** - Add to `.gitignore`
2. **Rotate API keys** if compromised
3. **Set usage limits** on OpenAI dashboard
4. **In production**: Use environment variables or secure vaults (AWS Secrets Manager, etc.)

---

## Support

If you face issues:
1. Check the browser console (F12) for errors
2. Check the terminal output from `python app.py`
3. Verify OpenAI API key is valid at https://platform.openai.com/api-keys
4. Test the API: Open browser and go to `http://localhost:5000/api/health`

---

**Happy Learning! 🚀**
