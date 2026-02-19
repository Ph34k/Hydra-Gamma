import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock problematic modules
sys.modules["browser_use"] = MagicMock()
sys.modules["browser_use.browser"] = MagicMock()
sys.modules["browser_use.browser.context"] = MagicMock()
sys.modules["browser_use.dom.service"] = MagicMock()
sys.modules["baidusearch"] = MagicMock()
sys.modules["baidusearch.baidusearch"] = MagicMock()
sys.modules["googlesearch"] = MagicMock()
sys.modules["duckduckgo_search"] = MagicMock()
sys.modules["pdfminer"] = MagicMock()
sys.modules["pdfminer.high_level"] = MagicMock()
sys.modules["html2text"] = MagicMock()
sys.modules["daytona"] = MagicMock()

import unittest
import os
from app.agent.rbac import RBACManager, User, UserRole, Action, Resource
from app.agent.secrets import SecretsManager, EnvVarVault, FileVault

class TestRBACSecrets(unittest.TestCase):
    def test_rbac_granular(self):
        rbac = RBACManager()

        # Test FREE user
        user_free = User(id="u1", role=UserRole.FREE)
        # Should be able to read file
        self.assertTrue(rbac.check_permission(user_free, Resource.FILE, Action.READ))
        # Should NOT be able to write file
        self.assertFalse(rbac.check_permission(user_free, Resource.FILE, Action.WRITE))

        # Test PRO user
        user_pro = User(id="u2", role=UserRole.PRO)
        # Should be able to write file
        self.assertTrue(rbac.check_permission(user_pro, Resource.FILE, Action.WRITE))

        # Test Action Enum usage
        self.assertTrue(rbac.check_permission(user_free, "file_tool", "read"))
        self.assertFalse(rbac.check_permission(user_free, "file_tool", "write"))

    def test_secrets_manager(self):
        # Mock env vars
        with patch.dict(os.environ, {"TEST_KEY": "secret_value"}):
            sm = SecretsManager(vault_path="nonexistent.json")

            # Test EnvVarVault
            self.assertEqual(sm.get_secret("TEST_KEY"), "secret_value")
            self.assertIsNone(sm.get_secret("NON_EXISTENT"))

    def test_inject_env_vars(self):
        with patch.dict(os.environ, {"TEST_KEY": "secret_value"}):
            sm = SecretsManager(vault_path="nonexistent.json")

            # Initially NOT in env (mocked above)
            # Wait, patch.dict puts it in os.environ.
            # I want to test injecting a NEW key from "Vault" (which is EnvVarVault here, so it's already there)
            # Let's mock a FileVault with a secret not in env

            sm.vaults = [] # Clear default vaults

            # Create a mock vault
            mock_vault = MagicMock()
            mock_vault.get_secret.side_effect = lambda k: "injected_secret" if k == "NEW_SECRET" else None
            sm.vaults.append(mock_vault)

            # Verify not in env
            self.assertNotIn("NEW_SECRET", os.environ)

            # Inject
            with sm.inject_env_vars(["NEW_SECRET"]):
                self.assertIn("NEW_SECRET", os.environ)
                self.assertEqual(os.environ["NEW_SECRET"], "injected_secret")

            # Verify cleanup
            self.assertNotIn("NEW_SECRET", os.environ)

if __name__ == "__main__":
    unittest.main()
