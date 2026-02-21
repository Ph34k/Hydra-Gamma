import unittest
from unittest.mock import MagicMock, patch
from app.llm import LLM, TokenCounter
from app.config import LLMSettings
from app.schema import Message
from app.exceptions import TokenLimitExceeded


class TestTokenCounter(unittest.TestCase):
    def setUp(self):
        # Mock tokenizer to return simple length-based token counts
        self.tokenizer = MagicMock()
        self.tokenizer.encode = lambda x: [1] * len(x) if x else []
        self.counter = TokenCounter(self.tokenizer)

    def test_count_text(self):
        self.assertEqual(self.counter.count_text("hello"), 5)
        self.assertEqual(self.counter.count_text(""), 0)

    def test_count_image_low_detail(self):
        img = {"detail": "low"}
        self.assertEqual(self.counter.count_image(img), 85)

    def test_count_image_high_detail(self):
        # 1024x1024 high detail
        # Short side = 768. 768/1024 scale -> 768x768
        # Tiles: ceil(768/512) * ceil(768/512) = 2 * 2 = 4 tiles
        # Tokens: 4 * 170 + 85 = 680 + 85 = 765
        img = {"detail": "high", "dimensions": (1024, 1024)}
        self.assertEqual(self.counter.count_image(img), 765)

    def test_count_message_tokens(self):
        msgs = [
            Message.system_message("sys"),
            Message.user_message("hi")
        ]
        # Base format tokens = 2
        # Msg 1: Base(4) + Role("system"=6) + Content("sys"=3) = 13
        # Msg 2: Base(4) + Role("user"=4) + Content("hi"=2) = 10
        # Total = 2 + 13 + 10 = 25
        self.assertEqual(self.counter.count_message_tokens(
            [m.to_dict() for m in msgs]
        ), 25)


class TestLLM(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Reset LLM singleton
        LLM._instances = {}

        self.single_settings = LLMSettings(
            model="gpt-4",
            base_url="url",
            api_key="key",
            api_type="openai",
            api_version="v1",
            max_input_tokens=100
        )

        self.llm_config = {"default": self.single_settings}

    @patch("app.llm.AsyncOpenAI")
    @patch("app.llm.tiktoken.encoding_for_model")
    def test_initialization(self, mock_tiktoken, mock_openai):
        llm = LLM(llm_config=self.llm_config)
        self.assertEqual(llm.model, "gpt-4")
        self.assertIsNotNone(llm.client)

    @patch("app.llm.AsyncOpenAI")
    @patch("app.llm.tiktoken.encoding_for_model")
    async def test_ask_token_limit_exceeded(self, mock_tiktoken, mock_openai):
        llm = LLM(llm_config=self.llm_config)
        # However, count_message_tokens delegates to self.token_counter
        # It's easier to mock the token_counter on the instance
        llm.token_counter.count_message_tokens = MagicMock(return_value=150)

        # tenacity retry wraps the exception in RetryError
        from tenacity import RetryError
        try:
            await llm.ask([Message.user_message("hi")])
        except RetryError as e:
            self.assertIsInstance(e.last_attempt.exception(),
                                  TokenLimitExceeded)
        except TokenLimitExceeded:
            # If it wasn't retried, this is also fine
            pass
        else:
            self.fail("TokenLimitExceeded not raised")

    @patch("app.llm.AsyncOpenAI")
    @patch("app.llm.tiktoken.encoding_for_model")
    def test_format_messages(self, mock_tiktoken, mock_openai):
        llm = LLM(llm_config=self.llm_config)

        # Test basic formatting
        msgs = [Message.user_message("hi")]
        formatted = llm.format_messages(msgs)
        self.assertEqual(formatted[0]["role"], "user")
        self.assertEqual(formatted[0]["content"], "hi")

        msg_with_img = Message.user_message("look", base64_image="xyz")

        # Case 1: No support -> strips image
        formatted = llm.format_messages([msg_with_img], supports_images=False)
        self.assertNotIn("base64_image", formatted[0])
        self.assertEqual(formatted[0]["content"], "look")

        # Case 2: Support -> converts to content list
        formatted = llm.format_messages([msg_with_img], supports_images=True)
        self.assertIsInstance(formatted[0]["content"], list)
        self.assertEqual(formatted[0]["content"][0]["text"], "look")
        self.assertEqual(formatted[0]["content"][1]["type"], "image_url")


if __name__ == '__main__':
    unittest.main()
