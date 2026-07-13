"""
sheet_summary.py

Pushes computed Revenue/Expenses/Profit into a "Summary" tab on the same
spreadsheet - one-directional (local/CI -> Sheet), matching the MannaHouse
project's sheet_export.py pattern for computed (not hand-entered) views.
Safe to call repeatedly - clears and rewrites the tab each time.
"""

from googleapiclient.discovery import build

SHEET_ID = "1Aa_Z6hd854sHRkKhkvFHvDrMAmuR09DtCm-51fjvdug"
TAB_NAME = "Summary"


def _ensure_tab(sheets):
    meta = sheets.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    for sheet in meta["sheets"]:
        if sheet["properties"]["title"] == TAB_NAME:
            return sheet["properties"]["sheetId"]
    result = sheets.spreadsheets().batchUpdate(
        spreadsheetId=SHEET_ID,
        body={"requests": [{"addSheet": {"properties": {"title": TAB_NAME}}}]},
    ).execute()
    return result["replies"][0]["addSheet"]["properties"]["sheetId"]


def push_summary(creds, monthly, mtd, ytd, total_ap):
    sheets = build("sheets", "v4", credentials=creds)
    tab_id = _ensure_tab(sheets)

    rows = [["Month", "Revenue", "Expenses", "Profit"]]
    for m in monthly:
        rows.append([m["month"], m["revenue"], m["expenses"], m["profit"]])
    rows.append([])
    rows.append(["Month-to-date", "Revenue", mtd["revenue"]])
    rows.append(["Month-to-date", "Expenses", mtd["expenses"]])
    rows.append(["Month-to-date", "Profit", mtd["profit"]])
    rows.append(["Year-to-date", "Revenue", ytd["revenue"]])
    rows.append(["Year-to-date", "Expenses", ytd["expenses"]])
    rows.append(["Year-to-date", "Profit", ytd["profit"]])
    rows.append(["Open Accounts Payable", "", total_ap])

    sheets.spreadsheets().values().clear(spreadsheetId=SHEET_ID, range=f"{TAB_NAME}!A:Z").execute()
    sheets.spreadsheets().values().update(
        spreadsheetId=SHEET_ID, range=f"{TAB_NAME}!A1", valueInputOption="USER_ENTERED",
        body={"values": rows},
    ).execute()

    sheets.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={"requests": [
        {"repeatCell": {
            "range": {"sheetId": tab_id, "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.92, "green": 0.89, "blue": 0.82}}},
            "fields": "userEnteredFormat(textFormat,backgroundColor)",
        }},
        {"updateDimensionProperties": {"range": {"sheetId": tab_id, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 4}, "properties": {"pixelSize": 130}, "fields": "pixelSize"}},
    ]}).execute()
