"""Tests for the briefing readiness gate (briefing_gate.py).

The gate holds back the GPU-heavy Kokoro TTS render when OpenMW/Dreamsleeve, a
game, or another GPU hog is running, so the scheduled briefing doesn't contend.
Detection is via pgrep (named apps) + ioreg (GPU %). These tests inject fake
process/GPU readers so they're deterministic and don't touch the real machine.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import briefing_gate as gate


# --- ioreg parsing ------------------------------------------------------------
def test_parse_gpu_utilization_single():
    assert gate.parse_gpu_utilization('"Device Utilization %"=57') == 57


def test_parse_gpu_utilization_takes_max_across_nodes():
    text = '"Device Utilization %"=12\nfoo\n"Device Utilization %"=88\n"Device Utilization %"=30'
    assert gate.parse_gpu_utilization(text) == 88


def test_parse_gpu_utilization_absent_returns_none():
    assert gate.parse_gpu_utilization("no gpu stats here") is None
    assert gate.parse_gpu_utilization("") is None


# --- process detection --------------------------------------------------------
def test_find_blocking_processes_matches():
    running = {"openmw"}
    hits = gate.find_blocking_processes(
        ["openmw", "Steam", "elden"], process_checker=lambda n: n in running
    )
    assert hits == ["openmw"]


def test_find_blocking_processes_ignores_blank_names():
    hits = gate.find_blocking_processes(
        ["", "  ", "openmw"], process_checker=lambda n: True
    )
    assert hits == ["openmw"]


# --- top-level gate -----------------------------------------------------------
def _cfg(**over):
    c = gate.default_config()
    c.update(over)
    return c


def test_disabled_never_blocks():
    blocked, reason = gate.render_blocked(
        config=_cfg(enabled=False, blocking_processes=["openmw"]),
        process_checker=lambda n: True,
        gpu_reader=lambda: '"Device Utilization %"=99',
    )
    assert blocked is False


def test_blocks_on_named_process():
    blocked, reason = gate.render_blocked(
        config=_cfg(blocking_processes=["openmw"]),
        process_checker=lambda n: n == "openmw",
        gpu_reader=lambda: '"Device Utilization %"=0',
    )
    assert blocked is True
    assert "openmw" in reason


def test_blocks_on_sustained_gpu():
    blocked, reason = gate.render_blocked(
        config=_cfg(blocking_processes=[], gpu_busy_threshold_pct=40),
        process_checker=lambda n: False,
        gpu_reader=lambda: '"Device Utilization %"=85',
    )
    assert blocked is True
    assert "GPU busy" in reason


def test_allows_when_gpu_below_threshold():
    blocked, reason = gate.render_blocked(
        config=_cfg(blocking_processes=[], gpu_busy_threshold_pct=40),
        process_checker=lambda n: False,
        gpu_reader=lambda: '"Device Utilization %"=12',
    )
    assert blocked is False
    assert reason == ""


def test_fail_open_when_signals_unreadable():
    """A broken detector must never permanently block the briefing."""
    blocked, reason = gate.render_blocked(
        config=_cfg(blocking_processes=["openmw"]),
        process_checker=lambda n: False,
        gpu_reader=lambda: "",  # ioreg returned nothing
    )
    assert blocked is False


# --- config loading -----------------------------------------------------------
def test_missing_config_uses_defaults(tmp_path):
    cfg = gate.load_gate_config(data_dir=str(tmp_path))
    assert cfg["enabled"] is True
    assert cfg["blocking_processes"] == gate.DEFAULT_BLOCKING_PROCESSES
    assert cfg["giveup_hour"] == gate.DEFAULT_GIVEUP_HOUR


def test_config_file_overrides_defaults(tmp_path):
    import json
    p = tmp_path / "briefing_gate.json"
    p.write_text(json.dumps({"gpu_busy_threshold_pct": 70, "blocking_processes": ["openmw", "csgo"]}))
    cfg = gate.load_gate_config(data_dir=str(tmp_path))
    assert cfg["gpu_busy_threshold_pct"] == 70
    assert cfg["blocking_processes"] == ["openmw", "csgo"]
    # Unspecified keys keep defaults.
    assert cfg["retry_interval_min"] == gate.DEFAULT_RETRY_INTERVAL_MIN


def test_malformed_config_falls_back_to_defaults(tmp_path):
    p = tmp_path / "briefing_gate.json"
    p.write_text("{ this is not valid json ")
    cfg = gate.load_gate_config(data_dir=str(tmp_path))
    assert cfg == gate.default_config()
