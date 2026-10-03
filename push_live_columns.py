"""
One-off: write the two live columns (K:L) and the live-only temple rows into the
client sheet. Needs GOOGLE_SA_JSON (service-account key with Editor on the sheet)
and SHEET_ID in .env.

    python push_live_columns.py
"""
import csv

import httpx

from app.config import settings
from dashboard.sheet_sync import API, TAB, _ensure_rows, _token

cols = list(csv.reader(open("Live_columns_for_client_sheet.csv", encoding="utf-8-sig")))
extra = list(csv.reader(open("Live_only_rows_for_client_sheet.csv", encoding="utf-8-sig")))
h = {"Authorization": f"Bearer {_token()}"}
first_new = len(cols) + 1  # sheet row after the last existing temple
_ensure_rows(h, first_new + len(extra))  # the grid may end at the last temple
data = [
    {"range": f"{TAB}!K1:L{len(cols)}", "values": cols},
    {"range": f"{TAB}!A{first_new}:L{first_new + len(extra) - 1}", "values": extra},
]
r = httpx.post(f"{API}/{settings.sheet_id}/values:batchUpdate", headers=h, timeout=180,
               json={"valueInputOption": "USER_ENTERED", "data": data})
r.raise_for_status()
print(f"done: K1:L{len(cols)} filled, {len(extra)} live-only rows added from row {first_new}")
