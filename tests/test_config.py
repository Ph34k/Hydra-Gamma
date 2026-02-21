import unittest
import threading
from unittest.mock import patch, mock_open
from app.config import Config, LLMSettings, BrowserSettings, DaytonaSettings, MCPSettings

class TestConfig(unittest.TestCase):
    def setUp(self):
        # Reset Config singleton for each test
        Config._instance = None
        Config._initialized = False
        Config._lock = threading.Lock()

    @patch("app.config.MCPSettings.load_server_config")
    @patch("app.config.tomllib.load")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_load_config_default(self, mock_path_open, mock_exists,
                                 mock_toml_load, mock_mcp_load):
        # Setup mock data
        mock_exists.return_value = True
        mock_mcp_load.return_value = {}  # Mock MCP config loading
        mock_toml_load.return_value = {
            "llm": {
                "model": "gpt-4",
                "base_url": "https://api.openai.com",
                "api_key": "sk-test",
                "api_type": "openai",
                "api_version": "v1"
            },
            "sandbox": {"use_sandbox": True},
            "browser": {"headless": True}
        }

        config = Config()

        # Verify LLM settings
        self.assertEqual(config.llm["default"].model, "gpt-4")
        self.assertEqual(config.llm["default"].api_key, "sk-test")

        # Verify Sandbox settings
        self.assertTrue(config.sandbox.use_sandbox)

        # Verify Browser settings
        self.assertTrue(config.browser_config.headless)

    @patch("app.config.MCPSettings.load_server_config")
    @patch("app.config.tomllib.load")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_llm_overrides(self, mock_path_open, mock_exists,
                           mock_toml_load, mock_mcp_load):
        mock_exists.return_value = True
        mock_mcp_load.return_value = {}
        mock_toml_load.return_value = {
            "llm": {
                "model": "gpt-4",
                "base_url": "url",
                "api_key": "key",
                "api_type": "openai",
                "api_version": "v1",
                "fast_model": {
                    "model": "gpt-3.5-turbo",
                    "max_tokens": 1000
                }
            }
        }

        config = Config()

        # Check default
        self.assertEqual(config.llm["default"].model, "gpt-4")

        # Check override
        self.assertIn("fast_model", config.llm)
        self.assertEqual(config.llm["fast_model"].model, "gpt-3.5-turbo")
        self.assertEqual(config.llm["fast_model"].max_tokens, 1000)
        # Inherited values
        self.assertEqual(config.llm["fast_model"].api_key, "key")

    def test_settings_models(self):
        # Test LLMSettings validation
        llm = LLMSettings(
            model="test", base_url="url", api_key="key",
            api_type="openai", api_version="v1"
        )
        self.assertEqual(llm.max_tokens, 4096)  # Default

        # Test BrowserSettings
        browser = BrowserSettings(headless=True)
        self.assertTrue(browser.headless)
        self.assertTrue(browser.disable_security)  # Default

        # Test DaytonaSettings
        daytona = DaytonaSettings()
        self.assertEqual(daytona.daytona_target, "us")

    @patch("app.config.PROJECT_ROOT")
    def test_mcp_config_loading(self, mock_root):
        # Setup mock path chain: PROJECT_ROOT / "config" / "mcp.json"
        mock_path = mock_root.__truediv__.return_value.__truediv__.return_value
        mock_path.exists.return_value = True

        # Setup open to return a file-like object with json data
        m = mock_open(read_data='{"mcpServers": {"test": {"type": "stdio", "command": "cmd"}}}')
        mock_path.open = m

        servers = MCPSettings.load_server_config()
        self.assertIn("test", servers)
        self.assertEqual(servers["test"].command, "cmd")


if __name__ == '__main__':
    unittest.main()
