import os
import json
from abc import ABC, abstractmethod
from typing import Dict, Optional, Generator
from contextlib import contextmanager

class VaultAdapter(ABC):
    """
    Abstract Base Class for Vault Providers.
    """
    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        pass

class EnvVarVault(VaultAdapter):
    """
    Simple vault that reads from environment variables.
    """
    def get_secret(self, key: str) -> Optional[str]:
        return os.environ.get(key)

class FileVault(VaultAdapter):
    """
    Vault that reads from a JSON file.
    """
    def __init__(self, path: str):
        self.path = path
        self._cache: Dict[str, str] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self._cache = json.load(f)
            except Exception as e:
                # In real app, log error
                pass

    def get_secret(self, key: str) -> Optional[str]:
        return self._cache.get(key)

class SecretsManager:
    """
    Manages secure access to credentials.
    Chapter 34: Secrets Management
    """

    def __init__(self, vault_path: Optional[str] = None):
        # Chain of Responsibility: FileVault -> EnvVarVault
        self.vaults: list[VaultAdapter] = []

        path = vault_path or os.environ.get("SECRETS_VAULT_PATH", "secrets.json")
        self.vaults.append(FileVault(path))
        self.vaults.append(EnvVarVault())

    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieves a secret from the registered vaults in order.
        """
        for vault in self.vaults:
            secret = vault.get_secret(key)
            if secret:
                return secret
        return None

    @contextmanager
    def inject_env_vars(self, keys: list[str]) -> Generator[None, None, None]:
        """
        Context manager to temporarily inject secrets into os.environ.
        Ensures cleanup even if exceptions occur.
        """
        original_env = {}
        injected_keys = []

        try:
            for key in keys:
                secret = self.get_secret(key)
                if secret:
                    if key in os.environ:
                        original_env[key] = os.environ[key]
                    os.environ[key] = secret
                    injected_keys.append(key)
            yield
        finally:
            # Cleanup
            for key in injected_keys:
                if key in original_env:
                    os.environ[key] = original_env[key]
                else:
                    del os.environ[key]

    def inject_secret(self, key: str, target_env: Dict[str, str]) -> bool:
        """
        Injects a secret into a target environment dictionary (for subprocesses).
        Returns True if successful, False if secret not found.
        """
        secret = self.get_secret(key)
        if secret:
            target_env[key] = secret
            return True
        return False
