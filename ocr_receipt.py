"""
ocr_receipt.py - auto-detect a transaction/reference number from an uploaded
receipt image, using Google Drive's built-in OCR (no extra dependency).

Mirrors the MannaHouse project's approach and its two hard-won fixes:
- reject generic "receipt" label matches (too often captures unrelated
  trailing text like a page-transition message, not an actual number)
- validate candidates are mostly digits before accepting them
- some receipt layouts OCR label/value into two separate blocks (all
  labels first, then all values) - the labeled-pattern regex can never
  match those, so the fallback is "longest digit run anywhere in the
  text" rather than "first digit run after a label"
"""

import re
from googleapiclient.discovery import build
from google_auth import get_creds

LABELED_PATTERNS = [
    re.compile(r"(?:Ref\.?\s*No\.?|Reference\s*#?|Transaction\s*ID)[:\s]*([A-Za-z0-9\-]{6,})", re.I),
]

DIGIT_RUN = re.compile(r"\d{8,20}")


def _looks_like_reference(s):
    if not s:
        return False
    digits = sum(c.isdigit() for c in s)
    return digits >= len(s) / 2


def ocr_text_from_drive_file(file_id):
    creds = get_creds()
    drive = build("drive", "v3", credentials=creds)
    copied = drive.files().copy(fileId=file_id, body={"mimeType": "application/vnd.google-apps.document"}).execute()
    doc_id = copied["id"]
    try:
        content = drive.files().export(fileId=doc_id, mimeType="text/plain").execute()
        text = content.decode("utf-8") if isinstance(content, bytes) else content
    finally:
        drive.files().delete(fileId=doc_id).execute()
    return text


def detect_reference_number(file_id):
    text = ocr_text_from_drive_file(file_id)

    for pattern in LABELED_PATTERNS:
        m = pattern.search(text)
        if m and _looks_like_reference(m.group(1)):
            return m.group(1)

    candidates = DIGIT_RUN.findall(text)
    if candidates:
        return max(candidates, key=len)

    return None
