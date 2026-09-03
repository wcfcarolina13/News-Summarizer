import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import mcp_config  # noqa: E402


def test_server_command_dev_mode(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    cmd = mcp_config.server_command()
    assert cmd[0] == sys.executable and cmd[1].endswith("mcp_server.py") and os.path.isabs(cmd[1])


def test_server_command_frozen(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/Applications/Daily Audio Briefing.app/Contents/MacOS/dab-mcp")
    assert mcp_config.server_command() == ["/Applications/Daily Audio Briefing.app/Contents/MacOS/dab-mcp"]


def test_snippet_shape():
    s = mcp_config.snippet(["/usr/bin/python3", "/x/mcp_server.py"])
    assert s == {"mcpServers": {"daily-audio-briefing": {"command": "/usr/bin/python3", "args": ["/x/mcp_server.py"]}}}


def test_install_merges_without_clobbering(tmp_path):
    code = tmp_path / ".claude.json"
    desk = tmp_path / "claude_desktop_config.json"
    code.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}, "theme": "dark"}))
    paths = {"claude_code": str(code), "claude_desktop": str(desk)}
    written = mcp_config.install(["/p", "/s.py"], paths=paths)
    assert set(written) == {str(code), str(desk)}
    c = json.loads(code.read_text())
    assert c["theme"] == "dark" and c["mcpServers"]["other"] == {"command": "x"}
    assert c["mcpServers"]["daily-audio-briefing"] == {"command": "/p", "args": ["/s.py"]}
    assert (tmp_path / ".claude.json.bak").exists()
    d = json.loads(desk.read_text())  # created from scratch
    assert d["mcpServers"]["daily-audio-briefing"]["command"] == "/p"


def test_uninstall_removes_only_our_key(tmp_path):
    code = tmp_path / ".claude.json"
    code.write_text(json.dumps({"mcpServers": {"other": {"command": "x"}, "daily-audio-briefing": {"command": "y"}}}))
    paths = {"claude_code": str(code), "claude_desktop": str(tmp_path / "missing.json")}
    written = mcp_config.uninstall(paths=paths)
    assert written == [str(code)]
    assert json.loads(code.read_text())["mcpServers"] == {"other": {"command": "x"}}


def test_config_paths_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    p = mcp_config.config_paths()
    assert p["claude_code"].endswith(".claude.json")
    assert p["claude_desktop"].endswith("Library/Application Support/Claude/claude_desktop_config.json")


def test_install_malformed_config_raises_and_leaves_file(tmp_path):
    code = tmp_path / ".claude.json"
    code.write_text("{not json")
    paths = {"claude_code": str(code), "claude_desktop": str(tmp_path / "claude_desktop_config.json")}
    try:
        mcp_config.install(["/p", "/s.py"], paths=paths)
        assert False, "expected ConfigError"
    except mcp_config.ConfigError:
        pass
    assert code.read_text() == "{not json"
    assert not (tmp_path / ".claude.json.bak").exists()


def test_uninstall_malformed_config_raises_and_leaves_file(tmp_path):
    code = tmp_path / ".claude.json"
    code.write_text("{not json")
    paths = {"claude_code": str(code), "claude_desktop": str(tmp_path / "missing.json")}
    try:
        mcp_config.uninstall(paths=paths)
        assert False, "expected ConfigError"
    except mcp_config.ConfigError:
        pass
    assert code.read_text() == "{not json"
    assert not (tmp_path / ".claude.json.bak").exists()
