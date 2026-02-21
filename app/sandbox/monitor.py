import psutil
import time
import os
import signal
from typing import Dict, Any, Optional
from uuid import UUID

try:
    import docker
except ImportError:
    docker = None

class ResourceMonitor:
    """Monitors resource usage of a sandbox process or container."""

    def __init__(self, sandbox_id: UUID, limits: Dict[str, Any], container_id: Optional[str] = None):
        self.sandbox_id = sandbox_id
        self.limits = limits
        self.container_id = container_id
        self.start_time = time.time()
        self._process = None
        self._docker_client = docker.from_env() if docker and container_id else None

    def attach_process(self, pid: int):
        """Attach to a process ID to monitor."""
        try:
            self._process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            raise RuntimeError(f"Process {pid} not found.")

    def check_cpu_usage(self) -> float:
        """Check CPU usage as a percentage."""
        if self.container_id and self._docker_client:
            try:
                container = self._docker_client.containers.get(self.container_id)
                stats = container.stats(stream=False)
                # Calculate CPU usage from stats (simplified)
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                if system_delta > 0:
                    return (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100.0
                return 0.0
            except Exception:
                return 0.0

        if not self._process:
            return 0.0
        try:
            return self._process.cpu_percent(interval=0.1)
        except psutil.NoSuchProcess:
            return 0.0

    def check_memory_usage(self) -> float:
        """Check memory usage in MB."""
        if self.container_id and self._docker_client:
            try:
                container = self._docker_client.containers.get(self.container_id)
                stats = container.stats(stream=False)
                return stats['memory_stats']['usage'] / (1024 * 1024)
            except Exception:
                return 0.0

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
        """Kill the monitored process or container."""
        if self.container_id and self._docker_client:
            try:
                container = self._docker_client.containers.get(self.container_id)
                container.kill()
            except Exception:
                pass
            return

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
