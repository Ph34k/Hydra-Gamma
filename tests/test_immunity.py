import pytest
import os
import json
from unittest.mock import patch, MagicMock
from app.agent.immunity import DigitalImmunitySystem

class TestDigitalImmunitySystem:
    @pytest.fixture
    def db_path(self, tmp_path):
        return str(tmp_path / "immunity_db.json")

    @pytest.fixture
    def immunity_system(self, db_path):
        return DigitalImmunitySystem(db_path=db_path)

    def test_initialization(self, immunity_system):
        assert immunity_system.blocked_tools == []
        assert immunity_system.antibodies == []
        assert immunity_system.failure_counts == {}

    def test_monitor_tool_call_safe(self, immunity_system):
        assert immunity_system.monitor_tool_call("some_tool", {"arg": "val"}) is True

    def test_monitor_tool_call_blocked(self, immunity_system):
        immunity_system.blocked_tools.append("dangerous_tool")
        assert immunity_system.monitor_tool_call("dangerous_tool", {}) is False

    def test_monitor_tool_call_antibody(self, immunity_system):
        # Add an antibody that blocks arguments containing "DROP TABLE"
        immunity_system.add_antibody("DROP TABLE")

        args = {"query": "SELECT * FROM users; DROP TABLE users;"}
        assert immunity_system.monitor_tool_call("sql_tool", args) is False

        safe_args = {"query": "SELECT * FROM users"}
        assert immunity_system.monitor_tool_call("sql_tool", safe_args) is True

    def test_repetitive_loop_detection(self, immunity_system):
        # Call the same tool with same args 4 times
        tool = "looping_tool"
        args = {"i": 1}

        assert immunity_system.monitor_tool_call(tool, args) is True # 1
        assert immunity_system.monitor_tool_call(tool, args) is True # 2
        assert immunity_system.monitor_tool_call(tool, args) is True # 3
        # 4th time should trigger loop detection
        assert immunity_system.monitor_tool_call(tool, args) is False

    def test_record_failure_and_blocking(self, immunity_system):
        tool = "flaky_tool"
        for _ in range(5):
            immunity_system.record_failure(tool)
            assert tool not in immunity_system.blocked_tools

        # 6th failure should block it
        immunity_system.record_failure(tool)
        assert tool in immunity_system.blocked_tools

    def test_learn_from_attack(self, immunity_system):
        tool = "vulnerable_tool"
        args = {"cmd": "rm -rf /"}

        immunity_system.learn_from_attack(tool, args, "dangerous command")

        # Check if antibody was created
        # The current implementation escapes the args string
        args_str = json.dumps(args, sort_keys=True)
        expected_antibody = import_re_escape(args_str)

        assert expected_antibody in immunity_system.antibodies

        # Verify it blocks subsequent calls
        assert immunity_system.monitor_tool_call(tool, args) is False

    def test_persistence(self, db_path):
        system1 = DigitalImmunitySystem(db_path=db_path)
        system1.add_antibody("test_pattern")
        system1.blocked_tools.append("test_tool")
        system1.save_immunity_db()

        system2 = DigitalImmunitySystem(db_path=db_path)
        assert "test_pattern" in system2.antibodies
        assert "test_tool" in system2.blocked_tools

def import_re_escape(s):
    import re
    return re.escape(s)
