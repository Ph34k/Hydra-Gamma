from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class ErrorCategory(str, Enum):
    """Enumeration of error categories for self-healing."""
    SYNTAX = "syntax"
    TIMEOUT = "timeout"
    PERMISSION = "permission"
    NOT_FOUND = "not_found"
    LOGIC = "logic"
    UNKNOWN = "unknown"


class RecoveryStrategy(str, Enum):
    """Enumeration of recovery strategies."""
    RETRY = "retry"
    RETRY_WITH_DELAY = "retry_delay"
    MODIFY_ARGS = "modify_args"
    ASK_USER = "ask_user"
    SKIP = "skip"


class RecoveryPlan(BaseModel):
    """Structured plan for recovering from an error."""
    category: ErrorCategory
    strategy: RecoveryStrategy
    reasoning: str
    suggested_args: Optional[Dict[str, Any]] = None


class RecoveryManager:
    """
    Implements Structured Self-Healing (Chapter 7).
    Analyzes errors and prescribes specific recovery strategies.
    """

    def __init__(self):
        self.error_history: List[str] = []

    def analyze_error(
        self,
        error_msg: str,
        tool_name: str,
        args: Dict[str, Any]
    ) -> RecoveryPlan:
        """
        Categorize the error and determine the best recovery strategy.

        Args:
            error_msg: The error message string.
            tool_name: Name of the tool that failed.
            args: Arguments passed to the failed tool.

        Returns:
            RecoveryPlan: The recommended strategy.
        """
        self.error_history.append(f"{tool_name}: {error_msg}")

        category = self._categorize_error(error_msg)

        # Check for repetitive failures
        recent_errors = [e for e in self.error_history if tool_name in e]
        if len(recent_errors) > 2:
            return RecoveryPlan(
                category=category,
                strategy=RecoveryStrategy.ASK_USER,
                reasoning=(
                    f"Tool {tool_name} failed repeatedly "
                    f"({len(recent_errors)} times). Escalating to user."
                )
            )

        if category == ErrorCategory.SYNTAX:
            return RecoveryPlan(
                category=category,
                strategy=RecoveryStrategy.MODIFY_ARGS,
                reasoning="Syntax error detected. Check content and fix syntax."
            )

        elif category == ErrorCategory.TIMEOUT:
            return RecoveryPlan(
                category=category,
                strategy=RecoveryStrategy.RETRY_WITH_DELAY,
                reasoning="Operation timed out. Retrying with delay."
            )

        elif category == ErrorCategory.PERMISSION:
            return RecoveryPlan(
                category=category,
                strategy=RecoveryStrategy.ASK_USER,
                reasoning="Permission denied. Requires user intervention."
            )

        elif category == ErrorCategory.NOT_FOUND:
            if tool_name == "file_tool":
                return RecoveryPlan(
                    category=category,
                    strategy=RecoveryStrategy.MODIFY_ARGS,
                    reasoning="File not found. Check path or list directory."
                )

        # Default fallback
        return RecoveryPlan(
            category=category,
            strategy=RecoveryStrategy.RETRY,
            reasoning="Transient error suspected. Retrying."
        )

    def _categorize_error(self, error_msg: str) -> ErrorCategory:
        """Helper to map error strings to categories."""
        error_msg = error_msg.lower()
        if "syntax" in error_msg or "indentation" in error_msg:
            return ErrorCategory.SYNTAX
        if "timeout" in error_msg or "timed out" in error_msg:
            return ErrorCategory.TIMEOUT
        if "permission" in error_msg or "access denied" in error_msg:
            return ErrorCategory.PERMISSION
        if "not found" in error_msg or "no such file" in error_msg:
            return ErrorCategory.NOT_FOUND
        return ErrorCategory.UNKNOWN
