import unittest
from app.agent.rbac import RBACManager, User, UserRole, Permission

class TestRBAC(unittest.TestCase):
    def setUp(self):
        self.rbac = RBACManager()
        self.free_user = User(id="u1", role=UserRole.FREE)
        self.pro_user = User(id="u2", role=UserRole.PRO)
        self.ent_user = User(id="u3", role=UserRole.ENTERPRISE)

    def test_free_user_shell(self):
        # Allowed
        self.assertTrue(self.rbac.check_permission(
            self.free_user, "shell", "exec", {"command": "ls -la"}
        ))
        # Denied (advanced)
        self.assertFalse(self.rbac.check_permission(
            self.free_user, "shell", "exec", {"command": "curl http://google.com"}
        ))

    def test_pro_user_shell(self):
        # Allowed
        self.assertTrue(self.rbac.check_permission(
            self.pro_user, "shell", "exec", {"command": "curl http://google.com"}
        ))

    def test_file_access(self):
        # Free: Read only
        self.assertTrue(self.rbac.check_permission(
            self.free_user, "file_tool", "read", {"path": "test.txt"}
        ))
        self.assertFalse(self.rbac.check_permission(
            self.free_user, "file_tool", "write", {"path": "test.txt", "content": "hi"}
        ))

        # Pro: Write allowed (assuming permission list includes it, let's check my implementation)
        # My implementation for PRO has `Permission(resource="file_tool", action="write")`
        self.assertTrue(self.rbac.check_permission(
            self.pro_user, "file_tool", "write", {"path": "test.txt"}
        ))

    def test_enterprise_features(self):
        # MCP Call - only Enterprise
        self.assertFalse(self.rbac.check_permission(
            self.pro_user, "mcp_tool", "call", {}
        ))
        self.assertTrue(self.rbac.check_permission(
            self.ent_user, "mcp_tool", "call", {}
        ))

if __name__ == '__main__':
    unittest.main()
