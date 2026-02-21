import unittest
from app.schema import Message, Role, ToolCall, Memory


class TestMessage(unittest.TestCase):
    def test_create_user_message(self):
        msg = Message.user_message("Hello")
        self.assertEqual(msg.role, Role.USER)
        self.assertEqual(msg.content, "Hello")
        self.assertIsNone(msg.base64_image)

    def test_create_system_message(self):
        msg = Message.system_message("System prompt")
        self.assertEqual(msg.role, Role.SYSTEM)
        self.assertEqual(msg.content, "System prompt")

    def test_create_assistant_message(self):
        msg = Message.assistant_message("Response")
        self.assertEqual(msg.role, Role.ASSISTANT)
        self.assertEqual(msg.content, "Response")

    def test_create_tool_message(self):
        msg = Message.tool_message("Result", "tool_name", "call_123")
        self.assertEqual(msg.role, Role.TOOL)
        self.assertEqual(msg.content, "Result")
        self.assertEqual(msg.name, "tool_name")
        self.assertEqual(msg.tool_call_id, "call_123")

    def test_message_addition(self):
        msg1 = Message.user_message("Hi")
        msg2 = Message.assistant_message("Hello")

        # Test Message + Message
        combined = msg1 + msg2
        self.assertEqual(len(combined), 2)
        self.assertEqual(combined[0], msg1)
        self.assertEqual(combined[1], msg2)

        # Test Message + List
        combined_list = msg1 + [msg2]
        self.assertEqual(len(combined_list), 2)
        self.assertEqual(combined_list[0], msg1)

        # Test List + Message (radd)
        radded = [msg1] + msg2
        self.assertEqual(len(radded), 2)
        self.assertEqual(radded[1], msg2)

    def test_to_dict(self):
        msg = Message.user_message("Hello", base64_image="base64string")
        d = msg.to_dict()
        self.assertEqual(d["role"], "user")
        self.assertEqual(d["content"], "Hello")
        self.assertEqual(d["base64_image"], "base64string")

    def test_from_tool_calls(self):
        # Mock a raw tool call object usually returned by LLM SDKs
        class MockFunction:
            def model_dump(self):
                return {"name": "func", "arguments": "{}"}

        class MockToolCall:
            id = "call_1"
            function = MockFunction()

        msg = Message.from_tool_calls([MockToolCall()])
        self.assertEqual(msg.role, Role.ASSISTANT)
        self.assertEqual(len(msg.tool_calls), 1)
        self.assertEqual(msg.tool_calls[0].id, "call_1")
        self.assertEqual(msg.tool_calls[0].function.name, "func")

    def test_invalid_addition(self):
        msg = Message.user_message("Hi")
        with self.assertRaises(TypeError):
            msg + 123


class TestMemory(unittest.TestCase):
    def setUp(self):
        self.memory = Memory(max_messages=3)

    def test_add_message(self):
        msg = Message.user_message("1")
        self.memory.add_message(msg)
        self.assertEqual(len(self.memory.messages), 1)
        self.assertEqual(self.memory.messages[0].content, "1")

    def test_max_messages_limit(self):
        self.memory.add_message(Message.user_message("1"))
        self.memory.add_message(Message.user_message("2"))
        self.memory.add_message(Message.user_message("3"))
        self.memory.add_message(Message.user_message("4"))

        self.assertEqual(len(self.memory.messages), 3)
        self.assertEqual(self.memory.messages[0].content, "2")
        self.assertEqual(self.memory.messages[-1].content, "4")

    def test_add_messages_list(self):
        msgs = [Message.user_message(str(i)) for i in range(4)]
        self.memory.add_messages(msgs)
        self.assertEqual(len(self.memory.messages), 3)
        self.assertEqual(self.memory.messages[0].content, "1")  # 0 is dropped

    def test_clear(self):
        self.memory.add_message(Message.user_message("1"))
        self.memory.clear()
        self.assertEqual(len(self.memory.messages), 0)

    def test_get_recent_messages(self):
        for i in range(3):
            self.memory.add_message(Message.user_message(str(i)))

        recent = self.memory.get_recent_messages(2)
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0].content, "1")
        self.assertEqual(recent[1].content, "2")

    def test_to_dict_list(self):
        self.memory.add_message(Message.user_message("Hi"))
        dicts = self.memory.to_dict_list()
        self.assertEqual(len(dicts), 1)
        self.assertEqual(dicts[0]["role"], "user")


if __name__ == '__main__':
    unittest.main()
