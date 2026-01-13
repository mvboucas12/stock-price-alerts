import base64
import json
import os
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def load_secret_file(env_var, filename):
    if os.path.exists(filename):
        return

    content = os.getenv(env_var)
    if not content:
        return

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)


def get_gmail_service():
    load_secret_file("GMAIL_CREDENTIALS_JSON", "credentials.json")
    load_secret_file("GMAIL_TOKEN_JSON", "token.json")

    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_email(subject, html_body, to_email):
    service = get_gmail_service()

    message = MIMEText(html_body, "html")
    message["to"] = to_email
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}

    service.users().messages().send(
        userId="me",
        body=body
    ).execute()
