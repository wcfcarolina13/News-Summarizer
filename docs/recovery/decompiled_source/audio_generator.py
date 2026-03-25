# Source Generated with Decompyle++
# File: audio_generator.pyc (Python 3.12)

'''Audio generation utilities for the Audio Briefing application.'''
import os
import sys
import subprocess
import threading
import io
from contextlib import redirect_stdout, redirect_stderr

class AudioGenerator:
    '''Handles audio generation - runs scripts in-process when frozen, via subprocess otherwise.'''
    
    def __init__(self, base_dir, status_callback = (None, None)):
        '''Initialize AudioGenerator.

        Args:
            base_dir: Base directory for output files. Defaults to script directory.
            status_callback: Function to call with status updates (msg, color)
        '''
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':
                app_support = os.path.expanduser('~/Library/Application Support/Daily Audio Briefing')
            elif sys.platform == 'win32':
                app_support = os.path.join(os.environ.get('APPDATA', ''), 'Daily Audio Briefing')
            else:
                app_support = os.path.expanduser('~/.daily-audio-briefing')
            if not os.path.exists(app_support):
                os.makedirs(app_support, exist_ok = True)
            self.base_dir = app_support
        elif not base_dir:
            base_dir
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        if not status_callback:
            status_callback
        self.status_callback = self._default_callback

    
    def _default_callback(self, message, color = ('gray',)):
        '''Default status callback that prints to console.'''
        print(f'''[{color}] {message}''')

    
    def get_python_executable(self):
        '''Get the appropriate Python executable path.'''
        if getattr(sys, 'frozen', False):
            return '/usr/bin/env python3'
        return sys.executable

    
    def run_script(self, script_name, output_name, extra_args, env_vars, completion_callback = (None, None, None)):
        '''Run a Python script asynchronously.

        When running as a frozen app (PyInstaller), this imports and runs the script
        directly in-process. When running normally, it uses subprocess.

        Args:
            script_name: Name of the script to run
            output_name: Description of expected output
            extra_args: Additional command line arguments
            env_vars: Additional environment variables
            completion_callback: Function to call when complete (success: bool)
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def _run_script_in_process(self, script_name, extra_args, stdout_capture, stderr_capture, log_path):
        """Run a script by importing it and calling its main function.

        This is used when running as a frozen app where subprocess won't work.
        """
        old_argv = sys.argv
        sys.argv = [
            script_name] + extra_args
    # WARNING: Decompyle incomplete

    
    def _run_script_subprocess(self, script_name, extra_args, env_vars, log_path):
        '''Run a script via subprocess (original development mode behavior).'''
        python_exe = self.get_python_executable()
        script_path = os.path.join(self.base_dir, script_name)
        cmd = [
            python_exe,
            script_path] + extra_args
        process_env = os.environ.copy()
        if env_vars:
            process_env.update(env_vars)
        result = subprocess.run(cmd, capture_output = True, text = True, cwd = self.base_dir, env = process_env, timeout = 3600)
    # WARNING: Decompyle incomplete

    
    def play_sample(self, voice):
        '''Generate and play a voice sample.

        Args:
            voice: Voice name to use for sample
        '''
        pass
    # WARNING: Decompyle incomplete

    
    def play_gtts_sample(self):
        '''Generate and play a gTTS sample to demonstrate the fast voice.'''
        pass
    # WARNING: Decompyle incomplete

    
    def open_folder(self):
        '''Open the output folder in the system file browser.'''
        if sys.platform == 'darwin':
            subprocess.run([
                'open',
                self.base_dir])
            return None
        if sys.platform == 'win32':
            os.startfile(self.base_dir)
            return None
        subprocess.run([
            'xdg-open',
            self.base_dir])
        return None
    # WARNING: Decompyle incomplete


