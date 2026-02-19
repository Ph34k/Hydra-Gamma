from enum import Enum
from typing import List, Dict, Optional, Set
from pydantic import BaseModel, Field

class UserRole(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class Permission(BaseModel):
    resource: str  # tool_name
    action: str    # exec, read, write
    # Optional: specific constraints like allowed_commands for shell

class RoleConfig(BaseModel):
    name: UserRole
    permissions: List[Permission]

class User(BaseModel):
    id: str
    role: UserRole

class RBACManager:
    """
    Manages Role-Based Access Control for the agent tools.
    Chapter 32: Role-Based Access Control
    """

    # Basic commands allowed for Free tier
    BASIC_SHELL_COMMANDS = {
        "ls", "cd", "pwd", "cat", "echo", "mkdir", "touch", "whoami", "date"
    }

    def __init__(self):
        self._role_definitions: Dict[UserRole, List[Permission]] = self._load_roles()

    def _load_roles(self) -> Dict[UserRole, List[Permission]]:
        """
        Defines the permissions for each role as per Chapter 32.3.
        """
        # Note: We use "shell" as the resource name, but "bash" tool maps to it.
        return {
            UserRole.FREE: [
                Permission(resource="shell", action="exec"),
                Permission(resource="bash", action="exec"), # Alias
                Permission(resource="file_tool", action="read"),
                Permission(resource="search_tool", action="exec"), # Changed from info to exec to match ToolCallAgent default
            ],
            UserRole.PRO: [
                Permission(resource="shell", action="exec"),
                Permission(resource="bash", action="exec"),
                Permission(resource="file_tool", action="read"),
                Permission(resource="file_tool", action="write"),
                Permission(resource="browser_tool", action="navigate"),
                Permission(resource="web_dev_tool", action="init"),
                Permission(resource="expose", action="port"),
                Permission(resource="search_tool", action="exec"),
            ],
            UserRole.ENTERPRISE: [
                Permission(resource="shell", action="exec"),
                Permission(resource="bash", action="exec"),
                Permission(resource="file_tool", action="read"),
                Permission(resource="file_tool", action="write"),
                Permission(resource="browser_tool", action="navigate"),
                Permission(resource="web_dev_tool", action="init"),
                Permission(resource="expose", action="port"),
                Permission(resource="search_tool", action="exec"),
                Permission(resource="mcp_tool", action="call"),
                Permission(resource="schedule_tool", action="cron"),
            ]
        }

    def check_permission(self, user: User, resource: str, action: str, tool_args: Optional[Dict] = None) -> bool:
        """
        Verifies if the user has permission to perform the action on the resource.
        """
        user_permissions = self._role_definitions.get(user.role, [])

        # Check if basic permission exists
        has_base_perm = any(
            p.resource == resource and (p.action == action or p.action == "*")
            for p in user_permissions
        )

        if not has_base_perm:
            return False

        # Granular checks based on Role and Resource
        if (resource == "shell" or resource == "bash") and action == "exec":
            return self._check_shell_permission(user.role, tool_args)

        if resource == "file_tool":
             return self._check_file_permission(user.role, action, tool_args)

        return True

    def _check_shell_permission(self, role: UserRole, args: Optional[Dict]) -> bool:
        if not args or "command" not in args:
            return False # Invalid args, deny

        command = args["command"].strip().split()[0] # Get the binary name

        if role == UserRole.FREE:
            return command in self.BASIC_SHELL_COMMANDS

        if role == UserRole.PRO:
            return True

        if role == UserRole.ENTERPRISE:
            return True

        return False

    def _check_file_permission(self, role: UserRole, action: str, args: Optional[Dict]) -> bool:
        if role == UserRole.FREE:
            if action == "write":
                return False
            if action == "read":
                return True

        return True
