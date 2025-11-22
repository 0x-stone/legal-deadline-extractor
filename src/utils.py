import re
from datetime import datetime
from typing import Optional, List
from langchain.text_splitter import RecursiveCharacterTextSplitter

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except:
        return False

def format_event_title(event_type: str, text: str, max_length: int = 100) -> str:
    title = f"{event_type}: {text}"
    if len(title) > max_length:
        title = title[:max_length-3] + "..."
    return title

def extract_case_number(text: str) -> Optional[str]:
    patterns = [
        r'Case\s+No\.?\s*:?\s*([A-Z0-9-]+)',
        r'Case\s+Number\s*:?\s*([A-Z0-9-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def is_future_date(datetime_str: str) -> bool:
    try:
        dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        return dt >= datetime.now()
    except ValueError:
        try:
            dt = datetime.strptime(datetime_str, '%Y-%m-%d')
            return dt >= datetime.now()
        except ValueError:
            return False

def chunk_text(text: str, chunk_size: int = 2000, chunk_overlap: int = 200) -> List[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", "!", "?", " ", ""]
    )
    return splitter.split_text(text)