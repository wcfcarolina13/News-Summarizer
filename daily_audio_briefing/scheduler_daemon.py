#!/usr/bin/env python3
"""
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
"""

import os
import sys
import time
import signal
import json
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_daemon_paths():
    """Get paths for daemon files (PID file, log file)."""
    if sys.platform == 'darwin':
        base_dir = os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
    elif sys.platform == 'win32':
        base_dir = os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
    else:
        base_dir = os.path.expanduser("~/.daily-audio-briefing")

    os.makedirs(base_dir, exist_ok=True)

    return {
        'pid_file': os.path.join(base_dir, 'scheduler_daemon.pid'),
        'log_file': os.path.join(base_dir, 'scheduler_daemon.log'),
        'base_dir': base_dir
    }


def setup_logging(log_file: str):
    """Configure logging for the daemon."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()  # Also log to console if running in foreground
        ]
    )
    return logging.getLogger('scheduler_daemon')


def is_daemon_running(pid_file: str) -> bool:
    """Check if the daemon is currently running."""
    if not os.path.exists(pid_file):
        return False

    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())

        # Check if process exists
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, FileNotFoundError):
        # Process doesn't exist or PID file is invalid
        # Clean up stale PID file
        try:
            os.remove(pid_file)
        except:
            pass
        return False


def get_daemon_pid(pid_file: str) -> int:
    """Get the PID of the running daemon, or None if not running."""
    if not os.path.exists(pid_file):
        return None

    try:
        with open(pid_file, 'r') as f:
            return int(f.read().strip())
    except:
        return None


def write_pid_file(pid_file: str):
    """Write the current process PID to the PID file."""
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))


def remove_pid_file(pid_file: str):
    """Remove the PID file."""
    try:
        os.remove(pid_file)
    except:
        pass


def run_scheduler_loop(logger):
    """Main scheduler loop - runs tasks at their scheduled times."""
    from scheduler import get_scheduler

    logger.info("Scheduler daemon starting...")

    # Initialize scheduler
    def on_task_complete(task, success, message):
        if success:
            logger.info(f"Task '{task.name}' completed: {message}")
        else:
            logger.error(f"Task '{task.name}' failed: {message}")

    scheduler = get_scheduler(on_task_complete=on_task_complete)

    # Start the scheduler
    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.tasks)} tasks")

    # Keep running until terminated
    try:
        while True:
            time.sleep(60)  # Check every minute

            # Reload tasks in case they were modified by the GUI
            scheduler.load_tasks()

    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        scheduler.stop()
        logger.info("Scheduler daemon stopped")


def start_daemon():
    """Start the daemon as a background process."""
    paths = get_daemon_paths()

    if is_daemon_running(paths['pid_file']):
        print("Scheduler daemon is already running")
        return False

    # Fork to create daemon (Unix-like systems)
    if sys.platform != 'win32':
        # First fork
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process - exit
                print(f"Scheduler daemon started (PID: {pid})")
                return True
        except OSError as e:
            print(f"Fork failed: {e}")
            return False

        # Decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # Second fork
        try:
            pid = os.fork()
            if pid > 0:
                # Exit from second parent
                sys.exit(0)
        except OSError as e:
            sys.exit(1)

        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()

        with open('/dev/null', 'r') as devnull:
            os.dup2(devnull.fileno(), sys.stdin.fileno())

        # Redirect stdout/stderr to log file
        log_file = open(paths['log_file'], 'a')
        os.dup2(log_file.fileno(), sys.stdout.fileno())
        os.dup2(log_file.fileno(), sys.stderr.fileno())

    else:
        # Windows - use subprocess to run in background
        import subprocess

        # Start a new process that runs this script with 'run' argument
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            [sys.executable, __file__, 'run'],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            stdout=open(paths['log_file'], 'a'),
            stderr=subprocess.STDOUT
        )

        print(f"Scheduler daemon started (PID: {process.pid})")
        return True

    # Write PID file
    write_pid_file(paths['pid_file'])

    # Setup logging
    logger = setup_logging(paths['log_file'])

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        remove_pid_file(paths['pid_file'])
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Run the scheduler loop
    try:
        run_scheduler_loop(logger)
    finally:
        remove_pid_file(paths['pid_file'])

    return True


def stop_daemon():
    """Stop the running daemon."""
    paths = get_daemon_paths()

    pid = get_daemon_pid(paths['pid_file'])
    if pid is None:
        print("Scheduler daemon is not running")
        return False

    try:
        # Send SIGTERM to gracefully stop
        os.kill(pid, signal.SIGTERM)

        # Wait for process to stop
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except OSError:
                # Process has stopped
                print("Scheduler daemon stopped")
                remove_pid_file(paths['pid_file'])
                return True

        # Force kill if still running
        os.kill(pid, signal.SIGKILL)
        print("Scheduler daemon force stopped")
        remove_pid_file(paths['pid_file'])
        return True

    except OSError as e:
        print(f"Error stopping daemon: {e}")
        remove_pid_file(paths['pid_file'])
        return False


def daemon_status():
    """Print the status of the daemon."""
    paths = get_daemon_paths()

    if is_daemon_running(paths['pid_file']):
        pid = get_daemon_pid(paths['pid_file'])
        print(f"Scheduler daemon is running (PID: {pid})")
        return True
    else:
        print("Scheduler daemon is not running")
        return False


def run_foreground():
    """Run the scheduler in the foreground (for debugging)."""
    paths = get_daemon_paths()

    if is_daemon_running(paths['pid_file']):
        print("Scheduler daemon is already running in background")
        return False

    # Write PID file
    write_pid_file(paths['pid_file'])

    # Setup logging
    logger = setup_logging(paths['log_file'])

    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        remove_pid_file(paths['pid_file'])
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    print("Running scheduler in foreground (Ctrl+C to stop)...")

    try:
        run_scheduler_loop(logger)
    finally:
        remove_pid_file(paths['pid_file'])

    return True


# === API for GUI Integration ===

def start_background_scheduler() -> bool:
    """Start the background scheduler daemon. Called from GUI."""
    paths = get_daemon_paths()

    if is_daemon_running(paths['pid_file']):
        return True  # Already running

    # Start as subprocess
    import subprocess

    script_path = os.path.abspath(__file__)

    if sys.platform == 'win32':
        # Windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        process = subprocess.Popen(
            [sys.executable, script_path, 'run'],
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
            stdout=open(paths['log_file'], 'a'),
            stderr=subprocess.STDOUT
        )
    else:
        # macOS/Linux
        process = subprocess.Popen(
            [sys.executable, script_path, 'start'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

    # Wait a moment and verify it started
    time.sleep(1)
    return is_daemon_running(paths['pid_file'])


def stop_background_scheduler() -> bool:
    """Stop the background scheduler daemon. Called from GUI."""
    return stop_daemon()


def is_background_scheduler_running() -> bool:
    """Check if the background scheduler is running. Called from GUI."""
    paths = get_daemon_paths()
    return is_daemon_running(paths['pid_file'])


def get_daemon_log_path() -> str:
    """Get the path to the daemon log file."""
    paths = get_daemon_paths()
    return paths['log_file']


# === Launch on Login Management ===

def enable_launch_on_login() -> bool:
    """Enable the scheduler to launch when the user logs in."""
    if sys.platform == 'darwin':
        return _enable_launch_on_login_macos()
    elif sys.platform == 'win32':
        return _enable_launch_on_login_windows()
    else:
        return _enable_launch_on_login_linux()


def disable_launch_on_login() -> bool:
    """Disable the scheduler from launching on login."""
    if sys.platform == 'darwin':
        return _disable_launch_on_login_macos()
    elif sys.platform == 'win32':
        return _disable_launch_on_login_windows()
    else:
        return _disable_launch_on_login_linux()


def is_launch_on_login_enabled() -> bool:
    """Check if launch on login is enabled."""
    if sys.platform == 'darwin':
        return _is_launch_on_login_enabled_macos()
    elif sys.platform == 'win32':
        return _is_launch_on_login_enabled_windows()
    else:
        return _is_launch_on_login_enabled_linux()


def _enable_launch_on_login_macos() -> bool:
    """Create a LaunchAgent plist for macOS."""
    plist_dir = os.path.expanduser("~/Library/LaunchAgents")
    plist_path = os.path.join(plist_dir, "com.dailyaudiobriefing.scheduler.plist")

    os.makedirs(plist_dir, exist_ok=True)

    script_path = os.path.abspath(__file__)
    python_path = sys.executable

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dailyaudiobriefing.scheduler</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{get_daemon_paths()['log_file']}</string>
    <key>StandardErrorPath</key>
    <string>{get_daemon_paths()['log_file']}</string>
</dict>
</plist>
"""

    try:
        with open(plist_path, 'w') as f:
            f.write(plist_content)

        # Load the agent
        os.system(f'launchctl load "{plist_path}"')
        return True
    except Exception as e:
        print(f"Error enabling launch on login: {e}")
        return False


def _disable_launch_on_login_macos() -> bool:
    """Remove the LaunchAgent plist for macOS."""
    plist_path = os.path.expanduser("~/Library/LaunchAgents/com.dailyaudiobriefing.scheduler.plist")

    try:
        if os.path.exists(plist_path):
            # Unload the agent
            os.system(f'launchctl unload "{plist_path}"')
            os.remove(plist_path)
        return True
    except Exception as e:
        print(f"Error disabling launch on login: {e}")
        return False


def _is_launch_on_login_enabled_macos() -> bool:
    """Check if LaunchAgent exists for macOS."""
    plist_path = os.path.expanduser("~/Library/LaunchAgents/com.dailyaudiobriefing.scheduler.plist")
    return os.path.exists(plist_path)


def _enable_launch_on_login_windows() -> bool:
    """Add to Windows startup registry."""
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        script_path = os.path.abspath(__file__)
        python_path = sys.executable

        command = f'"{python_path}" "{script_path}" run'

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "DailyAudioBriefingScheduler", 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error enabling launch on login: {e}")
        return False


def _disable_launch_on_login_windows() -> bool:
    """Remove from Windows startup registry."""
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, "DailyAudioBriefingScheduler")
        except FileNotFoundError:
            pass  # Already doesn't exist
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error disabling launch on login: {e}")
        return False


def _is_launch_on_login_enabled_windows() -> bool:
    """Check if startup registry entry exists for Windows."""
    try:
        import winreg

        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, "DailyAudioBriefingScheduler")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def _enable_launch_on_login_linux() -> bool:
    """Create autostart desktop entry for Linux."""
    autostart_dir = os.path.expanduser("~/.config/autostart")
    desktop_path = os.path.join(autostart_dir, "dailyaudiobriefing-scheduler.desktop")

    os.makedirs(autostart_dir, exist_ok=True)

    script_path = os.path.abspath(__file__)
    python_path = sys.executable

    desktop_content = f"""[Desktop Entry]
Type=Application
Name=Daily Audio Briefing Scheduler
Exec={python_path} {script_path} run
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""

    try:
        with open(desktop_path, 'w') as f:
            f.write(desktop_content)
        return True
    except Exception as e:
        print(f"Error enabling launch on login: {e}")
        return False


def _disable_launch_on_login_linux() -> bool:
    """Remove autostart desktop entry for Linux."""
    desktop_path = os.path.expanduser("~/.config/autostart/dailyaudiobriefing-scheduler.desktop")

    try:
        if os.path.exists(desktop_path):
            os.remove(desktop_path)
        return True
    except Exception as e:
        print(f"Error disabling launch on login: {e}")
        return False


def _is_launch_on_login_enabled_linux() -> bool:
    """Check if autostart desktop entry exists for Linux."""
    desktop_path = os.path.expanduser("~/.config/autostart/dailyaudiobriefing-scheduler.desktop")
    return os.path.exists(desktop_path)


# === Main Entry Point ===

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: scheduler_daemon.py [start|stop|status|run]")
        print("  start  - Start the daemon in background")
        print("  stop   - Stop the running daemon")
        print("  status - Check if daemon is running")
        print("  run    - Run in foreground (for debugging)")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == 'start':
        success = start_daemon()
        sys.exit(0 if success else 1)

    elif command == 'stop':
        success = stop_daemon()
        sys.exit(0 if success else 1)

    elif command == 'status':
        running = daemon_status()
        sys.exit(0 if running else 1)

    elif command == 'run':
        run_foreground()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
