import unittest
from app.utils.sanitizer import Sanitizer

class TestSanitizer(unittest.TestCase):
    def test_sanitize_keys(self):
        # API Keys
        text = "My key is sk-12345678901234567890"
        sanitized = Sanitizer.sanitize(text)
        self.assertIn("[OPENAI_KEY_REDACTED]", sanitized)
        self.assertNotIn("sk-12345", sanitized)

    def test_sanitize_email(self):
        # Email
        text = "Contact me at john.doe@example.com."
        sanitized = Sanitizer.sanitize(text)
        self.assertIn("[EMAIL_REDACTED]", sanitized)
        self.assertNotIn("john.doe@example.com", sanitized)

    def test_sanitize_cpf(self):
        # CPF
        text = "My CPF is 123.456.789-00."
        sanitized = Sanitizer.sanitize(text)
        self.assertIn("[CPF_REDACTED]", sanitized)
        self.assertNotIn("123.456.789-00", sanitized)

    def test_sanitize_dict(self):
        data = {
            "user": "Alice",
            "email": "alice@example.com",
            "key": "sk-12345678901234567890"
        }
        sanitized = Sanitizer.sanitize(data)
        self.assertIsInstance(sanitized, dict)
        self.assertIn("[EMAIL_REDACTED]", sanitized["email"])
        self.assertIn("[OPENAI_KEY_REDACTED]", sanitized["key"])

    def test_pseudonymize(self):
        # Hash check
        val = "user_123"
        hashed = Sanitizer.pseudonymize(val, salt="salty")
        self.assertNotEqual(val, hashed)
        self.assertEqual(len(hashed), 64) # SHA256 hex length
        # Deterministic
        self.assertEqual(hashed, Sanitizer.pseudonymize(val, salt="salty"))

if __name__ == "__main__":
    unittest.main()
