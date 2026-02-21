from typing import Any, Dict
from app.utils.sanitizer import Sanitizer as CoreSanitizer

class Sanitizer:
    """
    Simulates PII sanitization for Edge devices.
    (Chapter 51.4: Anonimização e Pseudonimização no Edge)
    """

    @staticmethod
    def sanitize(data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive keys or redact values."""
        # Use CoreSanitizer for regex-based redaction
        sanitized = CoreSanitizer.sanitize(data)

        # Additional recursive key-based redaction for Edge specific needs
        if isinstance(sanitized, dict):
            sensitive_keys = ["password", "token", "key"] # Removed 'email' as CoreSanitizer handles it
            for k in list(sanitized.keys()):
                if any(s in k.lower() for s in sensitive_keys):
                    sanitized[k] = "[REDACTED]"
                elif isinstance(sanitized[k], dict):
                    sanitized[k] = Sanitizer.sanitize(sanitized[k])

        return sanitized
