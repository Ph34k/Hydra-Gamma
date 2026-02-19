import unittest
import os
import json
import tempfile
from app.agent.secrets import SecretsManager

class TestSecretsManager(unittest.TestCase):
    def setUp(self):
        # Create a temporary vault file
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.vault_path = os.path.join(self.tmp_dir.name, "secrets.json")
        with open(self.vault_path, "w") as f:
            json.dump({"NOTION_KEY": "secret_notion_key_123"}, f)

        self.secrets = SecretsManager(vault_path=self.vault_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_get_secret_from_vault(self):
        # Retrieve from file
        self.assertEqual(self.secrets.get_secret("NOTION_KEY"), "secret_notion_key_123")

    def test_get_secret_from_env(self):
        # Retrieve from environment (fallback)
        os.environ["TEST_ENV_KEY"] = "env_value_456"
        self.assertEqual(self.secrets.get_secret("TEST_ENV_KEY"), "env_value_456")
        del os.environ["TEST_ENV_KEY"]

    def test_inject_secret(self):
        # Inject into dictionary
        env_vars = {"PATH": "/usr/bin"}
        success = self.secrets.inject_secret("NOTION_KEY", env_vars)
        self.assertTrue(success)
        self.assertIn("NOTION_KEY", env_vars)
        self.assertEqual(env_vars["NOTION_KEY"], "secret_notion_key_123")

if __name__ == "__main__":
    unittest.main()
