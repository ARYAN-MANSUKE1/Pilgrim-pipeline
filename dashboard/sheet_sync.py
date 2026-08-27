"""
Push temple progress into the team's Google Sheet.

The sheet is shared with the client, so writes are kept as narrow as possible.

A new temple is appended as a full row (Sr no, Temple ID, Name, Source language,
Language translated into, Audio available, Staging link). After that, the only
cells this code ever rewrites are "Language translated into" and "Audio
available" -- the two things that change as a temple progresses. Everything else
is fixed the moment the row is created, so a hand-edited name or staging link
survives.

Columns G, H, I -- "Approved by developers", "Approved by client", "Pushed on
the live website" -- are filled in by people and are never written at all.

Rows are matched on Temple ID (column B), so a temple keeps its row for life.
Nothing is ever reordered or deleted, because moving a row would carry the
approval marks to the wrong temple.

Setup (one-time):
  1. Create a service account in the GCP project, download its JSON key.
  2. Share the sheet with the service account's email as Editor.
  3. Set in .env:  GOOGLE_SA_JSON=C:/path/to/key.json
                   SHEET_ID=1Pv8r6LX...
"""

from __future__ import annotations

import threading

import httpx

from app.config import settings

SHEET_HEADER = [
    "Sr no", "Temple ID", "Name", "Source language ",
    "Language translated into ", "Audio available", "Staging link ",
    "Approved by developers ", "Approved by client ",
    "Pushed on the live website",
]
# Columns are located by header text, never by a hardcoded letter -- inserting a
# column in the sheet then can not silently shift writes onto the wrong cells.
COL_ID, COL_NAME, COL_SRC = "Temple ID", "Name", "Source language"
COL_TR, COL_AUDIO, COL_LINK = "Language translated into", "Audio available", "Staging link"
API = "https://sheets.googleapis.com/v4/spreadsheets"
TAB = "Sheet1"


def _token() -> str:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    if not settings.google_sa_json:
        raise RuntimeError("GOOGLE_SA_JSON is not set -- see the setup notes in this file")
    creds = service_account.Credentials.from_service_account_file(
        settings.google_sa_json, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    creds.refresh(Request())
    return creds.token


def _colmap(header: list) -> dict:
    """{normalised header text: 0-based index} for the sheet as it actually is."""
    return {str(h).strip(): i for i, h in enumerate(header)}


def _a1(idx: int) -> str:
    """0-based column index -> A1 letter (0->A). Sheets goes past Z at 26."""
    s, idx = "", idx
    while True:
        s = chr(ord("A") + idx % 26) + s
        idx = idx // 26 - 1
        if idx < 0:
            return s


def _link(url: str) -> str:
    """A HYPERLINK formula, not a bare URL: Sheets' auto-linking of plain text
    is only a display nicety and is lost the moment cell formatting is reset.
    A formula stays clickable regardless."""
    if not url:
        return ""
    safe = url.replace('"', "%22")
    return f'=HYPERLINK("{safe}","{safe}")'


def plan(desired: list[list], existing: list[list]) -> tuple[list[dict], list[list]]:
    """
    Work out the writes without touching the network -- so it can be tested dry.

    desired  : [[temple_id, name, source, targets, audio, link], ...], title order
    existing : the sheet's current rows INCLUDING the header

    Returns (updates, appends): updates are {"range", "values"} for D:E of an
    existing row, and only where they actually changed; appends are whole A-F
    rows to add at the bottom.
    """
    cols = _colmap(existing[0] if existing else SHEET_HEADER)
    i_id = cols.get(COL_ID, 1)
    i_tr, i_au = cols.get(COL_TR, 4), cols.get(COL_AUDIO, 5)
    cell = lambda row, i: (row[i] if len(row) > i else "").strip()

    row_of = {}
    for i, row in enumerate(existing[1:], start=2):  # row 1 is the header
        tid = cell(row, i_id)
        if tid:
            row_of[tid] = i

    next_sr = len(existing) - 1  # highest Sr no currently used
    updates, appends = [], []
    for tid, name, src, targets, audio, link in desired:
        key = str(tid)
        if key in row_of:
            r = row_of[key]
            row = existing[r - 1]
            if (cell(row, i_tr), cell(row, i_au)) != (targets, audio):  # no write when unchanged
                updates.append({"range": f"{TAB}!{_a1(i_tr)}{r}:{_a1(i_au)}{r}",
                                "values": [[targets, audio]]})
        else:
            next_sr += 1
            appends.append([next_sr, tid, name, src, targets, audio, _link(link)])
    return updates, appends


def _ensure_rows(headers: dict, needed: int) -> None:
    """Grow the grid if the appends wouldn't fit. OVERWRITE appends fail rather
    than extending the sheet, and the default grid is only 1000 rows."""
    r = httpx.get(f"{API}/{settings.sheet_id}", headers=headers, timeout=180,
                  params={"fields": "sheets.properties"})
    r.raise_for_status()
    props = r.json()["sheets"][0]["properties"]
    have = props["gridProperties"]["rowCount"]
    if needed <= have:
        return
    r = httpx.post(f"{API}/{settings.sheet_id}:batchUpdate", headers=headers, timeout=180,
                   json={"requests": [{"appendDimension": {
                       "sheetId": props["sheetId"], "dimension": "ROWS",
                       "length": needed - have + 50}}]})
    r.raise_for_status()


_sync_lock = threading.Lock()


def sync(desired: list[list]) -> dict:
    """Read the sheet, update the progress columns, append any new temples.

    Serialised: several job workers finish temples at once, and sync is a
    read-then-write -- two at a time could hand out the same Sr no to different
    temples, or append the same row twice."""
    if not (settings.google_sa_json and settings.sheet_id):
        return {"skipped": "GOOGLE_SA_JSON / SHEET_ID not configured"}

    with _sync_lock:
        return _sync(desired)


def _sync(desired: list[list]) -> dict:
    h = {"Authorization": f"Bearer {_token()}"}
    r = httpx.get(f"{API}/{settings.sheet_id}/values/{TAB}!A1:I10000", headers=h, timeout=180)
    r.raise_for_status()
    existing = r.json().get("values") or [SHEET_HEADER]

    updates, appends = plan(desired, existing)
    if appends:
        _ensure_rows(h, len(existing) + len(appends))
    if updates:
        r = httpx.post(f"{API}/{settings.sheet_id}/values:batchUpdate", headers=h, timeout=180,
                       json={"valueInputOption": "USER_ENTERED", "data": updates})
        r.raise_for_status()
    if appends:
        # OVERWRITE, not INSERT_ROWS: inserting a row makes Sheets copy the
        # formatting of the row above it, which dragged the green header style
        # down over every appended temple. Writing into the existing blank rows
        # keeps them at default formatting. Safe here because the sync only ever
        # appends below the last data row.
        r = httpx.post(f"{API}/{settings.sheet_id}/values/{TAB}!A1:append",
                       headers=h, timeout=180,
                       params={"valueInputOption": "USER_ENTERED",
                               "insertDataOption": "OVERWRITE"},
                       json={"values": appends})
        r.raise_for_status()
    return {"updated": len(updates), "appended": len(appends)}


if __name__ == "__main__":  # self-check: python -m dashboard.sheet_sync
    header = SHEET_HEADER
    existing = [
        header,
        [1, "26445", "A wooden Ganpati idol", "Marathi", "English, Hindi",
         "Marathi", "http://a", "yes", "yes", "yes"],
        [2, "7224", "Aabaji Maharaj Temple", "Marathi", "English", "", "http://b", "", "", ""],
    ]
    desired = [
        # gained a language AND a voice recording
        ["26445", "A wooden Ganpati idol", "Marathi", "English, Hindi, Kannada",
         "Marathi, English", "http://a"],
        ["7224", "Aabaji Maharaj Temple", "Marathi", "English", "", "http://b"],   # unchanged
        ["9087", "Aaravali Sun Temple", "Marathi", "English, Hindi", "", "http://c"],  # new
    ]
    up, ap = plan(desired, existing)
    # 26445 changed -> one E:F write; 7224 unchanged -> no write at all
    assert len(up) == 1 and len(ap) == 1, (up, ap)
    assert up[0]["range"] == "Sheet1!E2:F2", up[0]
    assert up[0]["values"] == [["English, Hindi, Kannada", "Marathi, English"]], up[0]
    assert ap[0][:3] == [3, "9087", "Aaravali Sun Temple"], ap[0]
    assert ap[0][6] == '=HYPERLINK("http://c","http://c")', ap[0]
    # the approval columns (H, I, J) can never appear in a write payload
    assert not any("yes" in str(u["values"]) for u in up), "approval columns must never be written"
    assert _a1(0) == "A" and _a1(25) == "Z" and _a1(26) == "AA", "column letters"
    # a sheet whose columns moved must still be written correctly
    shifted = [["Temple ID", "Name", "Sr no", "Language translated into ", "Audio available"],
               ["26445", "x", 1, "English", ""]]
    u2, _ = plan([["26445", "x", "Marathi", "English, Hindi", "Marathi", "http://a"]], shifted)
    assert u2[0]["range"] == "Sheet1!D2:E2", u2[0]
    print("sheet_sync self-check OK")
