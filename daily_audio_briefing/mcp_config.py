"""
mcp_config — build and install the MCP client config for this server.

Writes the one "daily-audio-briefing" key into Claude Code's ~/.claude.json and
Claude Desktop's claude_desktop_config.json, leaving every other key alone.
"""
import json
import os
import shutil
import sys

SERVER_KEY = "daily-audio-briefing"


def server_command():
    if getattr(sys, "frozen", False):
        return [sys.executable]
    here = os.path.dirname(os.path.abspath(__file__))
    return [sys.executable, os.path.join(here, "mcp_server.py")]


def snippet(command):
    return {"mcpServers": {SERVER_KEY: {"command": command[0], "args": list(command[1:])}}}


def config_paths():
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        desktop = os.path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json")
    elif sys.platform == "win32":
        desktop = os.path.join(os.environ.get("APPDATA", home), "Claude", "claude_desktop_config.json")
    else:
        desktop = os.path.join(home, ".config", "Claude", "claude_desktop_config.json")
    return {"claude_code": os.path.join(home, ".claude.json"), "claude_desktop": desktop}


def _load(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(path, data):
    if os.path.exists(path):
        shutil.copyfile(path, path + ".bak")
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def install(command, paths=None):
    paths = paths or config_paths()
    entry = snippet(command)["mcpServers"][SERVER_KEY]
    written = []
    for path in paths.values():
        data = _load(path)
        data.setdefault("mcpServers", {})[SERVER_KEY] = entry
        _save(path, data)
        written.append(path)
    return written


def uninstall(paths=None):
    paths = paths or config_paths()
    written = []
    for path in paths.values():
        if not os.path.exists(path):
            continue
        data = _load(path)
        if SERVER_KEY in data.get("mcpServers", {}):
            del data["mcpServers"][SERVER_KEY]
            _save(path, data)
            written.append(path)
    return written
