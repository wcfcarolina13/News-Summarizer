# Source Generated with Decompyle++
# File: scheduler_daemon.pyc (Python 3.12)

'''
Scheduler Daemon - Background process for scheduled extraction tasks

This script runs independently of the main GUI application, allowing scheduled
tasks to execute even when the app is closed. It can be:
1. Started/stopped from the GUI
2. Run as a standalone background process
3. Configured to launch on system startup

Usage:
    python scheduler_daemon.py start    # Start the daemon
    python scheduler_daemon.py stop     # Stop the daemon
    python scheduler_daemon.py status   # Check if running
    python scheduler_daemon.py run      # Run in foreground (for debugging)
'''
import os
import sys
import time
import signal
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def get_daemon_paths():
    '''Get paths for daemon files (PID file, log file).'''
    if sys.platform == 'darwin':
        base_dir = os.path.expanduser('~/Library/Application Support/Daily Audio Briefing')
    elif sys.platform == 'win32':
        base_dir = os.path.join(os.environ.get('APPDATA', ''), 'Daily Audio Briefing')
    else:
        base_dir = os.path.expanduser('~/.daily-audio-briefing')
    os.makedirs(base_dir, exist_ok = True)
    return {
        'pid_file': os.path.join(base_dir, 'scheduler_daemon.pid'),
        'log_file': os.path.join(base_dir, 'scheduler_daemon.log'),
        'base_dir': base_dir }


def setup_logging(log_file = None):
    '''Configure logging for the daemon.'''
    logging.basicConfig(level = logging.INFO, format = '%(asctime)s [%(levelname)s] %(message)s', handlers = [
        logging.FileHandler(log_file),
        logging.StreamHandler()])
    return logging.getLogger('scheduler_daemon')


def is_daemon_running(pid_file = None):
    '''Check if the daemon is currently running.'''
    if not os.path.exists(pid_file):
        return False
# WARNING: Decompyle incomplete


def get_daemon_pid(pid_file = None):
    '''Get the PID of the running daemon, or None if not running.'''
    if not os.path.exists(pid_file):
        return None
# WARNING: Decompyle incomplete


def write_pid_file(pid_file = None):
    '''Write the current process PID to the PID file.'''
    pass
# WARNING: Decompyle incomplete


def remove_pid_file(pid_file = None):
    '''Remove the PID file.'''
    os.remove(pid_file)
    return None
# WARNING: Decompyle incomplete


def run_scheduler_loop(logger):
    '''Main scheduler loop - runs tasks at their scheduled times.'''
    pass
# WARNING: Decompyle incomplete


def start_daemon():
    '''Start the daemon as a background process.'''
    pass
# WARNING: Decompyle incomplete


def stop_daemon():
    '''Stop the running daemon.'''
    paths = get_daemon_paths()
    pid = get_daemon_pid(paths['pid_file'])
# WARNING: Decompyle incomplete


def daemon_status():
    '''Print the status of the daemon.'''
    paths = get_daemon_paths()
    if is_daemon_running(paths['pid_file']):
        pid = get_daemon_pid(paths['pid_file'])
        print(f'''Scheduler daemon is running (PID: {pid})''')
        return True
    print('Scheduler daemon is not running')
    return False


def run_foreground():
    '''Run the scheduler in the foreground (for debugging).'''
    pass
# WARNING: Decompyle incomplete


def start_background_scheduler():
    '''Start the background scheduler daemon. Called from GUI.'''
    paths = get_daemon_paths()
    if is_daemon_running(paths['pid_file']):
        return True
    import subprocess
    script_path = os.path.abspath(__file__)
    if sys.platform == 'win32':
        startupinfo = subprocess.STARTUPINFO()
        subprocess.SW_HIDE = startupinfo, startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW, .dwFlags
        process = subprocess.Popen([
            sys.executable,
            script_path,
            'run'], startupinfo = startupinfo, creationflags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS, stdout = open(paths['log_file'], 'a'), stderr = subprocess.STDOUT)
    else:
        process = subprocess.Popen([
            sys.executable,
            script_path,
            'start'], stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL, start_new_session = True)
    time.sleep(1)
    return is_daemon_running(paths['pid_file'])


def stop_background_scheduler():
    '''Stop the background scheduler daemon. Called from GUI.'''
    return stop_daemon()


def is_background_scheduler_running():
    '''Check if the background scheduler is running. Called from GUI.'''
    paths = get_daemon_paths()
    return is_daemon_running(paths['pid_file'])


def get_daemon_log_path():
    '''Get the path to the daemon log file.'''
    paths = get_daemon_paths()
    return paths['log_file']


def enable_launch_on_login():
    '''Enable the scheduler to launch when the user logs in.'''
    if sys.platform == 'darwin':
        return _enable_launch_on_login_macos()
    if None.platform == 'win32':
        return _enable_launch_on_login_windows()
    return None()


def disable_launch_on_login():
    '''Disable the scheduler from launching on login.'''
    if sys.platform == 'darwin':
        return _disable_launch_on_login_macos()
    if None.platform == 'win32':
        return _disable_launch_on_login_windows()
    return None()


def is_launch_on_login_enabled():
    '''Check if launch on login is enabled.'''
    if sys.platform == 'darwin':
        return _is_launch_on_login_enabled_macos()
    if None.platform == 'win32':
        return _is_launch_on_login_enabled_windows()
    return None()


def _enable_launch_on_login_macos():
    '''Create a LaunchAgent plist for macOS.'''
    plist_dir = os.path.expanduser('~/Library/LaunchAgents')
    plist_path = os.path.join(plist_dir, 'com.dailyaudiobriefing.scheduler.plist')
    os.makedirs(plist_dir, exist_ok = True)
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0">\n<dict>\n    <key>Label</key>\n    <string>com.dailyaudiobriefing.scheduler</string>\n    <key>ProgramArguments</key>\n    <array>\n        <string>{python_path}</string>\n        <string>{script_path}</string>\n        <string>run</string>\n    </array>\n    <key>RunAtLoad</key>\n    <true/>\n    <key>KeepAlive</key>\n    <false/>\n    <key>StandardOutPath</key>\n    <string>{get_daemon_paths()['log_file']}</string>\n    <key>StandardErrorPath</key>\n    <string>{get_daemon_paths()['log_file']}</string>\n</dict>\n</plist>\n'''
# WARNING: Decompyle incomplete


def _disable_launch_on_login_macos():
    '''Remove the LaunchAgent plist for macOS.'''
    plist_path = os.path.expanduser('~/Library/LaunchAgents/com.dailyaudiobriefing.scheduler.plist')
    if os.path.exists(plist_path):
        subprocess.run([
            'launchctl',
            'unload',
            str(plist_path)])
        os.remove(plist_path)
    return True
# WARNING: Decompyle incomplete


def _is_launch_on_login_enabled_macos():
    '''Check if LaunchAgent exists for macOS.'''
    plist_path = os.path.expanduser('~/Library/LaunchAgents/com.dailyaudiobriefing.scheduler.plist')
    return os.path.exists(plist_path)


def _enable_launch_on_login_windows():
    '''Add to Windows startup registry.'''
    import winreg
    key_path = 'Software\\Microsoft\\Windows\\CurrentVersion\\Run'
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    command = f'''"{python_path}" "{script_path}" run'''
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, 'DailyAudioBriefingScheduler', 0, winreg.REG_SZ, command)
    winreg.CloseKey(key)
    return True
# WARNING: Decompyle incomplete


def _disable_launch_on_login_windows():
    '''Remove from Windows startup registry.'''
    import winreg
    key_path = 'Software\\Microsoft\\Windows\\CurrentVersion\\Run'
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
    winreg.DeleteValue(key, 'DailyAudioBriefingScheduler')
    winreg.CloseKey(key)
    return True
# WARNING: Decompyle incomplete


def _is_launch_on_login_enabled_windows():
    '''Check if startup registry entry exists for Windows.'''
    import winreg
    key_path = 'Software\\Microsoft\\Windows\\CurrentVersion\\Run'
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
    winreg.QueryValueEx(key, 'DailyAudioBriefingScheduler')
    winreg.CloseKey(key)
    return True
# WARNING: Decompyle incomplete


def _enable_launch_on_login_linux():
    '''Create autostart desktop entry for Linux.'''
    autostart_dir = os.path.expanduser('~/.config/autostart')
    desktop_path = os.path.join(autostart_dir, 'dailyaudiobriefing-scheduler.desktop')
    os.makedirs(autostart_dir, exist_ok = True)
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    desktop_content = f'''[Desktop Entry]\nType=Application\nName=Daily Audio Briefing Scheduler\nExec={python_path} {script_path} run\nHidden=false\nNoDisplay=true\nX-GNOME-Autostart-enabled=true\n'''
# WARNING: Decompyle incomplete


def _disable_launch_on_login_linux():
    '''Remove autostart desktop entry for Linux.'''
    desktop_path = os.path.expanduser('~/.config/autostart/dailyaudiobriefing-scheduler.desktop')
    if os.path.exists(desktop_path):
        os.remove(desktop_path)
    return True
# WARNING: Decompyle incomplete


def _is_launch_on_login_enabled_linux():
    '''Check if autostart desktop entry exists for Linux.'''
    desktop_path = os.path.expanduser('~/.config/autostart/dailyaudiobriefing-scheduler.desktop')
    return os.path.exists(desktop_path)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: scheduler_daemon.py [start|stop|status|run]')
        print('  start  - Start the daemon in background')
        print('  stop   - Stop the running daemon')
        print('  status - Check if daemon is running')
        print('  run    - Run in foreground (for debugging)')
        sys.exit(1)
    command = sys.argv[1].lower()
    if command == 'start':
        success = start_daemon()
        if success:
            sys.exit(0)
            return None
        None(1)
        return None
    if command == 'stop':
        success = stop_daemon()
        if success:
            sys.exit(0)
            return None
        None(1)
        return None
    if command == 'status':
        running = daemon_status()
        if running:
            sys.exit(0)
            return None
        None(1)
        return None
    if command == 'run':
        run_foreground()
        return None
    print(f'''Unknown command: {command}''')
    sys.exit(1)
    return None
