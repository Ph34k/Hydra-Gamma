from typing import Dict, List, Any
from app.exceptions import ToolError
from app.logger import logger

class DigitalImmunitySystem:
    """
    Implements Digital Immunity System (Chapter 50).
    Monitors agent behavior for anomalies and blocks threats proactively.
    """

    def __init__(self):
        self.failure_counts: Dict[str, int] = {}
        self.call_history: List[str] = []
        self.blocked_tools: List[str] = []
        self.antibodies: List[str] = [] # List of regex patterns to block in args

    def add_antibody(self, pattern: str):
        """Add a new antibody (regex pattern) to block specific arguments."""
        self.antibodies.append(pattern)
        logger.info(f"Immunity System: Generated antibody for pattern '{pattern}'")

    def monitor_tool_call(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """
        Check if a tool call is safe. Returns True if safe, False if blocked.
        """
        if tool_name in self.blocked_tools:
            logger.warning(f"Immunity System blocked blacklisted tool: {tool_name}")
            return False

        # Check antibodies (content filtering)
        import re
        import json
        try:
             args_str = json.dumps(args, sort_keys=True)
        except:
             args_str = str(args)

        for antibody in self.antibodies:
            if re.search(antibody, args_str):
                logger.warning(f"Immunity System: Antibody triggered for pattern '{antibody}'. Blocking call.")
                return False

        call_signature = f"{tool_name}:{args_str}"
        self.call_history.append(call_signature)

        # Check repetitive loop
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
            self.blocked_tools.append(tool_name)

    def record_success(self, tool_name: str):
        """Reset failure count on success."""
        self.failure_counts[tool_name] = 0

    def get_status(self) -> Dict[str, Any]:
        return {
            "blocked_tools": self.blocked_tools,
            "failure_counts": self.failure_counts
        }
