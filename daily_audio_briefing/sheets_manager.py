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
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'google_credentials.json')


def is_sheets_available() -> bool:
    """Check if Google Sheets integration is available."""
    return SHEETS_AVAILABLE and os.path.exists(CREDENTIALS_FILE)


def get_missing_requirements() -> str:
    """Return a message about what's missing for Sheets integration."""
    issues = []
    if not SHEETS_AVAILABLE:
        issues.append("Required packages not installed. Run: pip install google-auth google-auth-oauthlib google-api-python-client")
    if not os.path.exists(CREDENTIALS_FILE):
        issues.append(f"Credentials file not found at: {CREDENTIALS_FILE}")
    return "\n".join(issues) if issues else ""


def get_sheets_service():
    """Create and return a Google Sheets service instance."""
    if not SHEETS_AVAILABLE:
        raise ImportError("Google API packages not installed")

    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Credentials file not found: {CREDENTIALS_FILE}")

    credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    return service


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


def get_sheet_headers(spreadsheet_id: str, sheet_name: str = 'Sheet1') -> List[str]:
    """Get the header row from a sheet."""
    values = read_sheet(spreadsheet_id, f'{sheet_name}!1:1')
    return values[0] if values else []


def export_items_to_sheet(
    items: List[Any],
    spreadsheet_id: str,
    sheet_name: str = 'Sheet1',
    columns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Export extracted items to a Google Sheet.

    Args:
        items: List of ExtractedItem objects
        spreadsheet_id: The Google Sheet ID
        sheet_name: Name of the sheet tab
        columns: List of column names to export (uses item's to_dict keys if not specified)

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

    # Check if sheet has headers, if not add them
    try:
        existing_headers = get_sheet_headers(spreadsheet_id, sheet_name)
        if not existing_headers:
            # Add header row first
            append_to_sheet(spreadsheet_id, f'{sheet_name}!A1', [cols])
    except HttpError:
        # Sheet might be empty or not exist, try adding headers
        append_to_sheet(spreadsheet_id, f'{sheet_name}!A1', [cols])

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
