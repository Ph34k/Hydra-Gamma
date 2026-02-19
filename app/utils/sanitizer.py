import re
from typing import Any, Dict, List, Union

class Sanitizer:
    """
    Sanitizes sensitive information (API keys, passwords) from logs and memory.
    Chapter 10.6: Privacy and Expiration.
    """

    PATTERNS = [
        (r"sk-[a-zA-Z0-9]{20,}", "[OPENAI_KEY_REDACTED]"),
        (r"ghp_[a-zA-Z0-9]{20,}", "[GITHUB_KEY_REDACTED]"),
        (r"xox[baprs]-[a-zA-Z0-9]{10,}", "[SLACK_KEY_REDACTED]"),
        (r"(password|secret|token)\s*=\s*['\"]?([a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};':\\|,.<>/?]+)['\"]?", r"\1=[REDACTED]"),
        (r"Bearer [a-zA-Z0-9\-\._~\+\/]+", "Bearer [REDACTED]"),
    ]

    @staticmethod
    def sanitize(data: Union[str, Dict, List]) -> Union[str, Dict, List]:
        if isinstance(data, str):
            for pattern, replacement in Sanitizer.PATTERNS:
                data = re.sub(pattern, replacement, data, flags=re.IGNORECASE)
            return data
        elif isinstance(data, dict):
            return {k: Sanitizer.sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [Sanitizer.sanitize(item) for item in data]
        return data
