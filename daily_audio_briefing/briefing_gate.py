"""Readiness gate for the GPU-heavy audio-render step of the briefing pipeline.

The daily briefing's fetch + summarize steps run on the cloud free-chain (Groq /
Cerebras) and use no local GPU. Only the Kokoro TTS render uses the Metal GPU.
This module decides whether the machine is free enough to run that render *now*,
so a scheduled briefing doesn't contend with OpenMW / Dreamsleeve, games, or any
other GPU-heavy foreground app.

Detection (all no-sudo, macOS):
  - Named processes: ``pgrep -il <name>`` against a configurable blocklist.
  - GPU utilization: ``Device Utilization %`` from ``ioreg -c IOAccelerator``.

Config is OPTIONAL. The built-in defaults below always apply; a ``briefing_gate.json``
next to this module or in the data dir *overrides* them. The gate NEVER depends on a
gitignored file existing — a missing/broken config means "use defaults", not
"disabled" (cf. the local_sources.json silent-no-op footgun).

Only the ``quality`` (Kokoro) audio path is gated; the ``fast`` gTTS path is
CPU/network and is never blocked by this module.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Callable, List, Optional, Tuple

# --- Built-in defaults (used when no config file is present) ------------------
DEFAULT_ENABLED = True
# `openmw` covers Dreamsleeve too (Dreamsleeve content runs through the OpenMW
# engine, so the process name is still `openmw`). Add game / launcher process
# names via briefing_gate.json without touching code. Substring, case-insensitive.
DEFAULT_BLOCKING_PROCESSES: List[str] = ["openmw"]
DEFAULT_GPU_BUSY_THRESHOLD_PCT = 40
DEFAULT_RETRY_INTERVAL_MIN = 15
DEFAULT_GIVEUP_HOUR = 22  # after this local hour, stop retrying and skip to tomorrow

_CONFIG_FILENAME = "briefing_gate.json"


def default_config() -> dict:
    return {
        "enabled": DEFAULT_ENABLED,
        "blocking_processes": list(DEFAULT_BLOCKING_PROCESSES),
        "gpu_busy_threshold_pct": DEFAULT_GPU_BUSY_THRESHOLD_PCT,
        "retry_interval_min": DEFAULT_RETRY_INTERVAL_MIN,
        "giveup_hour": DEFAULT_GIVEUP_HOUR,
    }


def load_gate_config(data_dir: Optional[str] = None) -> dict:
    """Return the gate config: built-in defaults overlaid with an optional JSON file.

    Search order (first hit wins): ``<data_dir>/briefing_gate.json`` then
    ``<module_dir>/briefing_gate.json``. A missing or malformed file falls back to
    defaults — the gate is never silently disabled by an absent config.
    """
    cfg = default_config()
    candidates = []
    if data_dir:
        candidates.append(os.path.join(data_dir, _CONFIG_FILENAME))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), _CONFIG_FILENAME))

    for path in candidates:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    # Only override known keys; ignore unknown ones.
                    for k in cfg:
                        if k in loaded and loaded[k] is not None:
                            cfg[k] = loaded[k]
                break
        except Exception as e:  # malformed JSON, perms, etc. -> keep defaults
            print(f"[BriefingGate] Could not read {path} ({e}); using defaults")
            break
    return cfg


# --- Process detection --------------------------------------------------------
def _pgrep(name: str) -> bool:
    """True if a process whose name matches ``name`` (substring, case-insensitive)
    is running. Uses pgrep; returns False on any error or no-match."""
    try:
        # -i case-insensitive, -l lists (not needed for bool but harmless). pgrep
        # exits 0 on match, 1 on no match, >1 on error.
        res = subprocess.run(
            ["pgrep", "-i", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return res.returncode == 0
    except Exception:
        return False


def find_blocking_processes(
    names: List[str],
    process_checker: Optional[Callable[[str], bool]] = None,
) -> List[str]:
    """Return the subset of ``names`` that currently have a running process."""
    check = process_checker or _pgrep
    hits = []
    for n in names:
        n = (n or "").strip()
        if n and check(n):
            hits.append(n)
    return hits


# --- GPU utilization ----------------------------------------------------------
def parse_gpu_utilization(ioreg_output: str) -> Optional[int]:
    """Extract the max ``Device Utilization %`` from ioreg output.

    Multiple accelerator nodes can each report a value; the max is the most
    conservative choice (most likely to detect a busy GPU). Returns None if no
    value is present.
    """
    import re

    vals = [int(m) for m in re.findall(r'"Device Utilization %"=(\d+)', ioreg_output or "")]
    if not vals:
        return None
    return max(vals)


def _read_ioreg() -> str:
    try:
        res = subprocess.run(
            ["ioreg", "-r", "-d", "1", "-w", "0", "-c", "IOAccelerator"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return res.stdout or ""
    except Exception:
        return ""


def gpu_utilization_pct(reader: Optional[Callable[[], str]] = None) -> Optional[int]:
    """Current GPU ``Device Utilization %`` (max across nodes), or None if unreadable."""
    read = reader or _read_ioreg
    return parse_gpu_utilization(read())


# --- Top-level gate -----------------------------------------------------------
def render_blocked(
    config: Optional[dict] = None,
    data_dir: Optional[str] = None,
    *,
    process_checker: Optional[Callable[[str], bool]] = None,
    gpu_reader: Optional[Callable[[], str]] = None,
) -> Tuple[bool, str]:
    """Decide whether the GPU-heavy audio render should be held back right now.

    Returns ``(blocked, reason)``. ``blocked`` is False when the gate is disabled,
    when nothing is contending, or when signals are unreadable (fail-open: a broken
    detector must never permanently block the briefing).

    GPU is sampled twice ~1s apart and the *minimum* is used, so a single transient
    spike won't defer the render — only sustained load does.
    """
    cfg = config or load_gate_config(data_dir)
    if not cfg.get("enabled", True):
        return (False, "")

    # 1) Named processes (cheap, deterministic).
    procs = find_blocking_processes(
        cfg.get("blocking_processes") or [], process_checker=process_checker
    )
    if procs:
        return (True, f"app running: {', '.join(procs)}")

    # 2) GPU utilization (sustained-load check via two samples).
    threshold = cfg.get("gpu_busy_threshold_pct", DEFAULT_GPU_BUSY_THRESHOLD_PCT)
    try:
        threshold = int(threshold)
    except (TypeError, ValueError):
        threshold = DEFAULT_GPU_BUSY_THRESHOLD_PCT

    s1 = gpu_utilization_pct(reader=gpu_reader)
    if s1 is not None and s1 > threshold:
        # Confirm with a second sample so we don't defer on a one-off spike. Skip
        # the sleep when a reader is injected (tests) — same reader, same value.
        if gpu_reader is None:
            import time

            time.sleep(1)
        s2 = gpu_utilization_pct(reader=gpu_reader)
        sustained = min(s1, s2) if s2 is not None else s1
        if sustained > threshold:
            return (True, f"GPU busy: {sustained}% > {threshold}%")

    return (False, "")
