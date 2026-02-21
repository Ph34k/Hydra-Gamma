import unittest
from unittest.mock import patch
from app.logger import define_log_level


class TestLogger(unittest.TestCase):
    @patch("app.logger._logger")
    @patch("app.logger.PROJECT_ROOT")
    def test_define_log_level(self, mock_root, mock_logger):
        # Setup mock root
        mock_root.__truediv__.return_value = "mock_path"

        # Call function
        logger = define_log_level(
            print_level="DEBUG", logfile_level="INFO", name="test"
        )

        # Verify logger config
        mock_logger.remove.assert_called()
        self.assertEqual(mock_logger.add.call_count, 2)

        # Verify stderr handler
        args, kwargs = mock_logger.add.call_args_list[0]
        self.assertEqual(kwargs["level"], "DEBUG")

        # Verify file handler
        args, kwargs = mock_logger.add.call_args_list[1]
        self.assertEqual(kwargs["level"], "INFO")

        # Verify return value
        self.assertEqual(logger, mock_logger)


if __name__ == '__main__':
    unittest.main()
