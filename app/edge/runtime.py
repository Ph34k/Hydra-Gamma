import os
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.agent.core import AgentCore
from app.logger import logger
from app.edge.sanitizer import Sanitizer

class LocalRuntime:
    """
    Simulates a local Edge AI runtime environment.
    (Chapter 51: Soberania de Dados e Edge AI)
    """
    def __init__(self, workspace_path: str = "./edge_workspace"):
        self.workspace_path = workspace_path
        os.makedirs(workspace_path, exist_ok=True)
        self.is_connected = False

    def connect_cloud(self):
        """Simulate connecting to the cloud orchestrator."""
        self.is_connected = True
        logger.info("Edge Runtime: Connected to Cloud.")

    def disconnect_cloud(self):
        self.is_connected = False
        logger.info("Edge Runtime: Disconnected (Local Mode).")

    def sync_data(self, data: Dict[str, Any]):
        """Sync data to cloud, applying sanitization first."""
        if not self.is_connected:
            logger.warning("Edge Runtime: Cannot sync, offline.")
            return

        sanitized_data = Sanitizer.sanitize(data)
        logger.info(f"Edge Runtime: Syncing sanitized data: {sanitized_data.keys()}")
        # In real impl, this would POST to the cloud API
        return sanitized_data

class LocalAgent(AgentCore):
    """
    An agent optimized for running on Edge devices.
    Uses local tools and minimal memory footprint.
    """
    name: str = "EdgeAgent"
    description: str = "Lightweight agent for local processing."

    def __init__(self, **data):
        super().__init__(**data)
        self.runtime = LocalRuntime()

    async def act(self) -> str:
        """
        Override act to prefer local execution.
        """
        # For V1, we just log that we are running on edge
        logger.info("EdgeAgent: Executing action locally...")
        return await super().act()

    async def report_status(self):
        """Report status to cloud if connected."""
        status = {
            "agent_id": self.session_id,
            "state": self.state,
            "metrics": self.performance_monitor.get_metrics() if self.performance_monitor else {}
        }
        self.runtime.sync_data(status)
