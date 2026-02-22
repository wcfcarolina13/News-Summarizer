"""
Google Sheets Manager - Handles reading/writing to Google Sheets via Service Account

Setup:
1. Go to Google Cloud Console (https://console.cloud.google.com)
2. Create a project or select existing one
3. Enable the Google Sheets API
4. Create a Service Account (IAM & Admin > Service Accounts)
5. Create and download a JSON key for the service account
6. Save the JSON key as 'google_credentials.json' in the daily_audio_briefing folder
7. Share your Google Sheet with the service account email (found in the JSON file)
"""

import os
import sys
import json
from typing import List, Dict, Any, Optional

# Check for required packages
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False


SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def _find_credentials_file():
    """Find google_credentials.json, checking multiple locations."""
    # 1. Script/bundle directory
    script_dir = os.path.join(os.path.dirname(__file__), 'google_credentials.json')
    if os.path.exists(script_dir):
        return script_dir
    # 2. App data directory (frozen app stores creds here)
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            data_dir = os.path.expanduser('~/Library/Application Support/Daily Audio Briefing')
        elif sys.platform == 'win32':
            data_dir = os.path.join(os.environ.get('APPDATA', ''), 'Daily Audio Briefing')
        else:
            data_dir = os.path.expanduser('~/.daily-audio-briefing')
        data_path = os.path.join(data_dir, 'google_credentials.json')
        if os.path.exists(data_path):
            return data_path
    return script_dir  # Default (may not exist)

CREDENTIALS_FILE = _find_credentials_file()

# Cached service to avoid repeated discovery doc parsing + HTTP client creation
_cached_service = None
_cached_creds_source = None


def is_sheets_available() -> bool:
    """Check if Google Sheets integration is available (file or env var credentials)."""
    if not SHEETS_AVAILABLE:
        return False
    return os.path.exists(CREDENTIALS_FILE) or bool(os.environ.get('GOOGLE_CREDENTIALS_JSON'))


def get_missing_requirements() -> str:
    """Return a message about what's missing for Sheets integration."""
    issues = []
    if not SHEETS_AVAILABLE:
        issues.append("Required packages not installed. Run: pip install google-auth google-auth-oauthlib google-api-python-client")
    if not os.path.exists(CREDENTIALS_FILE) and not os.environ.get('GOOGLE_CREDENTIALS_JSON'):
        issues.append(f"No credentials found. Set GOOGLE_CREDENTIALS_JSON env var or place file at: {CREDENTIALS_FILE}")
    return "\n".join(issues) if issues else ""


def get_sheets_service():
    """Create and return a Google Sheets service instance.

    Caches the service at module level to avoid repeated discovery doc
    parsing and HTTP client creation. Service account tokens are refreshed
    internally by the google-auth library.

    Supports two credential sources:
    1. GOOGLE_CREDENTIALS_JSON env var (for server deployment)
    2. google_credentials.json file (for local development)
    """
    global _cached_service, _cached_creds_source

    if not SHEETS_AVAILABLE:
        raise ImportError("Google API packages not installed")

    # Determine current credential source
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    current_source = 'env' if creds_json else ('file' if os.path.exists(CREDENTIALS_FILE) else None)

    if current_source is None:
        raise FileNotFoundError(
            "No Google credentials found. Set GOOGLE_CREDENTIALS_JSON env var "
            f"or place credentials file at: {CREDENTIALS_FILE}"
        )

    # Return cached service if source hasn't changed
    if _cached_service is not None and _cached_creds_source == current_source:
        return _cached_service

    # Build fresh service
    if current_source == 'env':
        info = json.loads(creds_json)
        credentials = Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)

    _cached_service = build('sheets', 'v4', credentials=credentials)
    _cached_creds_source = current_source
    return _cached_service


def append_to_sheet(
    spreadsheet_id: str,
    range_name: str,
    values: List[List[Any]],
    value_input_option: str = 'USER_ENTERED'
) -> Dict[str, Any]:
    """
    Append rows to a Google Sheet.

    Args:
        spreadsheet_id: The ID of the spreadsheet (from the URL)
        range_name: The A1 notation of the range (e.g., 'Sheet1!A:Z' or just 'Sheet1')
        values: List of rows, where each row is a list of cell values
        value_input_option: How to interpret input ('RAW' or 'USER_ENTERED')

    Returns:
        API response dict with updates info
    """
    service = get_sheets_service()

    body = {
        'values': values
    }

    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption=value_input_option,
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()

    return result


def read_sheet(
    spreadsheet_id: str,
    range_name: str
) -> List[List[Any]]:
    """
    Read values from a Google Sheet.

    Args:
        spreadsheet_id: The ID of the spreadsheet
        range_name: The A1 notation of the range to read

    Returns:
        List of rows, where each row is a list of cell values
    """
    service = get_sheets_service()

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()

    return result.get('values', [])


def get_sheet_tab_names(spreadsheet_id: str) -> List[str]:
    """
    Get all tab (sheet) names from a Google Spreadsheet.

    Returns:
        List of sheet tab names, e.g. ['Sheet1', 'local-Daemon', 'Archive']
    """
    service = get_sheets_service()
    metadata = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        fields='sheets.properties.title'
    ).execute()
    return [s['properties']['title'] for s in metadata.get('sheets', [])]


def resolve_sheet_name(spreadsheet_id: str, configured_name: str) -> Optional[str]:
    """
    Verify a sheet tab name exists. If not, try to find the correct tab.

    Strategy:
    1. If configured_name exists → return it (no change needed)
    2. If only one tab exists → return that tab's name (user probably renamed it)
    3. If multiple tabs → return None (ambiguous, can't auto-resolve)

    Returns:
        The resolved sheet name, or None if it can't be determined.
    """
    try:
        tabs = get_sheet_tab_names(spreadsheet_id)
        if not tabs:
            return None

        # Exact match — all good
        if configured_name in tabs:
            return configured_name

        # Single tab — user renamed it, use the new name
        if len(tabs) == 1:
            print(f"[sheets_manager] Tab '{configured_name}' not found. "
                  f"Auto-resolved to only tab: '{tabs[0]}'")
            return tabs[0]

        # Multiple tabs — can't auto-resolve
        print(f"[sheets_manager] Tab '{configured_name}' not found. "
              f"Available tabs: {tabs}. Cannot auto-resolve.")
        return None
    except Exception as e:
        print(f"[sheets_manager] Warning: Could not resolve sheet name: {e}")
        return None


def create_sheet_tab(spreadsheet_id: str, tab_name: str) -> bool:
    """
    Create a new tab (sheet) in a Google Spreadsheet.

    Args:
        spreadsheet_id: The Google Sheet ID
        tab_name: Name for the new tab

    Returns:
        True if created successfully, False otherwise
    """
    try:
        service = get_sheets_service()
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': [{'addSheet': {'properties': {'title': tab_name}}}]}
        ).execute()
        print(f"[sheets_manager] Created new tab: '{tab_name}'")
        return True
    except HttpError as e:
        print(f"[sheets_manager] Error creating tab '{tab_name}': {e}")
        return False


def get_sheet_headers(spreadsheet_id: str, sheet_name: str = 'Sheet1') -> List[str]:
    """Get the header row from a sheet."""
    values = read_sheet(spreadsheet_id, f'{sheet_name}!1:1')
    return values[0] if values else []


def get_last_date_in_sheet(spreadsheet_id: str, sheet_name: str = 'Sheet1',
                           date_column: str = 'date_published') -> str:
    """
    Find the most recent date_published value in a sheet.

    Returns:
        Date string (YYYY-MM-DD) or "" if no dates found.
    """
    try:
        headers = get_sheet_headers(spreadsheet_id, sheet_name)
        if not headers or date_column not in headers:
            return ""

        col_idx = headers.index(date_column)
        col_letter = _col_letter(col_idx + 1)

        # Read just the date column
        values = read_sheet(spreadsheet_id, f'{sheet_name}!{col_letter}:{col_letter}')
        if not values or len(values) < 2:
            return ""

        # Find the latest date (skip header)
        latest = ""
        for row in values[1:]:
            if row and row[0].strip():
                date_val = row[0].strip()[:10]  # Take YYYY-MM-DD part
                if date_val > latest:
                    latest = date_val

        return latest
    except Exception as e:
        print(f"[sheets_manager] Error reading last date: {e}")
        return ""


def get_covered_dates_in_sheet(spreadsheet_id: str, sheet_name: str = 'Sheet1',
                               date_column: str = 'date_published') -> set:
    """
    Get the set of all unique dates already present in a sheet.

    Returns:
        Set of date strings (YYYY-MM-DD) that have at least one row in the sheet.
    """
    try:
        headers = get_sheet_headers(spreadsheet_id, sheet_name)
        if not headers or date_column not in headers:
            return set()

        col_idx = headers.index(date_column)
        col_letter = _col_letter(col_idx + 1)

        values = read_sheet(spreadsheet_id, f'{sheet_name}!{col_letter}:{col_letter}')
        if not values or len(values) < 2:
            return set()

        dates = set()
        for row in values[1:]:
            if row and row[0].strip():
                date_val = row[0].strip()[:10]
                if len(date_val) == 10 and date_val[4] == '-':
                    dates.add(date_val)

        return dates
    except Exception as e:
        print(f"[sheets_manager] Error reading covered dates: {e}")
        return set()


def delete_empty_rows(spreadsheet_id: str, sheet_name: str = 'Sheet1') -> int:
    """
    Delete rows that are completely empty (no title, no URL, no date) from a sheet.
    Preserves the header row and any row with meaningful data.

    Returns:
        Number of rows deleted.
    """
    try:
        service = get_sheets_service()

        # Get sheet metadata to find numeric sheetId
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_gid = None
        for s in meta.get('sheets', []):
            if s['properties']['title'] == sheet_name:
                sheet_gid = s['properties']['sheetId']
                break
        if sheet_gid is None:
            print(f"[sheets_manager] Tab '{sheet_name}' not found for empty row cleanup")
            return 0

        # Read all data
        all_data = read_sheet(spreadsheet_id, f'{sheet_name}!A:Z')
        if not all_data or len(all_data) < 2:
            return 0

        # Find empty rows (skip header at index 0)
        # A row is "empty" if it has no content in any cell (or only FALSE/empty strings)
        empty_row_indices = []
        for i in range(1, len(all_data)):
            row = all_data[i]
            has_content = False
            for cell in row:
                val = str(cell).strip() if cell else ''
                if val and val.upper() != 'FALSE':
                    has_content = True
                    break
            if not has_content:
                empty_row_indices.append(i)

        if not empty_row_indices:
            return 0

        # Build batch delete requests — must go in REVERSE order to keep indices valid
        requests_list = []
        # Group consecutive rows into ranges for efficiency
        ranges = []
        start = empty_row_indices[0]
        end = start
        for idx in empty_row_indices[1:]:
            if idx == end + 1:
                end = idx
            else:
                ranges.append((start, end))
                start = idx
                end = idx
        ranges.append((start, end))

        # Reverse so we delete from bottom to top
        for start, end in reversed(ranges):
            requests_list.append({
                'deleteDimension': {
                    'range': {
                        'sheetId': sheet_gid,
                        'dimension': 'ROWS',
                        'startIndex': start,  # 0-based, inclusive
                        'endIndex': end + 1,  # exclusive
                    }
                }
            })

        # Execute batch
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests_list}
        ).execute()

        print(f"[sheets_manager] Deleted {len(empty_row_indices)} empty rows in {len(ranges)} ranges")
        return len(empty_row_indices)

    except Exception as e:
        print(f"[sheets_manager] Error deleting empty rows: {e}")
        return 0



def get_sheet_headers_with_format(spreadsheet_id: str, sheet_name: str = 'Sheet1') -> List[Dict[str, Any]]:
    """Get headers with formatting info (data validation like checkboxes).

    Returns a list of dicts: [{"name": "url", "format": "text"}, {"name": "Processed", "format": "checkbox"}, ...]
    """
    try:
        service = get_sheets_service()
        # Get sheet metadata to find sheetId
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheet_id = None
        for s in meta.get('sheets', []):
            if s['properties']['title'] == sheet_name:
                sheet_id = s['properties']['sheetId']
                break
        if sheet_id is None:
            return []

        # Get headers (text values)
        headers = get_sheet_headers(spreadsheet_id, sheet_name)
        if not headers:
            return []

        # Get data validation for column 2 (row index 1, first data row) to detect checkboxes
        # We check row 2 because the header row itself doesn't have data validation
        resp = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            ranges=[f'{sheet_name}!A2:{_col_letter(len(headers))}2'],
            fields='sheets.data.rowData.values.dataValidation'
        ).execute()

        # Parse validation rules
        formats = []
        row_data = []
        try:
            row_data = resp['sheets'][0]['data'][0].get('rowData', [{}])[0].get('values', [])
        except (KeyError, IndexError):
            pass

        for i, name in enumerate(headers):
            fmt = "text"
            if i < len(row_data):
                dv = row_data[i].get('dataValidation', {})
                condition = dv.get('condition', {})
                if condition.get('type') == 'BOOLEAN':
                    fmt = "checkbox"
            formats.append({"name": name, "format": fmt})

        return formats
    except Exception as e:
        print(f"[sheets_manager] Error reading header formats: {e}")
        # Fall back to plain headers without format info
        headers = get_sheet_headers(spreadsheet_id, sheet_name)
        return [{"name": h, "format": "text"} for h in headers]


def _col_letter(n: int) -> str:
    """Convert 1-based column number to letter (1→A, 26→Z, 27→AA)."""
    result = ''
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def get_existing_urls(spreadsheet_id: str, sheet_name: str = 'Sheet1', url_column: str = 'url') -> set:
    """
    Read all existing URLs from a sheet to enable deduplication.

    Args:
        spreadsheet_id: The Google Sheet ID
        sheet_name: Name of the sheet tab
        url_column: Name of the column containing URLs

    Returns:
        Set of URL strings already in the sheet
    """
    try:
        # Read headers to find URL column index
        headers = get_sheet_headers(spreadsheet_id, sheet_name)
        if not headers or url_column not in headers:
            return set()

        url_idx = headers.index(url_column)
        col_letter = _col_letter(url_idx + 1)

        # Read just the URL column (much faster than A:Z for large sheets)
        all_data = read_sheet(spreadsheet_id, f'{sheet_name}!{col_letter}:{col_letter}')
        if not all_data or len(all_data) < 2:  # header only or empty
            return set()

        # Extract URLs (skip header row), ignoring empty rows
        existing = set()
        for row in all_data[1:]:
            if row and row[0] and row[0].strip():
                existing.add(row[0].strip())

        return existing
    except Exception as e:
        print(f"[sheets_manager] Warning: Could not read existing URLs for dedup: {e}")
        return set()


def deduplicate_sheet(
    spreadsheet_id: str,
    sheet_name: str = 'Sheet1',
    url_column: str = 'url'
) -> Dict[str, Any]:
    """
    Remove duplicate rows from an existing Google Sheet, keeping the first occurrence.

    Args:
        spreadsheet_id: The Google Sheet ID
        sheet_name: Name of the sheet tab
        url_column: Column to use for deduplication

    Returns:
        Dict with before_count, after_count, removed_count
    """
    service = get_sheets_service()

    # Read all data
    all_data = read_sheet(spreadsheet_id, f'{sheet_name}!A:Z')
    if not all_data or len(all_data) < 2:
        return {'before_count': 0, 'after_count': 0, 'removed_count': 0}

    headers = all_data[0]
    data_rows = all_data[1:]
    before_count = len(data_rows)

    # Find URL column index
    if url_column not in headers:
        print(f"[sheets_manager] Column '{url_column}' not found in headers: {headers}")
        return {'before_count': before_count, 'after_count': before_count, 'removed_count': 0, 'error': f'Column {url_column} not found'}

    url_idx = headers.index(url_column)

    # Deduplicate keeping first occurrence + remove empty rows
    seen = set()
    unique_rows = []
    for row in data_rows:
        # Skip completely empty rows (only FALSE or blank cells)
        has_content = any(
            str(c).strip() and str(c).strip().upper() != 'FALSE'
            for c in row
        )
        if not has_content:
            continue

        url_val = row[url_idx].strip() if len(row) > url_idx and row[url_idx] else ''
        if url_val and url_val in seen:
            continue  # Skip duplicate
        if url_val:
            seen.add(url_val)
        unique_rows.append(row)

    removed_count = before_count - len(unique_rows)

    if removed_count == 0:
        return {'before_count': before_count, 'after_count': before_count, 'removed_count': 0}

    # Clear the sheet and rewrite with deduplicated data
    # First, get the sheet ID (not spreadsheet ID) for the clear request
    try:
        # Clear all data rows (keep headers)
        clear_range = f'{sheet_name}!A2:Z'
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=clear_range,
            body={}
        ).execute()

        # Write back deduplicated data
        if unique_rows:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!A2',
                valueInputOption='USER_ENTERED',
                body={'values': unique_rows}
            ).execute()

        print(f"[sheets_manager] Dedup complete: {before_count} -> {len(unique_rows)} rows ({removed_count} removed)")
    except HttpError as e:
        print(f"[sheets_manager] Error during dedup write-back: {e}")
        return {'before_count': before_count, 'after_count': before_count, 'removed_count': 0, 'error': str(e)}

    return {
        'before_count': before_count,
        'after_count': len(unique_rows),
        'removed_count': removed_count
    }


def export_items_to_sheet(
    items: List[Any],
    spreadsheet_id: str,
    sheet_name: str = 'Sheet1',
    columns: Optional[List[str]] = None,
    include_headers: bool = True,
    deduplicate: bool = True,
    dedup_column: str = 'url'
) -> Dict[str, Any]:
    """
    Export extracted items to a Google Sheet with optional deduplication.

    Args:
        items: List of ExtractedItem objects
        spreadsheet_id: The Google Sheet ID
        sheet_name: Name of the sheet tab
        columns: List of column names to export (uses item's to_dict keys if not specified)
        include_headers: If True, add headers if sheet is empty. If False, skip headers entirely.
                        Set to False for append-only mode where headers already exist.
        deduplicate: If True, skip items whose URL already exists in the sheet (default: True)
        dedup_column: Column name to use for deduplication (default: 'url')

    Returns:
        API response with number of rows added
    """
    if not items:
        return {'updates': {'updatedRows': 0}}

    # Convert items to dicts
    rows_data = []
    for item in items:
        if hasattr(item, 'to_dict'):
            rows_data.append(item.to_dict())
        elif isinstance(item, dict):
            rows_data.append(item)
        else:
            continue

    if not rows_data:
        return {'updates': {'updatedRows': 0}}

    # Determine columns
    if columns:
        cols = columns
    else:
        # Get all unique keys from items
        cols = list(rows_data[0].keys())

    # Ensure headers exist (idempotent — only adds if row 1 is empty)
    if include_headers:
        try:
            existing_headers = get_sheet_headers(spreadsheet_id, sheet_name)
            if not existing_headers:
                append_to_sheet(spreadsheet_id, f'{sheet_name}!A1', [cols])
                print(f"[sheets_manager] Added header row: {cols}")
            # else: headers already present, skip
        except HttpError as e:
            print(f"[sheets_manager] Could not check headers, attempting to add: {e}")
            try:
                append_to_sheet(spreadsheet_id, f'{sheet_name}!A1', [cols])
            except HttpError:
                pass  # Tab may not exist — resolve_sheet_name should handle this

    # If the sheet already has headers, align data to the SHEET's column order
    # (not the config's column order) so appended rows match existing columns.
    try:
        existing_headers = get_sheet_headers(spreadsheet_id, sheet_name)
        if existing_headers:
            print(f"[sheets_manager] Aligning to sheet headers ({len(existing_headers)} cols)")
            cols = existing_headers
    except Exception:
        pass  # Fall back to config columns

    # Deduplication: skip items whose URL already exists in the sheet
    if deduplicate and dedup_column in cols:
        existing_urls = get_existing_urls(spreadsheet_id, sheet_name, dedup_column)
        if existing_urls:
            original_count = len(rows_data)
            rows_data = [r for r in rows_data if r.get(dedup_column, '').strip() not in existing_urls]
            skipped = original_count - len(rows_data)
            if skipped > 0:
                print(f"[sheets_manager] Dedup: skipped {skipped} items already in sheet ({len(rows_data)} new)")

    if not rows_data:
        return {'updates': {'updatedRows': 0}, 'dedup_skipped': 'all items already exist'}

    # Convert items to rows matching column order
    rows = []
    for item_dict in rows_data:
        row = [item_dict.get(col, '') for col in cols]
        rows.append(row)

    # Append data
    result = append_to_sheet(spreadsheet_id, f'{sheet_name}!A:A', rows)

    return result


def extract_sheet_id(url_or_id: str) -> str:
    """
    Extract the spreadsheet ID from a Google Sheets URL or return the ID if already extracted.

    Examples:
        https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit
        -> 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
    """
    if '/spreadsheets/d/' in url_or_id:
        # Extract ID from URL
        start = url_or_id.find('/spreadsheets/d/') + len('/spreadsheets/d/')
        end = url_or_id.find('/', start)
        if end == -1:
            end = url_or_id.find('?', start)
        if end == -1:
            end = len(url_or_id)
        return url_or_id[start:end]
    else:
        # Assume it's already an ID
        return url_or_id
