"""
Google Drive Manager - Handles uploading audio files to Google Drive via OAuth2.

Setup:
1. Enable the Google Drive API in Google Cloud Console
2. Create an OAuth 2.0 Client ID (Desktop app type)
3. Download the client secret JSON and save as 'drive_client_secret.json'
   next to this file (or in the app data directory for frozen builds).
4. User signs in via "Sign in with Google" button in Settings.

Auth flow:
- First time: opens browser for Google consent → stores refresh token locally
- Subsequent: uses stored refresh token (no browser needed)
- Token file: 'drive_token.json' in the app data directory
"""

import os
import sys
import json
import glob
import mimetypes
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


# Check for required packages
try:
    from google.oauth2.credentials import Credentials as OAuthCredentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
    DRIVE_AVAILABLE = True
except ImportError:
    DRIVE_AVAILABLE = False


# OAuth scope — only files/folders created by this app
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Cached service to avoid repeated auth + discovery doc parsing
_cached_service = None


def _get_data_directory() -> str:
    """Get the app's data directory for storing tokens."""
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            return os.path.expanduser('~/Library/Application Support/Daily Audio Briefing')
        elif sys.platform == 'win32':
            return os.path.join(os.environ.get('APPDATA', ''), 'Daily Audio Briefing')
        else:
            return os.path.expanduser('~/.daily-audio-briefing')
    return os.path.dirname(os.path.abspath(__file__))


def _find_client_secret_file() -> str:
    """Find drive_client_secret.json, checking multiple locations."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drive_client_secret.json'),
        os.path.join(_get_data_directory(), 'drive_client_secret.json'),
    ]
    # Frozen app: also check the bundle
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidates.insert(0, os.path.join(sys._MEIPASS, 'drive_client_secret.json'))
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]  # Default path (may not exist)


def _get_token_path() -> str:
    """Path to the stored OAuth token file."""
    return os.path.join(_get_data_directory(), 'drive_token.json')


CLIENT_SECRET_FILE = _find_client_secret_file()


def is_drive_available() -> bool:
    """Check if Google Drive integration is possible (libs + client secret present)."""
    if not DRIVE_AVAILABLE:
        return False
    return os.path.exists(CLIENT_SECRET_FILE)


def is_signed_in() -> bool:
    """Check if the user has a valid (possibly expired but refreshable) token."""
    token_path = _get_token_path()
    if not os.path.exists(token_path):
        return False
    try:
        creds = OAuthCredentials.from_authorized_user_file(token_path, SCOPES)
        # Has a refresh token = can get new access tokens
        return creds.refresh_token is not None
    except Exception:
        return False


def get_user_email() -> Optional[str]:
    """Get the signed-in user's email from the stored token."""
    token_path = _get_token_path()
    if not os.path.exists(token_path):
        return None
    try:
        with open(token_path, 'r') as f:
            data = json.load(f)
        return data.get('_user_email')
    except Exception:
        return None


def sign_in() -> Dict[str, Any]:
    """Run the OAuth2 sign-in flow (opens browser).

    Returns:
        Dict with: success (bool), email (str or None), error (str or None).
    """
    if not DRIVE_AVAILABLE:
        return {'success': False, 'email': None, 'error': 'Google API packages not installed'}
    if not os.path.exists(CLIENT_SECRET_FILE):
        return {'success': False, 'email': None,
                'error': f'Client secret not found: {CLIENT_SECRET_FILE}'}

    try:
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)

        # Get user info (email) for display
        email = None
        try:
            service = build('oauth2', 'v2', credentials=creds)
            user_info = service.userinfo().get().execute()
            email = user_info.get('email')
        except Exception:
            pass

        # Save token + email
        token_data = json.loads(creds.to_json())
        if email:
            token_data['_user_email'] = email

        token_path = _get_token_path()
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'w') as f:
            json.dump(token_data, f)
        os.chmod(token_path, 0o600)  # Owner-only read/write

        # Clear cached service so it picks up new creds
        global _cached_service
        _cached_service = None

        return {'success': True, 'email': email, 'error': None}

    except Exception as e:
        return {'success': False, 'email': None, 'error': str(e)}


def sign_out():
    """Revoke OAuth token with Google, then remove stored token file."""
    global _cached_service
    _cached_service = None
    token_path = _get_token_path()
    if os.path.exists(token_path):
        # Attempt to revoke the token server-side so it can't be reused if leaked
        try:
            import requests as _requests
            with open(token_path, 'r') as f:
                token_data = json.load(f)
            # Prefer access_token, fall back to refresh_token
            token = token_data.get('token') or token_data.get('refresh_token')
            if token:
                _requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': token},
                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                    timeout=5
                )
        except Exception:
            pass  # Best-effort revocation — still delete local file
        os.remove(token_path)


def get_drive_service():
    """Create and return a cached Google Drive service using OAuth2 user credentials.

    Automatically refreshes expired tokens using the stored refresh token.
    Raises RuntimeError if not signed in.
    """
    global _cached_service

    if not DRIVE_AVAILABLE:
        raise RuntimeError("Google API packages not installed")

    if _cached_service is not None:
        return _cached_service

    token_path = _get_token_path()
    if not os.path.exists(token_path):
        raise RuntimeError("Not signed in. Click 'Sign in with Google' in Settings.")

    creds = OAuthCredentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            token_data = json.loads(creds.to_json())
            # Preserve email
            try:
                with open(token_path, 'r') as f:
                    old_data = json.load(f)
                if '_user_email' in old_data:
                    token_data['_user_email'] = old_data['_user_email']
            except Exception:
                pass
            with open(token_path, 'w') as f:
                json.dump(token_data, f)
            os.chmod(token_path, 0o600)  # Owner-only read/write
        except Exception as e:
            raise RuntimeError(f"Token refresh failed: {e}. Try signing in again.")

    if not creds.valid and not creds.refresh_token:
        raise RuntimeError("Token expired and no refresh token. Please sign in again.")

    service = build('drive', 'v3', credentials=creds)
    _cached_service = service
    return service


def get_or_create_folder(folder_name: str, parent_id: str = 'root') -> str:
    """Find an existing folder by name under parent, or create it.

    Args:
        folder_name: Name of the folder to find/create.
        parent_id: Drive ID of the parent folder ('root' for top-level).

    Returns:
        The Drive folder ID.
    """
    service = get_drive_service()

    # Search for existing folder
    query = (
        f"name = '{folder_name}' "
        f"and '{parent_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    results = service.files().list(
        q=query, spaces='drive', fields='files(id, name)', pageSize=1
    ).execute()

    files = results.get('files', [])
    if files:
        return files[0]['id']

    # Create new folder
    metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=metadata, fields='id').execute()
    return folder['id']


def file_exists_in_folder(filename: str, folder_id: str) -> Optional[str]:
    """Check if a file with the given name exists in a folder.

    Returns the file's Drive ID if found, None otherwise.
    """
    service = get_drive_service()
    query = (
        f"name = '{filename}' "
        f"and '{folder_id}' in parents "
        f"and trashed = false"
    )
    results = service.files().list(
        q=query, spaces='drive', fields='files(id)', pageSize=1
    ).execute()
    files = results.get('files', [])
    return files[0]['id'] if files else None


def upload_file(local_path: str, folder_id: str, skip_existing: bool = True) -> Dict[str, Any]:
    """Upload a local file to a Drive folder.

    Returns:
        Dict with keys: id, name, size_bytes, status ('uploaded'|'skipped'|'error').
    """
    filename = os.path.basename(local_path)

    if skip_existing:
        existing_id = file_exists_in_folder(filename, folder_id)
        if existing_id:
            return {
                'id': existing_id,
                'name': filename,
                'status': 'skipped',
                'reason': 'already exists'
            }

    mime_type = mimetypes.guess_type(local_path)[0] or 'application/octet-stream'
    media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
    metadata = {
        'name': filename,
        'parents': [folder_id]
    }

    service = get_drive_service()
    try:
        uploaded = service.files().create(
            body=metadata, media_body=media, fields='id, name, size'
        ).execute()
        return {
            'id': uploaded['id'],
            'name': uploaded['name'],
            'size_bytes': int(uploaded.get('size', 0)),
            'status': 'uploaded'
        }
    except HttpError as e:
        return {
            'name': filename,
            'status': 'error',
            'reason': str(e)
        }


def extract_folder_id_from_url(url_or_id: str) -> str:
    """Extract a Google Drive folder ID from a URL or return the ID as-is.

    Accepts:
        - Full URL: https://drive.google.com/drive/folders/ABC123?usp=sharing
        - Just the ID: ABC123
    """
    if not url_or_id:
        return ""
    url_or_id = url_or_id.strip()
    if '/folders/' in url_or_id:
        part = url_or_id.split('/folders/')[-1]
        return part.split('?')[0].split('#')[0].strip('/')
    return url_or_id


def verify_folder_access(folder_id: str) -> Dict[str, Any]:
    """Verify the signed-in user can access a folder.

    Returns:
        Dict with: accessible (bool), name (str or None), error (str or None).
    """
    if not folder_id:
        return {'accessible': False, 'name': None, 'error': 'No folder ID provided'}
    service = get_drive_service()
    try:
        info = service.files().get(
            fileId=folder_id, fields='id, name, mimeType'
        ).execute()
        if info.get('mimeType') != 'application/vnd.google-apps.folder':
            return {'accessible': False, 'name': info.get('name'), 'error': 'Not a folder'}
        return {'accessible': True, 'name': info.get('name'), 'error': None}
    except HttpError as e:
        if e.resp.status == 404:
            return {'accessible': False, 'name': None,
                    'error': 'Folder not found or no access.'}
        return {'accessible': False, 'name': None, 'error': str(e)}


def sync_week_folders(local_base_path: str,
                      root_folder_name: str = "Daily Audio Briefing",
                      shared_folder_id: str = "",
                      status_callback=None) -> List[str]:
    """Sync all Week_* folders and their audio files to Google Drive.

    If shared_folder_id is provided, creates structure inside that folder:
        <shared_folder> / <root_folder_name> / Week_N_YYYY / audio_files
    Otherwise creates at Drive root:
        <root_folder_name> / Week_N_YYYY / audio_files
    """
    log = []

    def _status(msg, color="gray"):
        log.append(msg)
        if status_callback:
            status_callback(msg, color)

    _status("Connecting to Drive...", "orange")

    if shared_folder_id:
        check = verify_folder_access(shared_folder_id)
        if not check['accessible']:
            _status(f"Cannot access Drive folder: {check['error']}", "red")
            return log
        root_id = get_or_create_folder(root_folder_name, parent_id=shared_folder_id)
        _status(f"Using folder: {check['name']} / {root_folder_name}", "green")
    else:
        root_id = get_or_create_folder(root_folder_name)
        _status(f"Root folder ready: {root_folder_name}", "green")

    # Find local Week_* folders
    week_folders = sorted(glob.glob(os.path.join(local_base_path, "Week_*")))
    if not week_folders:
        _status("No weekly folders found locally.", "orange")
        return log

    for local_week in week_folders:
        week_name = os.path.basename(local_week)
        if not os.path.isdir(local_week):
            continue

        audio_files = (
            glob.glob(os.path.join(local_week, "*.mp3")) +
            glob.glob(os.path.join(local_week, "*.wav"))
        )
        if not audio_files:
            continue

        _status(f"Syncing {week_name} ({len(audio_files)} files)...", "orange")
        week_id = get_or_create_folder(week_name, parent_id=root_id)

        for local_file in audio_files:
            fname = os.path.basename(local_file)
            result = upload_file(local_file, week_id)
            if result['status'] == 'uploaded':
                size_mb = result.get('size_bytes', 0) / (1024 * 1024)
                _status(f"  Uploaded: {fname} ({size_mb:.1f}MB)", "green")
            elif result['status'] == 'skipped':
                _status(f"  Skipped (exists): {fname}", "gray")
            else:
                _status(f"  Error: {fname} — {result.get('reason', 'unknown')[:60]}", "red")

    _status("Sync complete.", "green")
    return log


def get_storage_quota() -> Dict[str, Any]:
    """Return Google Drive storage quota information."""
    service = get_drive_service()
    about = service.about().get(fields='storageQuota').execute()
    quota = about.get('storageQuota', {})

    used = int(quota.get('usage', 0))
    total = int(quota.get('limit', 0))
    used_gb = used / (1024 ** 3)
    total_gb = total / (1024 ** 3) if total else 0
    percent = (used / total * 100) if total else 0

    return {
        'used_bytes': used,
        'total_bytes': total,
        'used_gb': used_gb,
        'total_gb': total_gb,
        'percent_used': percent
    }


def list_old_audio_files(root_folder_name: str = "Daily Audio Briefing",
                         before_days: int = 30,
                         shared_folder_id: str = "") -> List[Dict[str, Any]]:
    """List audio files older than N days in the Drive folder structure."""
    service = get_drive_service()
    cutoff = (datetime.utcnow() - timedelta(days=before_days)).isoformat() + 'Z'

    # Find the app's root folder
    if shared_folder_id:
        query = (
            f"name = '{root_folder_name}' "
            f"and '{shared_folder_id}' in parents "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
    else:
        query = (
            f"name = '{root_folder_name}' "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
    results = service.files().list(q=query, spaces='drive', fields='files(id)', pageSize=1).execute()
    root_files = results.get('files', [])
    if not root_files:
        return []
    root_id = root_files[0]['id']

    # Find all Week_* subfolders
    query = (
        f"'{root_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    folder_results = service.files().list(
        q=query, spaces='drive', fields='files(id, name)', pageSize=100
    ).execute()

    old_files = []
    for folder in folder_results.get('files', []):
        file_query = (
            f"'{folder['id']}' in parents "
            f"and trashed = false "
            f"and modifiedTime < '{cutoff}'"
        )
        file_results = service.files().list(
            q=file_query, spaces='drive',
            fields='files(id, name, size, modifiedTime)',
            pageSize=100
        ).execute()
        for f in file_results.get('files', []):
            size_bytes = int(f.get('size', 0))
            old_files.append({
                'id': f['id'],
                'name': f['name'],
                'folder': folder['name'],
                'size_mb': round(size_bytes / (1024 * 1024), 1),
                'modified_date': f.get('modifiedTime', '')[:10]
            })

    old_files.sort(key=lambda x: x.get('modified_date', ''))
    return old_files


def delete_files(file_ids: List[str]) -> Dict[str, Any]:
    """Delete files from Google Drive by their IDs."""
    service = get_drive_service()
    deleted = 0
    errors = 0
    details = []

    for fid in file_ids:
        try:
            service.files().delete(fileId=fid).execute()
            deleted += 1
        except HttpError as e:
            errors += 1
            details.append(f"Failed to delete {fid}: {e}")

    return {'deleted': deleted, 'errors': errors, 'details': details}
