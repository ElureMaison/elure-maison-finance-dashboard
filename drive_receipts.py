"""drive_receipts.py - upload a receipt file to Drive, organized by year."""

import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth import get_creds

ROOT_FOLDER_NAME = "Elure Maison Finance"


def _find_or_create_folder(drive, name, parent_id=None):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    query += f" and '{parent_id}' in parents" if parent_id else " and 'root' in parents"
    res = drive.files().list(q=query, fields="files(id,name)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [parent_id]
    folder = drive.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_receipt(file_storage, year):
    """file_storage: a werkzeug FileStorage from a Flask file upload. Returns (webViewLink, file_id)."""
    creds = get_creds()
    drive = build("drive", "v3", credentials=creds)

    root_id = _find_or_create_folder(drive, ROOT_FOLDER_NAME)
    year_id = _find_or_create_folder(drive, str(year), parent_id=root_id)

    data = file_storage.read()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=file_storage.mimetype or "application/octet-stream", resumable=False)
    metadata = {"name": file_storage.filename, "parents": [year_id]}
    uploaded = drive.files().create(body=metadata, media_body=media, fields="id,webViewLink").execute()
    return uploaded["webViewLink"], uploaded["id"]
