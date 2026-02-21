import re
import hashlib
from typing import Dict, Any, List

class Sanitizer:
    """
    Handles PII redaction and data sanitization.
    Ref: Chapter 33 of the Technical Bible.
    """

    # Regex patterns for common PII
    PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"(\+\d{1,3}[-.]?)?\(?\d{3}\)?[-.]?\d{3}[-.]?\d{4}",
        "cpf": r"\d{3}\.\d{3}\.\d{3}-\d{2}", # Brazilian ID format example
        "credit_card": r"\b(?:\d{4}[- ]?){3}\d{4}\b",
        "api_key": r"(sk-[a-zA-Z0-9]{32,})|(ghp_[a-zA-Z0-9]{36})", # OpenAI, GitHub
    }

    def sanitize_text(self, text: str) -> str:
        """Redact PII from text."""
        if not text:
            return ""

        sanitized = text
        for label, pattern in self.PATTERNS.items():
            sanitized = re.sub(pattern, f"[REDACTED_{label.upper()}]", sanitized)

        return sanitized

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary values."""
        new_data = {}
        for k, v in data.items():
            if isinstance(v, str):
                new_data[k] = self.sanitize_text(v)
            elif isinstance(v, dict):
                new_data[k] = self.sanitize_dict(v)
            elif isinstance(v, list):
                new_data[k] = [self.sanitize_text(i) if isinstance(i, str) else i for i in v]
            else:
                new_data[k] = v
        return new_data

    @staticmethod
    def sanitize(data: Any) -> Any:
        """Static wrapper for convenience/compatibility."""
        s = Sanitizer()
        if isinstance(data, dict):
            return s.sanitize_dict(data)
        elif isinstance(data, str):
            return s.sanitize_text(data)
        return data

    @staticmethod
    def pseudonymize(text: str) -> str:
        """Pseudonymize text using SHA256 hash."""
        return hashlib.sha256(text.encode()).hexdigest()

    def forget_user_data(self, user_id: str):
        """
        Implement 'Right to Forget'.
        This would typically interface with databases to delete user records.
        For now, it's a placeholder interface.
        """
        # TODO: Connect to episodic/semantic memory and delete records tagged with user_id
        # Example: self.episodic_store.delete_by_user(user_id)
        pass

# Global instance
sanitizer = Sanitizer()
