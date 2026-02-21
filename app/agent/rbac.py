from enum import Enum
from typing import List, Dict, Optional, Set, Any
from pydantic import BaseModel, Field

class UserRole(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class Action(str, Enum):
    EXEC = "exec"
    READ = "read"
    WRITE = "write"
    NAVIGATE = "navigate"
    INIT = "init"
    PORT = "port"
    CALL = "call"
    CRON = "cron"
    ANY = "*"

class Resource(str, Enum):
    SHELL = "shell"
    BASH = "bash"
    FILE = "file_tool"
    SEARCH = "search_tool"
    BROWSER = "browser_tool"
    WEBDEV = "web_dev_tool"
    EXPOSE = "expose"
    MCP = "mcp_tool"
    SCHEDULE = "schedule_tool"
    GIT = "git_tool"
    CRM = "crm_tool"
    DELEGATE = "delegate_task"
    PYTHON = "python_execute"
    MEMORY = "memory_search"
    MEDIA = "media_generation_tool"
    PLANNING = "planning"

class Permission(BaseModel):
    resource: str  # tool_name
    action: str    # exec, read, write
    # Optional: specific constraints like allowed_commands for shell

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
                Permission(resource=Resource.SHELL, action=Action.EXEC),
                Permission(resource=Resource.BASH, action=Action.EXEC), # Alias
                Permission(resource=Resource.FILE, action=Action.READ),
                Permission(resource=Resource.SEARCH, action=Action.EXEC),
                Permission(resource=Resource.PLANNING, action=Action.EXEC), # Allow planning for all
            ],
            UserRole.PRO: [
                Permission(resource=Resource.SHELL, action=Action.EXEC),
                Permission(resource=Resource.BASH, action=Action.EXEC),
                Permission(resource=Resource.FILE, action=Action.READ),
                Permission(resource=Resource.FILE, action=Action.WRITE),
                Permission(resource=Resource.BROWSER, action=Action.NAVIGATE),
                Permission(resource=Resource.WEBDEV, action=Action.INIT),
                Permission(resource=Resource.EXPOSE, action=Action.PORT),
                Permission(resource=Resource.SEARCH, action=Action.EXEC),
                Permission(resource=Resource.PLANNING, action=Action.EXEC),
            ],
            UserRole.ENTERPRISE: [
                Permission(resource=Resource.SHELL, action=Action.EXEC),
                Permission(resource=Resource.BASH, action=Action.EXEC),
                Permission(resource=Resource.FILE, action=Action.READ),
                Permission(resource=Resource.FILE, action=Action.WRITE),
                Permission(resource=Resource.BROWSER, action=Action.NAVIGATE),
                Permission(resource=Resource.WEBDEV, action=Action.INIT),
                Permission(resource=Resource.EXPOSE, action=Action.PORT),
                Permission(resource=Resource.SEARCH, action=Action.EXEC),
                Permission(resource=Resource.MCP, action=Action.CALL),
                Permission(resource=Resource.SCHEDULE, action=Action.CRON),
                Permission(resource=Resource.GIT, action=Action.EXEC),
                Permission(resource=Resource.CRM, action=Action.EXEC),
                Permission(resource=Resource.DELEGATE, action=Action.EXEC),
                Permission(resource=Resource.PYTHON, action=Action.EXEC),
                Permission(resource=Resource.MEMORY, action=Action.READ),
                Permission(resource=Resource.MEDIA, action=Action.EXEC),
                Permission(resource=Resource.PLANNING, action=Action.EXEC),
            ]
        }

    def check_permission(self, user: User, resource: str, action: str, tool_args: Optional[Dict] = None) -> bool:
        """
        Verifies if the user has permission to perform the action on the resource.
        """
        user_permissions = self._role_definitions.get(user.role, [])

        # Check if basic permission exists
        has_base_perm = any(
            p.resource == resource and (p.action == action or p.action == Action.ANY)
            for p in user_permissions
        )

        if not has_base_perm:
            return False

        # Granular checks based on Role and Resource
        if (resource == Resource.SHELL or resource == Resource.BASH) and action == Action.EXEC:
            return self._check_shell_permission(user.role, tool_args)

        if resource == Resource.FILE:
             return self._check_file_permission(user.role, action, tool_args)

        return True

    def _check_shell_permission(self, role: UserRole, args: Optional[Dict]) -> bool:
        if not args or "command" not in args:
            return False # Invalid args, deny

        command = args["command"].strip().split()[0] # Get the binary name

        if role == UserRole.FREE:
            return command in self.BASIC_SHELL_COMMANDS

        if role == UserRole.PRO:
            # Pro users can run almost anything, but we might want to restrict dangerous ones
            # (though EthicalGuard handles dangerous ones globally)
            return True

        if role == UserRole.ENTERPRISE:
            return True

        return False

    def _check_file_permission(self, role: UserRole, action: str, args: Optional[Dict]) -> bool:
        if role == UserRole.FREE:
            if action == Action.WRITE:
                return False
            if action == Action.READ:
                # Can enforce reading only specific directories if args provided
                return True

        return True
