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

"Language available on live" and "Live link" show what the LIVE site has for the same
temple (matched by slug). If the sheet has no such columns yet, their headers
are added after the last existing column; they are kept up to date like D/E.

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
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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
COL_LIVE_TR, COL_LIVE_LINK = "Language available on live", "Live link"
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

    desired  : [[temple_id, name, source, targets, audio, link, live_langs, live_link], ...]
    existing : the sheet's current rows INCLUDING the header

    Returns (updates, appends): updates are {"range", "values"} for the progress
    cells of an existing row (and any missing live headers), only where they
    actually changed; appends are whole rows to add at the bottom.
    """
    header = list(existing[0]) if existing else list(SHEET_HEADER)
    cols = _colmap(header)
    updates = []
    for name in (COL_LIVE_TR, COL_LIVE_LINK):   # add the live columns once, after the last one
        if name not in cols:
            cols[name] = len(header)
            header.append(name)
            updates.append({"range": f"{TAB}!{_a1(cols[name])}1", "values": [[name]]})
    i_id = cols.get(COL_ID, 1)
    i_tr, i_au = cols.get(COL_TR, 4), cols.get(COL_AUDIO, 5)
    i_ltr, i_llink = cols[COL_LIVE_TR], cols[COL_LIVE_LINK]
    cell = lambda row, i: str(row[i] if len(row) > i else "").strip()

    row_of = {}
    for i, row in enumerate(existing[1:], start=2):  # row 1 is the header
        tid = cell(row, i_id)
        if tid:
            row_of[tid] = i

    next_sr = len(existing) - 1  # highest Sr no currently used
    appends = []
    for tid, name, src, targets, audio, link, live_tr, live_link in desired:
        key = str(tid)
        if key in row_of:
            r = row_of[key]
            row = existing[r - 1]
            if (cell(row, i_tr), cell(row, i_au)) != (targets, audio):  # no write when unchanged
                updates.append({"range": f"{TAB}!{_a1(i_tr)}{r}:{_a1(i_au)}{r}",
                                "values": [[targets, audio]]})
            # the link cell reads back as its display text, which is the URL itself
            for i, want, value in ((i_ltr, live_tr, live_tr), (i_llink, live_link, _link(live_link))):
                if cell(row, i) != want:
                    updates.append({"range": f"{TAB}!{_a1(i)}{r}", "values": [[value]]})
        else:
            next_sr += 1
            new = [""] * len(header)
            for col, value in ((cols.get("Sr no", 0), next_sr), (i_id, tid), (cols.get(COL_NAME, 2), name),
                               (cols.get(COL_SRC, 3), src), (i_tr, targets), (i_au, audio),
                               (cols.get(COL_LINK, 6), _link(link)), (i_ltr, live_tr), (i_llink, _link(live_link))):
                new[col] = value
            appends.append(new)
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


# Google answers 503/429 in bursts. Every other network path in this project
# retries; this one did not, so each blip silently dropped that temple's row
# and the sheet drifted 268 rows behind over one overnight run.
_sheet_retry = retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type((httpx.HTTPError,)),
    reraise=True,
)


@_sheet_retry
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
    r = httpx.get(f"{API}/{settings.sheet_id}/values/{TAB}!A1:Z10000", headers=h, timeout=180)
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
         "Marathi, English", "http://a", "Marathi, English", "http://live/a"],
        ["7224", "Aabaji Maharaj Temple", "Marathi", "English", "", "http://b", "Not on live", ""],
        ["9087", "Aaravali Sun Temple", "Marathi", "English, Hindi", "", "http://c", "Marathi", "http://live/c"],  # new
    ]
    up, ap = plan(desired, existing)
    ranges = [u["range"] for u in up]
    # the sheet had no live columns: their headers go right after the last column (J) -> K, L
    assert ranges[:2] == ["Sheet1!K1", "Sheet1!L1"] and up[0]["values"] == [["Language available on live"]], up[:2]
    # 26445: progress changed -> E:F, plus both live cells
    assert "Sheet1!E2:F2" in ranges and up[ranges.index("Sheet1!E2:F2")]["values"] == [["English, Hindi, Kannada", "Marathi, English"]]
    assert up[ranges.index("Sheet1!K2")]["values"] == [["Marathi, English"]]
    assert up[ranges.index("Sheet1!L2")]["values"] == [['=HYPERLINK("http://live/a","http://live/a")']]
    # 7224: progress unchanged, only the new live cells are written
    assert "Sheet1!E3:F3" not in ranges and up[ranges.index("Sheet1!K3")]["values"] == [["Not on live"]]
    # the new temple is appended with every column in its place
    assert len(ap) == 1 and ap[0][:3] == [3, "9087", "Aaravali Sun Temple"], ap
    assert ap[0][6] == '=HYPERLINK("http://c","http://c")' and ap[0][10] == "Marathi" and ap[0][11].endswith('"http://live/c")'), ap
    # the approval columns (H, I, J) can never appear in a write payload
    assert not any("yes" in str(u["values"]) for u in up), "approval columns must never be written"
    assert not any(r[len("Sheet1!")] in "HIJ" for r in ranges), ranges
    # once the live columns exist and match, nothing at all is written
    synced = [header + ["Language available on live", "Live link"],
              [1, "26445", "x", "Marathi", "English", "", "http://a", "", "", "", "Marathi", "http://live/a"]]
    u3, a3 = plan([["26445", "x", "Marathi", "English", "", "http://a", "Marathi", "http://live/a"]], synced)
    assert u3 == [] and a3 == [], (u3, a3)
    assert _a1(0) == "A" and _a1(25) == "Z" and _a1(26) == "AA", "column letters"
    # a sheet whose columns moved must still be written correctly
    shifted = [["Temple ID", "Name", "Sr no", "Language translated into ", "Audio available", "Language available on live", "Live link"],
               ["26445", "x", 1, "English", "", "Marathi", "http://live/a"]]
    u2, _ = plan([["26445", "x", "Marathi", "English, Hindi", "Marathi", "http://a", "Marathi", "http://live/a"]], shifted)
    assert [u["range"] for u in u2] == ["Sheet1!D2:E2"], u2
    print("sheet_sync self-check OK")
