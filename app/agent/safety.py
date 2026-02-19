from typing import List, Optional, Tuple
import re

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
