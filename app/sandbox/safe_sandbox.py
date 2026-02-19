from abc import ABC, abstractmethod
from typing import Dict, Optional, Protocol, Any
from uuid import UUID, uuid4

from app.config import SandboxSettings
from app.sandbox.monitor import ResourceMonitor

class SafeSandbox(ABC):
    """Abstract base class for a safe sandbox with resource monitoring."""

    def __init__(self, config: Optional[SandboxSettings] = None):
        self.id = uuid4()
        self.config = config or SandboxSettings()
        # Initialize Resource Monitor with limits from config
        self.monitor = ResourceMonitor(
            self.id,
            {
                "timeout": self.config.timeout,
                "memory_limit": self.config.memory_limit,
                "cpu_limit": self.config.cpu_limit
            }
        )

    @abstractmethod
    async def run_command(self, command: str, timeout: Optional[int] = None) -> str:
        """Executes command safely."""
        pass

    def check_resources(self):
        """Checks resource usage and raises error if limits exceeded."""
        if self.monitor.check_timeout():
            raise TimeoutError("Sandbox execution timeout exceeded.")
        # Additional checks can be added here based on monitor implementation

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleans up resources."""
        pass
