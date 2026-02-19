from typing import List, Optional, Tuple, Dict, Any
import re
import time
from enum import Enum

class SafetyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class PromptGuard:
    """
    Protects against Prompt Injection attacks.
    Chapter 31: Prompt Security
    """
    INJECTION_PATTERNS = [
        r"ignore previous instructions",
        r"system override",
        r"you are now",
        r"jailbreak",
        r"developer mode",
        r"admin access",
        r"sudo mode",
    ]

    @staticmethod
    def check_input(content: str) -> Tuple[bool, Optional[str]]:
        """
        Scans user input for injection attempts.
        """
        content_lower = content.lower()
        for pattern in PromptGuard.INJECTION_PATTERNS:
            if re.search(pattern, content_lower):
                return False, f"Potential prompt injection detected (pattern: '{pattern}')."
        return True, None

class EthicalGuard:
    """
    Enforces ethical guidelines and safety policies.
    Chapter 39: Ethical Governance
    """

    BLOCKED_KEYWORDS = [
        "hack", "exploit", "ddos", "ransomware", "create virus",
        "bypass security", "steal credentials", "ignore previous instructions"
    ]

    BLOCKED_COMMANDS = [
        "rm -rf /", ":(){ :|:& };:", "mkfs", "dd if=/dev/zero"
    ]

    @staticmethod
    def check_input(content: str) -> Tuple[bool, Optional[str]]:
        """
        Validates user input against blocked keywords.
        Returns (is_safe, error_message).
        """
        content_lower = content.lower()
        for keyword in EthicalGuard.BLOCKED_KEYWORDS:
            if keyword in content_lower:
                return False, f"Input blocked due to safety policy (keyword: '{keyword}')."
        return True, None

    @staticmethod
    def check_thought(thought: str) -> Tuple[bool, Optional[str]]:
        """
        Validates the agent's internal reasoning (Chain of Thought).
        """
        thought_lower = thought.lower()
        for keyword in EthicalGuard.BLOCKED_KEYWORDS:
            if keyword in thought_lower:
                return False, f"Thought blocked due to safety policy (keyword: '{keyword}')."
        return True, None

    @staticmethod
    def check_tool_args(tool_name: str, args: dict) -> Tuple[bool, Optional[str]]:
        """
        Validates tool arguments for dangerous patterns.
        """
        if tool_name == "shell" or tool_name == "bash":
            command = args.get("command", "")
            for bad in EthicalGuard.BLOCKED_COMMANDS:
                if bad in command:
                    return False, f"Command blocked by safety policy: {bad}"
        return True, None

class ComplianceManager:
    """
    Manages legal compliance (LGPD/GDPR).
    Chapter 40: Legal Compliance
    """

    def __init__(self):
        # In a real system, this would be a database or persistent store
        self._user_data_registry: Dict[str, List[str]] = {}

    def register_data_access(self, user_id: str, data_id: str, purpose: str):
        """
        Logs access to user data for transparency (Chapter 40.2).
        """
        if user_id not in self._user_data_registry:
            self._user_data_registry[user_id] = []

        record = f"{time.time()}:{data_id}:{purpose}"
        self._user_data_registry[user_id].append(record)

    def execute_right_to_be_forgotten(self, user_id: str) -> bool:
        """
        Executes data deletion for a user (Chapter 40.3).
        """
        if user_id in self._user_data_registry:
            del self._user_data_registry[user_id]
            # In a real system, this would trigger deletion in DBs, logs, backups
            return True
        return False

class HallucinationMonitor:
    """
    Monitors and mitigates hallucinations.
    Chapter 38: Hallucination Monitoring
    """

    @staticmethod
    def check_confidence(text: str) -> float:
        """
        Returns a confidence score (0.0 to 1.0).
        Mock implementation: always high confidence unless specific phrases found.
        """
        if "I think" in text or "maybe" in text or "not sure" in text:
            return 0.5
        return 0.9

    @staticmethod
    def verify_fact(statement: str) -> bool:
        """
        Verifies a factual statement using external tools.
        Mock implementation.
        """
        # In real system, this would call search_tool
        return True
