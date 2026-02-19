import re
import hashlib
from typing import Any, Dict, List, Union, Optional

class Sanitizer:
    """
    Sanitizes sensitive information (API keys, passwords, PII) from logs and memory.
    Chapter 10.6: Privacy and Expiration.
    Chapter 33: Data Privacy (Anonymization & Pseudonymization).
    """

    PATTERNS = [
        (r"sk-[a-zA-Z0-9]{20,}", "[OPENAI_KEY_REDACTED]"),
        (r"ghp_[a-zA-Z0-9]{20,}", "[GITHUB_KEY_REDACTED]"),
        (r"xox[baprs]-[a-zA-Z0-9]{10,}", "[SLACK_KEY_REDACTED]"),
        (r"(password|secret|token)\s*=\s*['\"]?([a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};':\\|,.<>/?]+)['\"]?", r"\1=[REDACTED]"),
        (r"Bearer [a-zA-Z0-9\-\._~\+\/]+", "Bearer [REDACTED]"),
        # PII Patterns (Chapter 33)
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"), # Email
        (r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", "[CPF_REDACTED]"), # CPF (Brazil)
        (r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b", "[CNPJ_REDACTED]"), # CNPJ (Brazil)
    ]

    @staticmethod
    def sanitize(data: Union[str, Dict, List]) -> Union[str, Dict, List]:
        """
        Removes sensitive information using regex patterns (Anonymization).
        """
        if isinstance(data, str):
            for pattern, replacement in Sanitizer.PATTERNS:
                data = re.sub(pattern, replacement, data, flags=re.IGNORECASE)
            return data
        elif isinstance(data, dict):
            return {k: Sanitizer.sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Sanitizer.sanitize(item) for item in data]
        return data

    @staticmethod
    def pseudonymize(data: str, salt: Optional[str] = "") -> str:
        """
        Replaces a value with a deterministic hash (Pseudonymization).
        Useful for tracking entities without revealing their identity.
        """
        return hashlib.sha256((data + (salt or "")).encode()).hexdigest()
