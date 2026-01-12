"""
Transcription Service Module

Provides transcription capabilities through multiple backends:
1. Local faster-whisper (if installed on system)
2. Cloud API (future - for monetized/hosted version)

This module includes scaffolding for future licensing and API management.
"""

import os
import sys
import subprocess
import tempfile
import json
from typing import Optional, Tuple, Dict, Any
from enum import Enum


class TranscriptionBackend(Enum):
    """Available transcription backends."""
    NONE = "none"
    LOCAL_WHISPER = "local_whisper"      # System-installed faster-whisper
    CLOUD_API = "cloud_api"              # Future: hosted transcription API


class LicenseStatus(Enum):
    """License status for cloud features."""
    NO_LICENSE = "no_license"
    TRIAL = "trial"
    ACTIVE = "active"
    EXPIRED = "expired"
    RATE_LIMITED = "rate_limited"


# ============================================================================
# FUTURE LICENSING SCAFFOLDING
# ============================================================================

class LicenseManager:
    """
    Manages user licenses for cloud/premium features.

    Future implementation will:
    - Validate license keys against a server
    - Track usage quotas
    - Handle rate limiting
    - Manage subscription status
    """

    LICENSE_SERVER_URL = "https://api.yourdomain.com/v1/license"  # TODO: Set your API endpoint

    def __init__(self):
        self._license_key: Optional[str] = None
        self._license_status = LicenseStatus.NO_LICENSE
        self._usage_quota: int = 0
        self._usage_remaining: int = 0
        self._cache_file = self._get_cache_path()
        self._load_cached_license()

    def _get_cache_path(self) -> str:
        """Get path for cached license info."""
        if sys.platform == 'darwin':
            cache_dir = os.path.expanduser("~/Library/Application Support/DailyAudioBriefing")
        elif sys.platform == 'win32':
            cache_dir = os.path.join(os.environ.get('APPDATA', ''), 'DailyAudioBriefing')
        else:
            cache_dir = os.path.expanduser("~/.config/daily_audio_briefing")

        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, "license.json")

    def _load_cached_license(self):
        """Load cached license from disk."""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    data = json.load(f)
                    self._license_key = data.get('license_key')
                    # Don't trust cached status - will revalidate on check
        except Exception:
            pass

    def _save_cached_license(self):
        """Save license info to disk."""
        try:
            with open(self._cache_file, 'w') as f:
                json.dump({
                    'license_key': self._license_key,
                }, f)
        except Exception:
            pass

    def set_license_key(self, key: str) -> bool:
        """
        Set and validate a license key.

        Future implementation will validate against server.
        """
        self._license_key = key
        self._save_cached_license()
        return self.validate_license()

    def validate_license(self) -> bool:
        """
        Validate the current license key.

        TODO: Implement server-side validation:
        - POST to LICENSE_SERVER_URL with license key
        - Check response for status, quota, expiry
        - Handle rate limiting headers
        """
        if not self._license_key:
            self._license_status = LicenseStatus.NO_LICENSE
            return False

        # PLACEHOLDER: Always return no_license until server is implemented
        # In production, this would call the license server
        self._license_status = LicenseStatus.NO_LICENSE
        return False

    def get_status(self) -> LicenseStatus:
        """Get current license status."""
        return self._license_status

    def get_usage_info(self) -> Dict[str, Any]:
        """Get usage quota information."""
        return {
            'status': self._license_status.value,
            'quota': self._usage_quota,
            'remaining': self._usage_remaining,
            'license_key': self._license_key[:8] + '...' if self._license_key else None
        }

    def can_use_cloud_transcription(self) -> bool:
        """Check if user can use cloud transcription."""
        return self._license_status in [LicenseStatus.TRIAL, LicenseStatus.ACTIVE]

    def record_usage(self, seconds_transcribed: float) -> bool:
        """
        Record usage of cloud transcription.

        TODO: Implement server-side usage tracking:
        - POST usage to server
        - Update remaining quota
        - Handle quota exceeded
        """
        if not self.can_use_cloud_transcription():
            return False

        # PLACEHOLDER: Just decrement local counter
        self._usage_remaining = max(0, self._usage_remaining - int(seconds_transcribed))
        return self._usage_remaining > 0


# Global license manager instance
_license_manager: Optional[LicenseManager] = None

def get_license_manager() -> LicenseManager:
    """Get the global license manager instance."""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager


# ============================================================================
# LOCAL TRANSCRIPTION DETECTION
# ============================================================================

def _find_system_python() -> Optional[str]:
    """Find the system Python executable."""
    # Common Python paths
    python_paths = [
        '/usr/bin/python3',
        '/usr/local/bin/python3',
        '/opt/homebrew/bin/python3',  # Apple Silicon Homebrew
        'python3',  # Rely on PATH
        'python',
    ]

    for python_path in python_paths:
        try:
            result = subprocess.run(
                [python_path, '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return python_path
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            continue

    return None


def check_system_whisper() -> Tuple[bool, Optional[str]]:
    """
    Check if faster-whisper is installed in system Python.

    Returns:
        Tuple of (is_available, python_path)
    """
    # If running from source (not frozen), check directly
    if not getattr(sys, 'frozen', False):
        try:
            import faster_whisper
            return True, sys.executable
        except ImportError:
            pass

    # For frozen apps, check system Python
    python_path = _find_system_python()
    if not python_path:
        return False, None

    try:
        result = subprocess.run(
            [python_path, '-c', 'import faster_whisper; print("OK")'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and 'OK' in result.stdout:
            return True, python_path
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    return False, None


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


# ============================================================================
# TRANSCRIPTION SERVICE
# ============================================================================

class TranscriptionService:
    """
    Unified transcription service that handles multiple backends.
    """

    def __init__(self):
        self._backend = TranscriptionBackend.NONE
        self._system_python: Optional[str] = None
        self._detect_backend()

    def _detect_backend(self):
        """Detect available transcription backend."""
        # Check for local faster-whisper first (free)
        has_whisper, python_path = check_system_whisper()
        if has_whisper and check_ffmpeg():
            self._backend = TranscriptionBackend.LOCAL_WHISPER
            self._system_python = python_path
            return

        # Check for cloud API access
        license_mgr = get_license_manager()
        if license_mgr.can_use_cloud_transcription():
            self._backend = TranscriptionBackend.CLOUD_API
            return

        self._backend = TranscriptionBackend.NONE

    def get_backend(self) -> TranscriptionBackend:
        """Get the current transcription backend."""
        return self._backend

    def is_available(self) -> bool:
        """Check if any transcription backend is available."""
        return self._backend != TranscriptionBackend.NONE

    def get_status_message(self) -> Tuple[str, str]:
        """
        Get a status message for the GUI.

        Returns:
            Tuple of (message, color) where color is 'green', 'orange', or 'red'
        """
        if self._backend == TranscriptionBackend.LOCAL_WHISPER:
            return "✓ Transcription ready (local)", "green"
        elif self._backend == TranscriptionBackend.CLOUD_API:
            return "✓ Transcription ready (cloud)", "green"
        else:
            # Check what's missing
            has_ffmpeg = check_ffmpeg()
            has_whisper, _ = check_system_whisper()

            if not has_ffmpeg and not has_whisper:
                return "⚠ Transcription disabled - Install ffmpeg & faster-whisper", "orange"
            elif not has_ffmpeg:
                return "⚠ Transcription disabled - Install ffmpeg", "orange"
            elif not has_whisper:
                return "⚠ Transcription disabled - Install faster-whisper", "orange"
            else:
                return "⚠ Transcription unavailable", "orange"

    def transcribe(self, audio_path: str, model_size: str = "base") -> Optional[str]:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to audio file
            model_size: Whisper model size (tiny, base, small, medium, large)

        Returns:
            Transcribed text or None if failed
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if self._backend == TranscriptionBackend.LOCAL_WHISPER:
            return self._transcribe_local(audio_path, model_size)
        elif self._backend == TranscriptionBackend.CLOUD_API:
            return self._transcribe_cloud(audio_path)
        else:
            raise RuntimeError("No transcription backend available")

    def _transcribe_local(self, audio_path: str, model_size: str) -> Optional[str]:
        """Transcribe using local faster-whisper."""
        # If running from source, use direct import
        if not getattr(sys, 'frozen', False):
            try:
                from faster_whisper import WhisperModel
                model = WhisperModel(model_size, device="auto")
                segments, info = model.transcribe(audio_path, vad_filter=True)
                return "\n".join(seg.text.strip() for seg in segments).strip()
            except Exception as e:
                raise RuntimeError(f"Local transcription failed: {e}")

        # For frozen apps, call system Python
        if not self._system_python:
            raise RuntimeError("System Python not found")

        # Create a temporary script to run transcription
        script = f'''
import sys
try:
    from faster_whisper import WhisperModel
    model = WhisperModel("{model_size}", device="auto")
    segments, info = model.transcribe("{audio_path}", vad_filter=True)
    for seg in segments:
        print(seg.text.strip())
except Exception as e:
    print(f"ERROR: {{e}}", file=sys.stderr)
    sys.exit(1)
'''

        try:
            result = subprocess.run(
                [self._system_python, '-c', script],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for long files
            )

            if result.returncode != 0:
                raise RuntimeError(f"Transcription failed: {result.stderr}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise RuntimeError("Transcription timed out")
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}")

    def _transcribe_cloud(self, audio_path: str) -> Optional[str]:
        """
        Transcribe using cloud API.

        TODO: Implement cloud transcription:
        - Upload audio to your API endpoint
        - Wait for transcription result
        - Handle errors and rate limiting
        - Record usage with LicenseManager
        """
        license_mgr = get_license_manager()
        if not license_mgr.can_use_cloud_transcription():
            raise RuntimeError("Cloud transcription not available - check license")

        # PLACEHOLDER: Cloud transcription not yet implemented
        raise NotImplementedError(
            "Cloud transcription coming soon. "
            "For now, install faster-whisper locally: pip install faster-whisper"
        )


# Global service instance
_transcription_service: Optional[TranscriptionService] = None

def get_transcription_service() -> TranscriptionService:
    """Get the global transcription service instance."""
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def is_transcription_available() -> bool:
    """Check if transcription is available."""
    return get_transcription_service().is_available()

def get_transcription_status() -> Tuple[str, str]:
    """Get transcription status message and color."""
    return get_transcription_service().get_status_message()

def transcribe_audio(audio_path: str, model_size: str = "base") -> Optional[str]:
    """Transcribe an audio file using the best available backend."""
    return get_transcription_service().transcribe(audio_path, model_size)
