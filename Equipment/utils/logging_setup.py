"""
utils/logging_setup.py -- Global Timestamped Stream & Logger interceptor
Prepends [YYYY-MM-DD HH:MM:SS] to every printed log line dynamically
and appends output in append mode to a rolling log file (backend.log).
"""
import sys
import os
import re
from datetime import datetime

# Regex pattern to match and strip ANSI escape sequences (terminal colors)
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

class TimestampedStream:
    def __init__(self, original_stream, log_file=None):
        self.stream = original_stream
        self.log_file = log_file
        self.newline = True

    def write(self, message):
        if not message:
            return
            
        # Split message by newline to prepend timestamps correctly
        parts = message.split('\n')
        for i, part in enumerate(parts):
            if i > 0:
                # Write original newline character
                self.stream.write('\n')
                if self.log_file:
                    self.log_file.write('\n')
                self.newline = True
                
            if part:
                if self.newline:
                    # Capture exact current time
                    ts = datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
                    self.stream.write(ts)
                    if self.log_file:
                        self.log_file.write(ts)
                    self.newline = False
                
                self.stream.write(part)
                if self.log_file:
                    # Clean terminal color escape sequences for clean file logs
                    clean_part = ANSI_ESCAPE.sub('', part)
                    self.log_file.write(clean_part)

    def flush(self):
        self.stream.flush()
        if self.log_file:
            self.log_file.flush()

    def __getattr__(self, name):
        """
        Delegate all standard stream attributes (e.g., .isatty(), .fileno(), .encoding)
        to the original system stream. This prevents AttributeErrors when third-party
        libraries inspect stdout or stderr.
        """
        return getattr(self.stream, name)


def setup_logging(log_filename="backend.log"):
    """
    Globally configures uvicorn and print statements to include date-time timestamps
    and appends them (without overwriting) to a local rolling log file.
    """
    # Resolve absolute paths to verify if we are already redirected to the same target file
    abs_log_path = os.path.abspath(log_filename)
    
    dup_stdout = False
    if hasattr(sys.stdout, "name") and sys.stdout.name:
        try:
            if os.path.abspath(sys.stdout.name) == abs_log_path:
                dup_stdout = True
        except Exception:
            pass

    dup_stderr = False
    if hasattr(sys.stderr, "name") and sys.stderr.name:
        try:
            if os.path.abspath(sys.stderr.name) == abs_log_path:
                dup_stderr = True
        except Exception:
            pass

    # Open the log file in APPEND mode ('a') with UTF-8 encoding
    log_file = open(log_filename, "a", encoding="utf-8", buffering=1)
    
    # Avoid duplicate writes if the streams are already redirected to the same log file by the OS/shell
    stdout_log = None if dup_stdout else log_file
    stderr_log = None if dup_stderr else log_file

    sys.stdout = TimestampedStream(sys.stdout, stdout_log)
    sys.stderr = TimestampedStream(sys.stderr, stderr_log)
    print(f"[System] Global timestamped logging active. Appending to: {log_filename}")
