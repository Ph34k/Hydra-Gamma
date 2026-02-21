import json
import os
import re
from typing import Dict, List, Any
from app.exceptions import ToolError
from app.logger import logger

IMMUNITY_DB_PATH = "workspace/immunity_db.json"

class DigitalImmunitySystem:
    """
    Implements Digital Immunity System (Chapter 50).
    Monitors agent behavior for anomalies and blocks threats proactively.
    Enhanced with Persistence and Learning (Immunological Memory).
    """

    def __init__(self, db_path: str = IMMUNITY_DB_PATH):
        self.db_path = db_path
        self.failure_counts: Dict[str, int] = {}
        self.call_history: List[str] = []

        # Persistent Data
        self.blocked_tools: List[str] = []
        self.antibodies: List[str] = [] # List of regex patterns to block in args

        self.load_immunity_db()

    def load_immunity_db(self):
        """Load immunity database from disk."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    data = json.load(f)
                    self.blocked_tools = data.get("blocked_tools", [])
                    self.antibodies = data.get("antibodies", [])
                logger.info(f"Immunity System: Loaded {len(self.antibodies)} antibodies from DB.")
            except Exception as e:
                logger.error(f"Immunity System: Failed to load DB: {e}")
        else:
            logger.info("Immunity System: No existing DB found. Starting fresh.")

    def save_immunity_db(self):
        """Save immunity database to disk."""
        data = {
            "blocked_tools": self.blocked_tools,
            "antibodies": self.antibodies
        }
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("Immunity System: Saved DB to disk.")
        except Exception as e:
            logger.error(f"Immunity System: Failed to save DB: {e}")

    def add_antibody(self, pattern: str):
        """Add a new antibody (regex pattern) to block specific arguments."""
        if pattern not in self.antibodies:
            self.antibodies.append(pattern)
            self.save_immunity_db()
            logger.info(f"Immunity System: Generated antibody for pattern '{pattern}'")

    def learn_from_attack(self, tool_name: str, args: Dict[str, Any], reason: str):
        """
        Learn from a blocked or malicious attack by generating a new antibody.
        (Chapter 50.2: Anticorpos/Resposta)
        """
        logger.warning(f"Immunity System: Learning from attack on {tool_name}. Reason: {reason}")

        # Simple heuristic: generate a regex that blocks this specific argument pattern
        # Ideally, this would use an LLM to generalize the pattern, but for now we use exact match or simple token blocking.
        try:
            args_str = json.dumps(args, sort_keys=True)
            # Escape special characters to form a valid regex literal
            escaped_args = re.escape(args_str)
            self.add_antibody(escaped_args)
        except Exception as e:
            logger.error(f"Immunity System: Failed to learn from attack: {e}")

    def monitor_tool_call(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """
        Check if a tool call is safe. Returns True if safe, False if blocked.
        """
        if tool_name in self.blocked_tools:
            logger.warning(f"Immunity System blocked blacklisted tool: {tool_name}")
            return False

        # Check antibodies (content filtering)
        try:
             args_str = json.dumps(args, sort_keys=True)
        except:
             args_str = str(args)

        for antibody in self.antibodies:
            try:
                if re.search(antibody, args_str):
                    logger.warning(f"Immunity System: Antibody triggered for pattern '{antibody}'. Blocking call.")
                    return False
            except re.error:
                logger.error(f"Immunity System: Invalid regex pattern in DB: {antibody}")
                continue

        call_signature = f"{tool_name}:{args_str}"
        self.call_history.append(call_signature)

        # Check repetitive loop (Chapter 50.4: Behavioral Anomaly)
        if len(self.call_history) > 3:
            recent = self.call_history[-3:]
            if all(x == call_signature for x in recent):
                 logger.warning(f"Immunity System detected repetitive loop for {tool_name}. Blocking temporarily.")
                 return False

        return True

    def record_failure(self, tool_name: str):
        """Record a tool failure and potentially block the tool."""
        self.failure_counts[tool_name] = self.failure_counts.get(tool_name, 0) + 1
        if self.failure_counts[tool_name] > 5:
            logger.error(f"Immunity System: Tool {tool_name} failed too many times. Blocking it.")
            if tool_name not in self.blocked_tools:
                self.blocked_tools.append(tool_name)
                self.save_immunity_db()

    def record_success(self, tool_name: str):
        """Reset failure count on success."""
        self.failure_counts[tool_name] = 0

    def get_status(self) -> Dict[str, Any]:
        return {
            "blocked_tools": self.blocked_tools,
            "failure_counts": self.failure_counts,
            "antibodies_count": len(self.antibodies)
        }
