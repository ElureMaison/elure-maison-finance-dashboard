"""sheet_write.py - append/update/clear a single row in the Expenses sheet."""

from googleapiclient.discovery import build
from google_auth import get_creds

SHEET_ID = "1Aa_Z6hd854sHRkKhkvFHvDrMAmuR09DtCm-51fjvdug"

COLUMNS = ["date", "category", "vendor", "description", "amount", "payment_method", "notes", "unpaid", "due_date", "receipt_drive_link", "reference_number", "original_currency", "original_amount", "fx_rate"]


def _row_values(txn):
    return [
        txn["date"], txn["category"], txn.get("vendor", ""), txn.get("description", ""),
        txn["amount"], txn.get("payment_method", ""), txn.get("notes", ""),
        "TRUE" if txn.get("unpaid") else "FALSE", txn.get("due_date") or "",
        txn.get("receipt_drive_link") or "", txn.get("reference_number") or "",
        txn.get("original_currency") or "", txn.get("original_amount") or "", txn.get("fx_rate") or "",
    ]


def append_row(txn):
    creds = get_creds()
    sheets = build("sheets", "v4", credentials=creds)
    result = sheets.spreadsheets().values().append(
        spreadsheetId=SHEET_ID, range="Expenses!A2", valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS", body={"values": [_row_values(txn)]},
    ).execute()
    # Extract the row number Sheets actually wrote to, e.g. "Expenses!A15:K15"
    updated_range = result["updates"]["updatedRange"]
    row_num = int(updated_range.split("!")[1].split(":")[0][1:])
    return row_num


def update_row(sheet_row, txn):
    creds = get_creds()
    sheets = build("sheets", "v4", credentials=creds)
    sheets.spreadsheets().values().update(
        spreadsheetId=SHEET_ID, range=f"Expenses!A{sheet_row}:N{sheet_row}", valueInputOption="USER_ENTERED",
        body={"values": [_row_values(txn)]},
    ).execute()


def clear_row(sheet_row):
    creds = get_creds()
    sheets = build("sheets", "v4", credentials=creds)
    sheets.spreadsheets().values().clear(
        spreadsheetId=SHEET_ID, range=f"Expenses!A{sheet_row}:N{sheet_row}",
    ).execute()
