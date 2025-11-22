# Legal DeadLine Extractor

> Built to demonstrate the core workflow for legal document processing: OCR → LLM extraction → Calendar sync.

## 🎥 Demo (~2 min)
> Upload Document → Extract deadlines → Sync to Google Calendar

https://github.com/user-attachments/assets/8bf8a3ce-712b-4959-92ad-f4edf88ec408

---

## Architecture

```
PDF Upload → Tesseract OCR → Chunk text (2000 chars, 200 overlap)
→ Gemini 2.0 extraction (regex fallback) → Deduplicate
→ Google Calendar API → Return event links
```

**Key decisions:**
- **Hybrid extraction**: LLM primary, regex fallback (handles API failures, rate limits, structured dates)
- **Text chunking**: 2000-char blocks with 200-char overlap to preserve context
- **Deduplication**: Hash (datetime, event_type) prevents duplicate events
- **OAuth token persistence**: Refresh tokens stored server-side for seamless re-auth
- **Past date filtering**: Only extracts future deadlines to avoid calendar clutter

---

## Quick Start

**Docker:**
```bash
# Create .env file with:
# GOOGLE_CALENDAR_ID=primary
# GEMINI_API_KEY=your_key_here


# Add your Google Calendar credentials.json
# (from Google Cloud Console → Calendar API → OAuth)


docker build -t deadline-extractor .
docker run -p 8000:8000 \
  -v $(pwd)/credentials.json:/app/credentials.json \
  --env-file .env \
  deadline-extractor

# Connect calendar once: visit http://localhost:8000/connect
# Upload test files: open test.html in browser
```

---

## What I'd Improve for Production

- **Document security**: Encrypted storage (S3 + KMS), not raw files on server
- **OAuth credential security**: Store tokens encrypted, not in raw JSON files
- **Monitoring**: LangSmith for LLM observability, Sentry for error tracking
- **Calendar integrations**: Outlook/Office 365, Apple Calendar
- **Timezone handling**: Currently hardcoded UTC
- **Confidence scores**: Flag low-confidence extractions for review
- **Background jobs**: Celery + Redis for async processing
- **Database**: PostgreSQL for event/document history
- **Audit logs**: Track who uploaded what, when

---

## Code Structure

```
src/
├── main.py                # FastAPI endpoints, OAuth flow
├── ocr_processor.py       # Tesseract, PDF→image, text cleanup
├── deadline_extractor.py  # Gemini + regex extraction logic
├── calendar_sync.py       # Google Calendar API wrapper
└── utils.py               # Chunking, date validation

test.html                  # Drag-and-drop test UI
Dockerfile                 # Production container
```

---

## Sample Output

**Input:** `court_filing.pdf`  
**Extracted:**
```json
[
  {
    "title": "Hearing: Motion to Compel",
    "datetime": "2025-01-15 10:00",
    "event_type": "Hearing",
    "calendar_link": "https://calendar.google.com/event?eid=..."
  },
  {
    "title": "Deadline: Response Due",
    "datetime": "2025-01-08 17:00",
    "event_type": "Deadline",
    "calendar_link": "https://calendar.google.com/event?eid=..."
  }
]
```

---