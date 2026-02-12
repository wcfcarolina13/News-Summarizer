"""Audio generation utilities for the Audio Briefing application."""
import os
import sys
import subprocess
import threading
import io
from contextlib import redirect_stdout, redirect_stderr


class AudioGenerator:
    """Handles audio generation - runs scripts in-process when frozen, via subprocess otherwise."""

    def __init__(self, base_dir=None, status_callback=None):
        """Initialize AudioGenerator.

        Args:
            base_dir: Base directory for output files. Defaults to script directory.
            status_callback: Function to call with status updates (msg, color)
        """
        if getattr(sys, "frozen", False):
            # When running as frozen app, use Application Support for data files
            # This ensures a writable location even if app is in /Applications
            if sys.platform == "darwin":
                app_support = os.path.expanduser("~/Library/Application Support/Daily Audio Briefing")
            elif sys.platform == "win32":
                app_support = os.path.join(os.environ.get("APPDATA", ""), "Daily Audio Briefing")
            else:
                app_support = os.path.expanduser("~/.daily-audio-briefing")

            # Create the directory if it doesn't exist
            if not os.path.exists(app_support):
                os.makedirs(app_support, exist_ok=True)

            self.base_dir = app_support
        else:
            self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.status_callback = status_callback or self._default_callback

    def _default_callback(self, message, color="gray"):
        """Default status callback that prints to console."""
        print(f"[{color}] {message}")

    def get_python_executable(self):
        """Get the appropriate Python executable path."""
        if getattr(sys, "frozen", False):
            return "/usr/bin/env python3"
        return sys.executable

    def run_script(self, script_name, output_name, extra_args=None, env_vars=None, completion_callback=None):
        """Run a Python script asynchronously.

        When running as a frozen app (PyInstaller), this imports and runs the script
        directly in-process. When running normally, it uses subprocess.

        Args:
            script_name: Name of the script to run
            output_name: Description of expected output
            extra_args: Additional command line arguments
            env_vars: Additional environment variables
            completion_callback: Function to call when complete (success: bool)
        """
        extra_args = extra_args or []

        def task():
            log_path = os.path.join(self.base_dir, "gui_log.txt")
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()

            try:
                # Set environment variables
                old_env = {}
                if env_vars:
                    for key, val in env_vars.items():
                        old_env[key] = os.environ.get(key)
                        os.environ[key] = val

                # Change to base directory for proper file output
                old_cwd = os.getcwd()
                os.chdir(self.base_dir)

                success = False
                try:
                    if getattr(sys, "frozen", False):
                        # FROZEN MODE: Run script as imported module
                        success = self._run_script_in_process(
                            script_name, extra_args, stdout_capture, stderr_capture, log_path
                        )
                    else:
                        # DEVELOPMENT MODE: Use subprocess (original behavior)
                        success = self._run_script_subprocess(
                            script_name, extra_args, env_vars, log_path
                        )
                finally:
                    # Restore working directory
                    os.chdir(old_cwd)

                    # Restore environment
                    if env_vars:
                        for key, orig_val in old_env.items():
                            if orig_val is None:
                                os.environ.pop(key, None)
                            else:
                                os.environ[key] = orig_val

                if success:
                    self.status_callback(f"Done! Generated {output_name}", "green")
                    if completion_callback:
                        completion_callback(True)
                else:
                    self.status_callback(f"Error. See gui_log.txt", "red")
                    if completion_callback:
                        completion_callback(False)

            except Exception as e:
                # Log the exception
                with open(log_path, "a", encoding="utf-8") as log:
                    log.write(f"\nException in task: {e}\n")
                    import traceback
                    log.write(traceback.format_exc())
                self.status_callback(f"Exception: {e}", "red")
                if completion_callback:
                    completion_callback(False)

        threading.Thread(target=task, daemon=True).start()

    def _run_script_in_process(self, script_name, extra_args, stdout_capture, stderr_capture, log_path):
        """Run a script by importing it and calling its main function.

        This is used when running as a frozen app where subprocess won't work.
        """
        # Build fake sys.argv for the script
        old_argv = sys.argv
        sys.argv = [script_name] + extra_args

        try:
            with open(log_path, "w", encoding="utf-8") as log:
                log.write(f"--- Running {script_name} (in-process mode) ---\n")
                log.write(f"Args: {extra_args}\n")
                log.write(f"Working directory: {os.getcwd()}\n")
                log.write("-" * 50 + "\n")

            # Import and run the appropriate script
            if script_name == "get_youtube_news.py":
                import get_youtube_news
                # Reload to pick up new arguments
                import importlib
                importlib.reload(get_youtube_news)
                # The script runs on import due to if __name__ == "__main__"
                # So we need to call main() explicitly
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    get_youtube_news.main()

            elif script_name == "make_audio_fast.py":
                import make_audio_fast
                import importlib
                importlib.reload(make_audio_fast)
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    make_audio_fast.main()

            elif script_name == "make_audio_quality.py":
                import make_audio_quality
                import importlib
                importlib.reload(make_audio_quality)
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    make_audio_quality.main()
            else:
                raise ValueError(f"Unknown script: {script_name}")

            # Log output
            with open(log_path, "a", encoding="utf-8") as log:
                log.write("STDOUT:\n")
                log.write(stdout_capture.getvalue())
                log.write("\nSTDERR:\n")
                log.write(stderr_capture.getvalue())
                log.write("\nCompleted successfully.\n")

            return True

        except SystemExit as e:
            # Script called sys.exit() - check exit code
            with open(log_path, "a", encoding="utf-8") as log:
                log.write("STDOUT:\n")
                log.write(stdout_capture.getvalue())
                log.write("\nSTDERR:\n")
                log.write(stderr_capture.getvalue())
                log.write(f"\nScript exited with code: {e.code}\n")
            return e.code == 0 or e.code is None

        except Exception as e:
            with open(log_path, "a", encoding="utf-8") as log:
                log.write("STDOUT:\n")
                log.write(stdout_capture.getvalue())
                log.write("\nSTDERR:\n")
                log.write(stderr_capture.getvalue())
                log.write(f"\nException: {e}\n")
                import traceback
                log.write(traceback.format_exc())
            return False

        finally:
            sys.argv = old_argv

    def _run_script_subprocess(self, script_name, extra_args, env_vars, log_path):
        """Run a script via subprocess (original development mode behavior)."""
        python_exe = self.get_python_executable()
        script_path = os.path.join(self.base_dir, script_name)
        cmd = [python_exe, script_path] + extra_args

        process_env = os.environ.copy()
        if env_vars:
            process_env.update(env_vars)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.base_dir,
                env=process_env,
                timeout=3600
            )
        except subprocess.TimeoutExpired as tex:
            with open(log_path, "w", encoding="utf-8") as log:
                log.write(f"--- Timeout running {script_name} ---\n")
                log.write(f"Args: {extra_args}\n")
                log.write(f"Timeout after: {tex.timeout}s\n")
            return False

        # Log the execution
        with open(log_path, "w", encoding="utf-8") as log:
            log.write(f"--- Running {script_name} (subprocess mode) ---\n")
            log.write(f"Command: {' '.join(cmd)}\n")
            log.write(f"Args: {extra_args}\n")
            log.write(f"Working directory: {self.base_dir}\n")
            log.write(f"Return Code: {result.returncode}\n")
            log.write("STDOUT:\n")
            log.write(result.stdout)
            log.write("\nSTDERR:\n")
            log.write(result.stderr)

        return result.returncode == 0

    def play_sample(self, voice):
        """Generate and play a voice sample.

        Args:
            voice: Voice name to use for sample
        """
        self.status_callback(f"Generating sample for {voice}...", "orange")

        def task():
            try:
                sample_file = os.path.join(self.base_dir, "sample_temp.wav")

                if os.path.exists(sample_file):
                    os.remove(sample_file)

                # Use in-process method when frozen
                if getattr(sys, "frozen", False):
                    old_cwd = os.getcwd()
                    os.chdir(self.base_dir)
                    try:
                        old_argv = sys.argv
                        sys.argv = [
                            "make_audio_quality.py",
                            "--voice", voice,
                            "--text", "This is a sample of the selected voice.",
                            "--output", sample_file,
                            "--format", "wav"
                        ]
                        try:
                            import make_audio_quality
                            import importlib
                            importlib.reload(make_audio_quality)
                            make_audio_quality.main()
                        finally:
                            sys.argv = old_argv
                    finally:
                        os.chdir(old_cwd)
                else:
                    # Subprocess mode for development
                    python_exe = self.get_python_executable()
                    cmd = [
                        python_exe,
                        os.path.join(self.base_dir, "make_audio_quality.py"),
                        "--voice", voice,
                        "--text", "This is a sample of the selected voice.",
                        "--output", sample_file,
                        "--format", "wav"
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.base_dir)
                    if result.returncode != 0:
                        error_msg = result.stderr or result.stdout or "Unknown error"
                        self.status_callback(f"Sample Error: {error_msg[:50]}", "red")
                        return

                if os.path.exists(sample_file):
                    self.status_callback("Playing sample...", "green")

                    # Play audio based on platform
                    if sys.platform == "darwin":
                        subprocess.run(["afplay", sample_file])
                    elif sys.platform == "win32":
                        import winsound
                        winsound.PlaySound(sample_file, winsound.SND_FILENAME)
                    else:
                        subprocess.run(["aplay", sample_file])

                    # Clean up sample file
                    try:
                        os.remove(sample_file)
                    except:
                        pass

                    self.status_callback("Ready", "gray")
                else:
                    self.status_callback("Sample Error: File not created", "red")

            except Exception as e:
                self.status_callback(f"Sample Error: {str(e)[:50]}", "red")

        threading.Thread(target=task, daemon=True).start()

    def play_gtts_sample(self):
        """Generate and play a gTTS sample to demonstrate the fast voice."""
        self.status_callback("Generating gTTS sample...", "orange")

        def task():
            try:
                sample_file = os.path.join(self.base_dir, "gtts_sample_temp.mp3")

                if os.path.exists(sample_file):
                    os.remove(sample_file)

                # Generate sample using gTTS
                from gtts import gTTS
                sample_text = "This is a sample of the gTTS fast voice. It's quick to generate but has a more robotic quality."
                tts = gTTS(text=sample_text, lang='en')
                tts.save(sample_file)

                if os.path.exists(sample_file):
                    self.status_callback("Playing gTTS sample...", "green")

                    # Play audio based on platform
                    if sys.platform == "darwin":
                        subprocess.run(["afplay", sample_file])
                    elif sys.platform == "win32":
                        import winsound
                        # winsound doesn't support mp3, use a different approach
                        try:
                            os.startfile(sample_file)
                        except:
                            subprocess.run(["start", sample_file], shell=True)
                    else:
                        subprocess.run(["mpg123", "-q", sample_file])

                    # Clean up sample file after a delay
                    import time
                    time.sleep(1)  # Allow time for playback to finish
                    try:
                        os.remove(sample_file)
                    except:
                        pass

                    self.status_callback("Ready", "gray")
                else:
                    self.status_callback("gTTS Sample Error: File not created", "red")

            except Exception as e:
                self.status_callback(f"gTTS Sample Error: {str(e)[:50]}", "red")

        threading.Thread(target=task, daemon=True).start()

    def open_folder(self):
        """Open the output folder in the system file browser."""
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", self.base_dir])
            elif sys.platform == "win32":
                os.startfile(self.base_dir)
            else:
                subprocess.run(["xdg-open", self.base_dir])
        except Exception:
            pass
