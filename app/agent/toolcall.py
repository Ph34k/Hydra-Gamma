import asyncio
import json
import re
import time
import os
from typing import Any, List, Optional, Union, Dict

from pydantic import Field, PrivateAttr

from app.agent.react import ReActAgent
from app.exceptions import TokenLimitExceeded
from app.logger import logger
from app.prompt.toolcall import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.schema import TOOL_CHOICE_TYPE, AgentState, Message, ToolCall, ToolChoice
from app.tool import CreateChatCompletion, Terminate, ToolCollection

# Security Modules
from app.agent.rbac import RBACManager, User, UserRole, Action
from app.agent.secrets import SecretsManager
from app.agent.safety import EthicalGuard, PromptGuard, ComplianceManager, HallucinationMonitor
from app.agent.immunity import DigitalImmunitySystem
from app.agent.rlhf import FeedbackCollector
from app.utils.audit import AuditLogger
from app.utils.sanitizer import Sanitizer


TOOL_CALL_REQUIRED = "Tool calls required but none provided"

# Chapter 34: Secrets Mapping
TOOL_REQUIRED_SECRETS = {
    "notion_tool": ["NOTION_API_KEY"],
    "search_tool": ["SEARCH_API_KEY", "GOOGLE_API_KEY", "BING_API_KEY"],
    "mcp_tool": ["MCP_API_KEY"],
    # Add more mappings as needed
}

class ToolCallAgent(ReActAgent):
    """Base agent class for handling tool/function calls with enhanced abstraction"""

    name: str = "toolcall"
    description: str = "an agent that can execute tool calls."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection(
        CreateChatCompletion(), Terminate()
    )
    tool_choices: TOOL_CHOICE_TYPE = ToolChoice.AUTO  # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = None

    max_steps: int = 30
    max_observe: Optional[Union[int, bool]] = None

    # Security Components (Private Attributes)
    _rbac: RBACManager = PrivateAttr()
    _secrets: SecretsManager = PrivateAttr()
    _audit: AuditLogger = PrivateAttr()
    _compliance: ComplianceManager = PrivateAttr()
    _immunity: DigitalImmunitySystem = PrivateAttr()
    _feedback: FeedbackCollector = PrivateAttr()
    _user: User = PrivateAttr()
    _secrets_lock: asyncio.Lock = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize Security Components
        self._rbac = RBACManager()
        self._secrets = SecretsManager()
        self._audit = AuditLogger()
        self._compliance = ComplianceManager()
        self._immunity = DigitalImmunitySystem()
        self._feedback = FeedbackCollector()
        self._secrets_lock = asyncio.Lock()
        # Default user context (In a real app, this would be passed in)
        self._user = User(id="default_user", role=UserRole.ENTERPRISE)

    async def think(self) -> bool:
        """Process current state and decide next actions using tools"""
        if self.next_step_prompt:
            user_msg = Message.user_message(self.next_step_prompt)
            self.messages += [user_msg]

        try:
            # Get response with tool options
            response = await self.llm.ask_tool(
                messages=self.messages,
                system_msgs=(
                    [Message.system_message(self.system_prompt)]
                    if self.system_prompt
                    else None
                ),
                tools=self.available_tools.to_params(),
                tool_choice=self.tool_choices,
            )
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False
            raise

        self.tool_calls = tool_calls = (
            response.tool_calls if response and response.tool_calls else []
        )
        content = response.content if response and response.content else ""

        # Ethical Guard (Thought)
        if content:
            is_safe, error_msg = EthicalGuard.check_thought(content)
            if not is_safe:
                logger.warning(f"🚫 Thought blocked by EthicalGuard: {error_msg}")
                content = f"⚠️ My previous thought was blocked due to safety policy: {error_msg}. I must re-evaluate."
                self.memory.add_message(Message.assistant_message(content))
                return False

            # Hallucination Monitor (Confidence Check)
            confidence = HallucinationMonitor.check_confidence(content)
            if confidence < 0.7:
                logger.warning(f"🤔 Low confidence thought detected ({confidence:.2f}): {content}")
                # Ideally, we should trigger a search or verification step here
                # For now, we log it and proceed, but add a self-correction prompt to memory
                # content += f"\n(Self-Correction: I am not fully confident in this. I should verify facts before acting.)"
                # For simplicity in this iteration, we just log.

        # Log response info
        logger.info(f"✨ {self.name}'s thoughts: {content}")
        logger.info(
            f"🛠️ {self.name} selected {len(tool_calls) if tool_calls else 0} tools to use"
        )
        if tool_calls:
            logger.info(
                f"🧰 Tools being prepared: {[call.function.name for call in tool_calls]}"
            )
            logger.info(f"🔧 Tool arguments: {tool_calls[0].function.arguments}")

        try:
            if response is None:
                raise RuntimeError("No response received from the LLM")

            # Handle different tool_choices modes
            if self.tool_choices == ToolChoice.NONE:
                if tool_calls:
                    logger.warning(
                        f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                    )
                if content:
                    self.memory.add_message(Message.assistant_message(content))
                    return True
                return False

            # Create and add assistant message
            assistant_msg = (
                Message.from_tool_calls(content=content, tool_calls=self.tool_calls)
                if self.tool_calls
                else Message.assistant_message(content)
            )
            self.memory.add_message(assistant_msg)

            if self.tool_choices == ToolChoice.REQUIRED and not self.tool_calls:
                return True  # Will be handled in act()

            # For 'auto' mode, continue with content if no commands but content exists
            if self.tool_choices == ToolChoice.AUTO and not self.tool_calls:
                return bool(content)

            return bool(self.tool_calls)
        except Exception as e:
            logger.error(f"🚨 Oops! The {self.name}'s thinking process hit a snag: {e}")
            self.memory.add_message(
                Message.assistant_message(
                    f"Error encountered while processing: {str(e)}"
                )
            )
            return False

    async def act(self) -> str:
        """Execute tool calls and handle their results (Parallel Execution)"""
        if not self.tool_calls:
            if self.tool_choices == ToolChoice.REQUIRED:
                raise ValueError(TOOL_CALL_REQUIRED)

            # Return last message content if no tool calls
            return self.messages[-1].content or "No content or commands to execute"

        # Execute tools in parallel using asyncio.gather
        tasks = []
        for command in self.tool_calls:
            tasks.append(self.execute_tool(command))

        results = await asyncio.gather(*tasks)

        for i, command in enumerate(self.tool_calls):
            result = results[i]
            if self.max_observe:
                result = result[: self.max_observe]

            logger.info(
                f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}"
            )

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result,
                tool_call_id=command.id,
                name=command.function.name,
            )
            self.memory.add_message(tool_msg)

        return "\n\n".join(results)

    def _sanitize_command(self, name: str, args: dict) -> bool:
        """Sanitize tool arguments (Security Layer)."""
        # Block dangerous shell commands
        # Using EthicalGuard now instead of hardcoded list here, but keeping basic check or delegating?
        # I'll delegate to EthicalGuard in execute_tool.
        return True

    async def execute_tool(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling and security checks"""
        start_time = time.time()

        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            # Parse arguments
            args_str = command.function.arguments or "{}"
            args = json.loads(args_str)

            # 1. Audit Log (Start)
            self._audit.log_tool_call(
                task_id=self.memory.messages[0].content[:20] if self.memory.messages else "unknown", # weak task id
                user_id=self._user.id,
                tool_name=name,
                tool_args=Sanitizer.sanitize(args) # Sanitize PII in logs
            )

            # 2. Ethical Guard (Input)
            is_safe, error_msg = EthicalGuard.check_tool_args(name, args)
            if not is_safe:
                self._audit.log_event("security_blocked", tool_name=name, payload=error_msg)
                return f"Error: {error_msg}"

            # 2.5. Digital Immunity (Behavioral Check)
            if not self._immunity.monitor_tool_call(name, args):
                error_msg = f"Digital Immunity blocked tool '{name}' due to suspicious behavior."
                self._audit.log_event("immunity_blocked", tool_name=name, payload=error_msg)
                return f"Error: {error_msg}"

            # 3. RBAC Check
            action = Action.EXEC
            if "read" in name: action = Action.READ
            if "write" in name: action = Action.WRITE
            if "navigate" in name: action = Action.NAVIGATE

            # Refine action based on args if available (for tools like file_tool)
            if "action" in args:
                val = args["action"].lower()
                if "read" in val: action = Action.READ
                elif "write" in val or "append" in val or "edit" in val: action = Action.WRITE
                elif "navigate" in val or "goto" in val: action = Action.NAVIGATE
                elif "init" in val: action = Action.INIT
                elif "cron" in val: action = Action.CRON

            # Allow fallback to string if Action enum fails or just pass string
            action_str = str(action.value) if isinstance(action, Action) else action

            if not self._rbac.check_permission(self._user, name, action_str, args):
                error_msg = f"Permission denied for user role {self._user.role} on {name}"
                self._audit.log_event("rbac_denied", tool_name=name, payload=error_msg)
                return f"Error: {error_msg}"

            # Compliance Logging (Chapter 40)
            if name in ["file_tool", "search_tool", "mcp_tool"]:
                 self._compliance.register_data_access(
                     user_id=self._user.id,
                     data_id=f"{name}:{action_str}",
                     purpose=f"Tool execution: {name} {action_str}"
                 )

            # 4. Secrets Injection
            required_keys = TOOL_REQUIRED_SECRETS.get(name, [])

            logger.info(f"🔧 Activating tool: '{name}'...")

            # 5. Execution (with Context Manager for Secrets)
            # Use inject_env_vars context manager which handles cleanup
            # Wrap with lock to prevent race conditions on os.environ in threaded/async env
            async with self._secrets_lock:
                with self._secrets.inject_env_vars(required_keys):
                    result = await self.available_tools.execute(name=name, tool_input=args)

            # Handle special tools
            await self._handle_special_tool(name=name, result=result)

            # Format result
            observation = str(result) if result else f"Cmd `{name}` completed with no output"

            # 6. Ethical Guard (Output) - e.g. check for PII leaks in output?
            # Sanitizer handles PII masking. EthicalGuard could block massive leaks if implemented.

            # 7. Sanitize Output
            observation = Sanitizer.sanitize(observation)

            # 8. Output Truncation
            if len(observation) > 5000:
                observation = observation[:5000] + "\n... [Output Truncated]"

            # 9. Audit Log (End)
            duration = (time.time() - start_time) * 1000
            self._audit.log_tool_result(
                task_id="unknown",
                user_id=self._user.id,
                tool_name=name,
                status="success",
                duration_ms=duration,
                result=observation
            )

            # Immunity: Record Success
            self._immunity.record_success(name)

            return observation

        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(f"📝 Invalid JSON args: {command.function.arguments}")
            return f"Error: {error_msg}"
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.exception(error_msg)

            self._audit.log_tool_result(
                task_id="unknown",
                user_id=self._user.id,
                tool_name=name,
                status="error",
                duration_ms=duration,
                result=str(e)
            )

            # Immunity: Record Failure
            self._immunity.record_failure(name)

            return f"Error: {error_msg}"

    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED

    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True

    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]

    async def cleanup(self):
        """Clean up resources used by the agent's tools."""
        logger.info(f"🧹 Cleaning up resources for agent '{self.name}'...")
        for tool_name, tool_instance in self.available_tools.tool_map.items():
            if hasattr(tool_instance, "cleanup") and asyncio.iscoroutinefunction(
                tool_instance.cleanup
            ):
                try:
                    logger.debug(f"🧼 Cleaning up tool: {tool_name}")
                    await tool_instance.cleanup()
                except Exception as e:
                    logger.error(
                        f"🚨 Error cleaning up tool '{tool_name}': {e}", exc_info=True
                    )
        logger.info(f"✨ Cleanup complete for agent '{self.name}'.")

    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with cleanup when done."""
        # Prompt Guard (Input)
        if request:
            is_safe, error_msg = PromptGuard.check_input(request)
            if not is_safe:
                return f"Error: {error_msg}"

        try:
            result = await super().run(request)
            return result
        finally:
            await self.cleanup()

    def collect_feedback(self, session_id: str, user_input: str, agent_output: str, rating: int, comment: str = None):
        """Collect user feedback for RLHF."""
        self._feedback.collect(session_id, "unknown_task", user_input, agent_output, rating, comment)
