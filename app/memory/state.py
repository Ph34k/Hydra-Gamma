import os
import time
import json
import shutil
import tempfile
from typing import Dict, Any, Optional
from app.logger import logger

class StateMonitor:
    """
    Monitors the environment state (pwd, ls, env) and provides synchronization mechanisms.
    """
    def __init__(self):
        self.last_check_time = 0
        self.check_interval = 30 # seconds

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Capture the current state of the environment.
        """
        snapshot = {}
        try:
            snapshot["pwd"] = os.getcwd()
            # limit to 20 files
            try:
                snapshot["ls"] = os.listdir(os.getcwd())[:20]
            except OSError:
                snapshot["ls"] = []

            # Only capture relevant environment variables
            snapshot["env"] = {k: v for k, v in os.environ.items() if k in ["USER", "HOME", "PATH", "LANG"]}

            # Additional checks: processes, disk usage
            # Implementing ps/df checks would require subprocess calls, keeping simple for now
            self.last_check_time = time.time()
            return snapshot
        except Exception as e:
            logger.error(f"Failed to get environment snapshot: {e}")
            return {}

    def check_heartbeat(self) -> bool:
        """
        Check if a heartbeat update is needed based on time elapsed since last check.
        """
        return (time.time() - self.last_check_time) > self.check_interval


class AtomicState:
    """Helper for atomic persistence of state files."""

    @staticmethod
    def save(filepath: str, data: Dict[str, Any]):
        """
        Save data to a file atomically.
        1. Write to temp file
        2. fsync
        3. Rename to target file
        """
        dir_path = os.path.dirname(filepath) or "."
        try:
            with tempfile.NamedTemporaryFile('w', dir=dir_path, delete=False) as tf:
                json.dump(data, tf, indent=2, default=str)
                tf.flush()
                os.fsync(tf.fileno())
                temp_name = tf.name

            shutil.move(temp_name, filepath)
            logger.debug(f"State saved atomically to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save state atomically: {e}")
            if 'temp_name' in locals() and os.path.exists(temp_name):
                os.remove(temp_name)
