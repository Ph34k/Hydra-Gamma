import psutil
import time
import os
import signal
from typing import Dict, Any, Optional
from uuid import UUID

class ResourceMonitor:
    """Monitors resource usage of a sandbox process."""

    def __init__(self, sandbox_id: UUID, limits: Dict[str, Any]):
        self.sandbox_id = sandbox_id
        self.limits = limits
        self.start_time = time.time()
        self._process = None

    def attach_process(self, pid: int):
        """Attach to a process ID to monitor."""
        try:
            self._process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            raise RuntimeError(f"Process {pid} not found.")

    def check_cpu_usage(self) -> float:
        """Check CPU usage as a percentage."""
        if not self._process:
            return 0.0
        try:
            return self._process.cpu_percent(interval=0.1)
        except psutil.NoSuchProcess:
            return 0.0

    def check_memory_usage(self) -> float:
        """Check memory usage in MB."""
        if not self._process:
            return 0.0
        try:
            mem_info = self._process.memory_info()
            return mem_info.rss / (1024 * 1024)
        except psutil.NoSuchProcess:
            return 0.0

    def check_timeout(self) -> bool:
        """Check if execution time has exceeded the limit."""
        timeout = self.limits.get("timeout", 3600)
        return (time.time() - self.start_time) > timeout

    def kill_process(self, pid: Optional[int] = None):
        """Kill the monitored process or a specific PID."""
        target_pid = pid or (self._process.pid if self._process else None)
        if target_pid:
            try:
                os.kill(target_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def report_status(self) -> Dict[str, Any]:
        """Report current resource usage."""
        return {
            "sandbox_id": str(self.sandbox_id),
            "cpu_usage": self.check_cpu_usage(),
            "memory_usage": self.check_memory_usage(),
            "elapsed_time": time.time() - self.start_time,
            "timeout_exceeded": self.check_timeout(),
        }
