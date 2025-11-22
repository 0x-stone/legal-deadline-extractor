import re
from datetime import datetime
from dateutil import parser
from typing import List, Dict
from pydantic import BaseModel, Field, RootModel
from dotenv import load_dotenv
from google import genai

load_dotenv()


class DeadlineResponse(BaseModel):
    title: str = Field(
        ...,
        description="A concise short, calendar-friendly title"
    )    
    text: str = Field(
        ...,
        description="The exact snippet of text where the date/time was mentioned."
    )
    datetime: str = Field(
        ...,
        description="Parsed datetime in 'YYYY-MM-DD HH:MM' format."
    )
    event_type: str = Field(
        ...,
        description="The detected category of event (e.g., Hearing, Deadline, Filing)."
    )
    description: str = Field(
        ...,
        description="A concise, calendar-friendly explanation of the event and required action."
    )

class DeadlineList(RootModel):
    root: List[DeadlineResponse]

class DeadlineExtractor:
    def __init__(self):
        self.event_keywords = {
            'hearing': ['hearing', 'court date', 'appearance'],
            'deadline': ['deadline', 'due', 'must file', 'required by'],
            'filing': ['filing', 'file by', 'submit'],
            'response': ['response', 'answer', 'reply'],
            'trial': ['trial', 'trial date'],
            'deposition': ['deposition', 'depo'],
            'conference': ['conference', 'meeting']
        }
        self.client = genai.Client()

    def extract_deadlines(self, text: str) -> List[Dict]:
        deadlines = []
        llm_based = self._llm_extraction(text)
        if llm_based:
            deadlines.extend(llm_based)
        else:
            rule_based = self._rule_based_extraction(text)
            deadlines.extend(rule_based)
        return self._deduplicate(deadlines)


    def _rule_based_extraction(self, text: str) -> List[Dict]:
        deadlines = []

        date_patterns = [
            r'([A-Za-z]+\s+\d{1,2},?\s+\d{4})',                     
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',                     
            r'(\d{4}-\d{1,2}-\d{1,2})',                            
            r'(\d{1,2}(?:st|nd|rd|th)\s+of\s+[A-Za-z]+\s+\d{4})',  
        ]

        time_patterns = [
            r'(\d{1,2}:\d{2}\s?(?:AM|PM|am|pm))',  
            r'(\d{1,2}\s?(?:AM|PM|am|pm))',       
            r'(\d{1,2}:\d{2})',                
        ]

        for date_pattern in date_patterns:
            matches = re.finditer(date_pattern, text, re.IGNORECASE)

            for match in matches:
                date_str = match.group(1)

                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 80)
                context = text[start:end]

                found_time = None
                for t_pat in time_patterns:
                    t_match = re.search(t_pat, context)
                    if t_match:
                        found_time = t_match.group(1)
                        break

                try:
                    if found_time:
                        dt = parser.parse(f"{date_str} {found_time}", fuzzy=True)
                    else:
                        dt = parser.parse(date_str, fuzzy=True).replace(hour=9, minute=0)

                    if dt >= datetime.now():
                        event_type = self._identify_event_type(context)
                        deadlines.append({
                            "title":f"{event_type}:{context.strip()[:50]}",
                            "text": context.strip(),
                            "datetime": dt.strftime("%Y-%m-%d %H:%M"),
                            "event_type": event_type,
                            "description": event_type
                        })

                except Exception:
                    continue

        return deadlines

    def _identify_event_type(self, text: str) -> str:
        text_lower = text.lower()
        for event_type, keywords in self.event_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return event_type.capitalize()
        return "Deadline"


    def _llm_extraction(self, text: str) -> List[Dict]:
        try:
            prompt = f"""
Extract all legal deadlines and hearing-related dates **with times** from the following document.

For each item, provide:
1. title A concise short, calendar-friendly title
2. exact text snippet mentioning the date/time
3. datetime in 'YYYY-MM-DD HH:MM' format
4. event_type (Hearing, Filing, Deadline, Response, Trial, etc.)
5. a concise 1–3 sentence calendar-friendly description

TEXT:
{text}

Return ONLY a JSON array.
"""

            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": DeadlineList.model_json_schema()
                }
            )

            parsed = DeadlineList.model_validate_json(response.text)
            return [item.dict() for item in parsed.root]

        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return []


    def _deduplicate(self, deadlines: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []

        for d in deadlines:
            key = (d["datetime"], d["event_type"])
            if key not in seen:
                seen.add(key)
                unique.append(d)

        return unique
