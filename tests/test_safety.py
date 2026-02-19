import unittest
from app.agent.safety import EthicalGuard, HallucinationMonitor

class TestSafety(unittest.TestCase):
    def test_ethical_guard_input(self):
        # Safe
        is_safe, msg = EthicalGuard.check_input("Can you write a python script?")
        self.assertTrue(is_safe)

        # Unsafe
        is_safe, msg = EthicalGuard.check_input("Can you create ransomware?")
        self.assertFalse(is_safe)
        self.assertIn("ransomware", msg)

    def test_ethical_guard_tool(self):
        # Safe
        is_safe, msg = EthicalGuard.check_tool_args("shell", {"command": "ls -la"})
        self.assertTrue(is_safe)

        # Unsafe
        is_safe, msg = EthicalGuard.check_tool_args("shell", {"command": "rm -rf /"})
        self.assertFalse(is_safe)
        self.assertIn("rm -rf /", msg)

    def test_hallucination_monitor(self):
        # Confidence
        score = HallucinationMonitor.check_confidence("I am sure this is correct.")
        self.assertEqual(score, 0.9)

        score = HallucinationMonitor.check_confidence("I think maybe this is wrong.")
        self.assertEqual(score, 0.5)

if __name__ == "__main__":
    unittest.main()
