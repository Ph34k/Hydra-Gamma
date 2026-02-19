import os
import json
from typing import Dict, Optional
from pydantic import BaseModel

class SecretsManager:
    """
    Manages secure access to credentials.
    Chapter 34: Secrets Management
    """

    def __init__(self, vault_path: Optional[str] = None):
        self.vault_path = vault_path or os.environ.get("SECRETS_VAULT_PATH", "secrets.json")
        self._cache: Dict[str, str] = {}
        self._load_vault()

    def _load_vault(self):
        """Loads secrets from the simulated vault file."""
        if os.path.exists(self.vault_path):
            try:
                with open(self.vault_path, 'r') as f:
                    self._cache = json.load(f)
            except Exception as e:
                # Log error in real app
                print(f"Error loading vault: {e}")
        else:
            # Fallback to environment variables for certain known keys if not in file
            # This is useful for testing or simple setups
            pass

    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieves a secret from the vault.
        Prioritizes the vault file, then environment variables.
        """
        if key in self._cache:
            return self._cache[key]

        # Fallback to process environment (useful for development)
        return os.environ.get(key)

    def inject_secret(self, key: str, target_env: Dict[str, str]) -> bool:
        """
        Injects a secret into a target environment dictionary.
        Returns True if successful, False if secret not found.
        """
        secret = self.get_secret(key)
        if secret:
            target_env[key] = secret
            return True
        return False
