# Source Generated with Decompyle++
# File: drive_manager.pyc (Python 3.12)

__doc__ = '\nGoogle Drive Manager - Handles uploading audio files to Google Drive via OAuth2.\n\nSetup:\n1. Enable the Google Drive API in Google Cloud Console\n2. Create an OAuth 2.0 Client ID (Desktop app type)\n3. Download the client secret JSON and save as \'drive_client_secret.json\'\n   next to this file (or in the app data directory for frozen builds).\n4. User signs in via "Sign in with Google" button in Settings.\n\nAuth flow:\n- First time: opens browser for Google consent → stores refresh token locally\n- Subsequent: uses stored refresh token (no browser needed)\n- Token file: \'drive_token.json\' in the app data directory\n'
import os
import sys
import json
import glob
import time
import mimetypes
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials as OAuthCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
DRIVE_AVAILABLE = True
SCOPES = [
    'https://www.googleapis.com/auth/drive.file']
_cached_service = None
_reauth_needed = False

def _get_data_directory():
    """Get the app's data directory for storing tokens."""
    if getattr(sys, 'frozen', False):
        if sys.platform == 'darwin':
            return os.path.expanduser('~/Library/Application Support/Daily Audio Briefing')
        if None.platform == 'win32':
            return os.path.join(os.environ.get('APPDATA', ''), 'Daily Audio Briefing')
        return None.path.expanduser('~/.daily-audio-briefing')
    return None.path.dirname(os.path.abspath(__file__))


def _find_client_secret_file():
    '''Find drive_client_secret.json, checking multiple locations.'''
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'drive_client_secret.json'),
        os.path.join(_get_data_directory(), 'drive_client_secret.json')]
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        candidates.insert(0, os.path.join(sys._MEIPASS, 'drive_client_secret.json'))
    for path in candidates:
        if not os.path.exists(path):
            continue
        
        return candidates, path
    return candidates[0]


def _get_token_path():
    '''Path to the stored OAuth token file.'''
    return os.path.join(_get_data_directory(), 'drive_token.json')

CLIENT_SECRET_FILE = _find_client_secret_file()

def is_drive_available():
    '''Check if Google Drive integration is possible (libs + client secret present).'''
    if not DRIVE_AVAILABLE:
        return False
    return os.path.exists(CLIENT_SECRET_FILE)


def is_signed_in():
    '''Check if the user has a valid (possibly expired but refreshable) token.'''
    token_path = _get_token_path()
    if not os.path.exists(token_path):
        return False
    creds = OAuthCredentials.from_authorized_user_file(token_path)
    return creds.refresh_token is not None
# WARNING: Decompyle incomplete


def get_user_email():
    """Get the signed-in user's email from the stored token."""
    token_path = _get_token_path()
    if not os.path.exists(token_path):
        return None
# WARNING: Decompyle incomplete


def sign_in():
    '''Run the OAuth2 sign-in flow (opens browser).

    Returns:
        Dict with: success (bool), email (str or None), error (str or None).
    '''
    if not DRIVE_AVAILABLE:
        return {
            'success': False,
            'email': None,
            'error': 'Google API packages not installed' }
    if not None.path.exists(CLIENT_SECRET_FILE):
        return {
            'success': False,
            'email': None,
            'error': f'''Client secret not found: {CLIENT_SECRET_FILE}''' }
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port = 0, open_browser = True)
    email = None
    service = build('oauth2', 'v2', credentials = creds)
    user_info = service.userinfo().get().execute()
    email = user_info.get('email')
    token_data = json.loads(creds.to_json())
    if email:
        token_data['_user_email'] = email
    token_path = _get_token_path()
    os.makedirs(os.path.dirname(token_path), exist_ok = True)
# WARNING: Decompyle incomplete


def sign_out():
    '''Revoke OAuth token with Google, then remove stored token file.'''
    global _cached_service
    _cached_service = None
    token_path = _get_token_path()
# WARNING: Decompyle incomplete


def flag_reauth_needed():
    '''Mark Drive as needing re-authentication (expired/revoked refresh token).'''
    global _reauth_needed, _cached_service
    _reauth_needed = True
    _cached_service = None


def is_reauth_needed():
    '''Check if Drive needs re-authentication.'''
    return _reauth_needed


def clear_reauth_flag():
    '''Clear the re-auth flag (called after successful sign-in).'''
    global _reauth_needed
    _reauth_needed = False


def get_drive_service():
    '''Create and return a cached Google Drive service using OAuth2 user credentials.

    Automatically refreshes expired tokens using the stored refresh token.
    Raises RuntimeError if not signed in.
    '''
    if not DRIVE_AVAILABLE:
        raise RuntimeError('Google API packages not installed')
# WARNING: Decompyle incomplete


def get_or_create_folder(folder_name = None, parent_id = None):
    """Find an existing folder by name under parent, or create it.

    Args:
        folder_name: Name of the folder to find/create.
        parent_id: Drive ID of the parent folder ('root' for top-level).

    Returns:
        The Drive folder ID.
    """
    service = get_drive_service()
    query = f'''name = \'{folder_name}\' and \'{parent_id}\' in parents and mimeType = \'application/vnd.google-apps.folder\' and trashed = false'''
    results = service.files().list(q = query, spaces = 'drive', fields = 'files(id, name)', pageSize = 1).execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    metadata = {
        'name': None,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [
            parent_id] }
    folder = service.files().create(body = metadata, fields = 'id').execute()
    return folder['id']


def file_exists_in_folder(filename = None, folder_id = None):
    """Check if a file with the given name exists in a folder.

    Returns the file's Drive ID if found, None otherwise.
    Retries on transient SSL/connection errors (stale connections in long-running daemon).
    """
    global _cached_service
    _cached_service = None
    query = f'''name = \'{filename}\' and \'{folder_id}\' in parents and trashed = false'''
    for attempt in range(3):
        service = get_drive_service()
        results = service.files().list(q = query, spaces = 'drive', fields = 'files(id)', pageSize = 1).execute()
        files = results.get('files', [])
        if files:
            
            return range(3), files[0]['id']
        
        return None, range(3)
    return None
# WARNING: Decompyle incomplete


def upload_file(local_path = None, folder_id = None, skip_existing = None):
    """Upload a local file to a Drive folder.

    Returns:
        Dict with keys: id, name, size_bytes, status ('uploaded'|'skipped'|'error').
    """
    global _cached_service
    filename = os.path.basename(local_path)
    if skip_existing:
        existing_id = file_exists_in_folder(filename, folder_id)
        if existing_id:
            return {
                'id': existing_id,
                'name': filename,
                'status': 'skipped',
                'reason': 'already exists' }
        _cached_service = None
        if not mimetypes.guess_type(local_path)[0]:
            mimetypes.guess_type(local_path)[0]
    mime_type = 'application/octet-stream'
    media = MediaFileUpload(local_path, mimetype = mime_type, resumable = True)
    metadata = {
        'name': filename,
        'parents': [
            folder_id] }
    last_err = None
    for attempt in range(3):
        service = get_drive_service()
        uploaded = service.files().create(body = metadata, media_body = media, fields = 'id, name, size').execute()
        
        return range(3), {
            'id': uploaded['id'],
            'name': uploaded['name'],
            'size_bytes': int(uploaded.get('size', 0)),
            'status': 'uploaded' }
    return {
        'name': filename,
        'status': 'error',
        'reason': f'''Failed after 3 attempts: {last_err}''' }
# WARNING: Decompyle incomplete


def extract_folder_id_from_url(url_or_id = None):
    '''Extract a Google Drive folder ID from a URL or return the ID as-is.

    Accepts:
        - Full URL: https://drive.google.com/drive/folders/ABC123?usp=sharing
        - Just the ID: ABC123
    '''
    if not url_or_id:
        return ''
    url_or_id = url_or_id.strip()
    if '/folders/' in url_or_id:
        part = url_or_id.split('/folders/')[-1]
        return part.split('?')[0].split('#')[0].strip('/')


def verify_folder_access(folder_id = None):
    '''Verify the signed-in user can access a folder.

    Returns:
        Dict with: accessible (bool), name (str or None), error (str or None).
    '''
    if not folder_id:
        return {
            'accessible': False,
            'name': None,
            'error': 'No folder ID provided' }
    service = None()
    info = service.files().get(fileId = folder_id, fields = 'id, name, mimeType').execute()
    if info.get('mimeType') != 'application/vnd.google-apps.folder':
        return {
            'accessible': False,
            'name': info.get('name'),
            'error': 'Not a folder' }
    return {
        'accessible': None,
        'name': info.get('name'),
        'error': None }
# WARNING: Decompyle incomplete


def sync_week_folders(local_base_path = None, root_folder_name = None, shared_folder_id = None, status_callback = ('Daily Audio Briefing', '', None)):
    '''Sync all Week_* folders and their audio files to Google Drive.

    If shared_folder_id is provided, creates structure inside that folder:
        <shared_folder> / <root_folder_name> / Week_N_YYYY / audio_files
    Otherwise creates at Drive root:
        <root_folder_name> / Week_N_YYYY / audio_files
    '''
    pass
# WARNING: Decompyle incomplete


def get_storage_quota():
    '''Return Google Drive storage quota information.'''
    service = get_drive_service()
    about = service.about().get(fields = 'storageQuota').execute()
    quota = about.get('storageQuota', { })
    used = int(quota.get('usage', 0))
    total = int(quota.get('limit', 0))
    used_gb = used / 1073741824
    total_gb = total / 1073741824 if total else 0
    percent = (used / total) * 100 if total else 0
    return {
        'used_bytes': used,
        'total_bytes': total,
        'used_gb': used_gb,
        'total_gb': total_gb,
        'percent_used': percent }


def list_old_audio_files(root_folder_name = None, before_days = None, shared_folder_id = None):
    '''List audio files older than N days in the Drive folder structure.'''
    service = get_drive_service()
    cutoff = (datetime.utcnow() - timedelta(days = before_days)).isoformat() + 'Z'
    if shared_folder_id:
        query = f'''name = \'{root_folder_name}\' and \'{shared_folder_id}\' in parents and mimeType = \'application/vnd.google-apps.folder\' and trashed = false'''
    else:
        query = f'''name = \'{root_folder_name}\' and mimeType = \'application/vnd.google-apps.folder\' and trashed = false'''
    results = service.files().list(q = query, spaces = 'drive', fields = 'files(id)', pageSize = 1).execute()
    root_files = results.get('files', [])
    if not root_files:
        return []
    root_id = None[0]['id']
    query = f'''\'{root_id}\' in parents and mimeType = \'application/vnd.google-apps.folder\' and trashed = false'''
    folder_results = service.files().list(q = query, spaces = 'drive', fields = 'files(id, name)', pageSize = 100).execute()
    old_files = []
    for folder in folder_results.get('files', []):
        file_query = f'''\'{folder['id']}\' in parents and trashed = false and modifiedTime < \'{cutoff}\''''
        file_results = service.files().list(q = file_query, spaces = 'drive', fields = 'files(id, name, size, modifiedTime)', pageSize = 100).execute()
        for f in file_results.get('files', []):
            size_bytes = int(f.get('size', 0))
            old_files.append({
                'id': f['id'],
                'name': f['name'],
                'folder': folder['name'],
                'size_mb': round(size_bytes / 1048576, 1),
                'modified_date': f.get('modifiedTime', '')[:10] })
    old_files.sort(key = (lambda x: x.get('modified_date', '')))
    return old_files


def delete_files(file_ids = None):
    '''Delete files from Google Drive by their IDs.'''
    service = get_drive_service()
    deleted = 0
    errors = 0
    details = []
    for fid in file_ids:
        service.files().delete(fileId = fid).execute()
        deleted += 1
    return {
        'deleted': deleted,
        'errors': errors,
        'details': details }
# WARNING: Decompyle incomplete

return None
# WARNING: Decompyle incomplete
