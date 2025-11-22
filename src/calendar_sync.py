
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json

load_dotenv()

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


class CalendarSync:
    def __init__(self):
        self.service = None
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self.token_file = "token.json"

    def initialize_service(self):
        if self.service:
            return  

        creds = None
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r") as f:
                    data = json.load(f)
                
                creds = Credentials(
                    token=data.get("token"),
                    refresh_token=data.get("refresh_token"),
                    token_uri=data.get("token_uri"),
                    client_id=data.get("client_id"),
                    client_secret=data.get("client_secret"),
                    scopes=data.get("scopes"),
                )
                
                if creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        self._save_token(creds)
                    except Exception as e:
                        print(f"Error refreshing token: {e}")
                        raise Exception("Failed to refresh token. Please re-authenticate at /connect")
                        
            except Exception as e:
                print(f"Error loading token: {e}")
                raise Exception("Invalid token file. Please re-authenticate at /connect")
        else:
            raise Exception("No token file found. Please authenticate at /connect")

        self.service = build("calendar", "v3", credentials=creds)

    def _save_token(self, creds):
        """Save credentials to token file"""
        data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        with open(self.token_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Token saved to {self.token_file}")

    def create_event(self, title: str, description: str, datetime_str: str, timezone="UTC"):
        self.initialize_service()

        event_date = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
        start_datetime = event_date
        end_datetime = start_datetime + timedelta(hours=1)

        event_body = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_datetime.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end_datetime.isoformat(), "timeZone": timezone},
        }

        created_event = self.service.events().insert(
            calendarId=self.calendar_id,
            body=event_body
        ).execute()
        return {
            "status": "success",
            "event_id": created_event.get("id"),
            "event_link": created_event.get("htmlLink")
        }
