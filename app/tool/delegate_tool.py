from typing import Any, Dict

from app.logger import logger
from app.tool.base import BaseTool, ToolResult
# Imports will be inside execute to avoid circular dependency with SwarmOrchestrator if it imports this tool

class DelegateTool(BaseTool):
    name: str = "delegate_task"
    description: str = """
    Delegate a sub-task to a specialized agent.
    Available agents:
    - coding_agent: For software engineering, testing, git.
    - research_agent: For deep research, synthesis, grounding.
    - sales_agent: For prospecting, CRM, outreach.
    - support_agent: For ticket resolution, RAG.
    - data_science_agent: For analysis, visualization.
    """
    parameters: dict = {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "enum": ["coding_agent", "research_agent", "sales_agent", "support_agent", "data_science_agent"],
                "description": "The name of the specialized agent to delegate to.",
            },
            "task": {
                "type": "string",
                "description": "The specific task description for the agent.",
            },
        },
        "required": ["agent_name", "task"],
    }

    async def execute(self, agent_name: str, task: str, **kwargs) -> ToolResult:
        try:
            logger.info(f"Delegating task to {agent_name}: {task}")

            # Lazy import to avoid circular dependencies
            from app.agent.specialized.coding import CodingAgent
            from app.agent.specialized.research import ResearchAgent
            from app.agent.specialized.sales import SalesAgent
            from app.agent.specialized.support import SupportAgent
            from app.agent.specialized.data_science import DataScienceAgent

            agent = None
            if agent_name == "coding_agent":
                agent = CodingAgent()
            elif agent_name == "research_agent":
                agent = ResearchAgent()
            elif agent_name == "sales_agent":
                agent = SalesAgent()
            elif agent_name == "support_agent":
                agent = SupportAgent()
            elif agent_name == "data_science_agent":
                agent = DataScienceAgent()
            else:
                return ToolResult(error=f"Unknown agent: {agent_name}")

            # Run the agent
            # Note: We might want to pass context or memory, but for now simple task delegation
            result = await agent.run(task)

            return ToolResult(output=f"Agent {agent_name} completed task. Result:\n{result}")

        except Exception as e:
            logger.exception(f"Delegation failed: {e}")
            return ToolResult(error=f"Delegation failed: {str(e)}")
