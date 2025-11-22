from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
import os
import json
from dotenv import load_dotenv

from .ocr_processor import OCRProcessor
from .deadline_extractor import DeadlineExtractor
from .calendar_sync import CalendarSync
from .utils import chunk_text
from google_auth_oauthlib.flow import Flow
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

MAX_FILE_SIZE_MB= 10

load_dotenv()

app = FastAPI(
    title="Legal Document Deadline Extraction API",
    description="Extract deadlines from legal documents and sync to Google Calendar"
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr_processor = OCRProcessor()
deadline_extractor = DeadlineExtractor()
calendar_sync = CalendarSync()

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CLIENT_SECRETS_FILE = "credentials.json"


class EventData(BaseModel):
    title: str
    details: str
    start_time: str
    end_time: str
    timezone: str = "UTC"

class DeadlineResponse(BaseModel):
    text: str
    datetime: str
    event_type: str
    calendar_event_id: Optional[str] = None
    calendar_link: Optional[str] = None

class ProcessResponse(BaseModel):
    status: str
    extracted_text: str
    deadlines: List[DeadlineResponse]

@app.get("/")
async def root():
    return {
        "message": "Legal Document Extraction API",
    }

@app.get("/connect")
def connect_google():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/callback"
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent" 
    )
    return RedirectResponse(url=auth_url) 



@app.get("/callback")
async def callback(code: str):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/callback"
    )
    flow.fetch_token(code=code)
    credentials = flow.credentials

    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes
    }

    with open("token.json", "w") as f:
        json.dump(token_data, f)

    return JSONResponse(content={"status": "success", "message": "Google Calendar connected!"})



@app.post("/process-document", response_model=ProcessResponse)
async def process_document(file: UploadFile = File(...)):
    try:
        if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds maximum size of {MAX_FILE_SIZE_MB} MB"
            )
        if not file.filename.lower().endswith(('.pdf', '.txt', '.png', 'jpg')):
            raise HTTPException(
                status_code=400,
                detail="Only PDF, PNG, JPG and TXT files are supported"
            )
        
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        extracted_text = ocr_processor.process_document(temp_path)
        
        os.remove(temp_path)
        
        if not extracted_text:
            raise HTTPException(
                status_code=400,
                detail="No text could be extracted from document"
            )
        
        text_chunks = chunk_text(extracted_text)

        deadlines = []
        for chunk in text_chunks:
            deadlines.extend(deadline_extractor.extract_deadlines(chunk))

        unique_deadlines = {d['datetime']: d for d in deadlines}.values()

        deadline_responses = []
        for deadline in unique_deadlines:
            try:
                event_result = calendar_sync.create_event(
                    title=f"{deadline['title']}",
                    description=f"{deadline['description']}",
                    datetime_str=deadline['datetime'],
                )
                
                deadline_responses.append(DeadlineResponse(
                    text=deadline['text'],
                    datetime=deadline['datetime'],
                    event_type=deadline['event_type'],
                    calendar_event_id=event_result.get('event_id'),
                    calendar_link=event_result.get('event_link')
                ))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
        
        return ProcessResponse(
            status="success",
            extracted_text=extracted_text,
            deadlines=deadline_responses
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
