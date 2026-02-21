import os
import re
import json
from typing import List, Optional, Dict, Any

from pydantic import Field

from app.agent.manus import Manus
from app.prompt.specialized import META_PROGRAMMER_PROMPT
from app.tool import ToolCollection, Terminate
from app.tool.file_tool import FileTool
from app.tool.shell_tool import ShellTool
from app.tool.git_tool import GitTool
from app.logger import logger

class MetaProgrammerAgent(Manus):
    """
    The Meta-Programmer Agent (Chapter 49).
    Responsible for self-evolution, performance analysis, and code improvement.
    Enhanced with concrete analysis and proposal capabilities.
    """
    name: str = "meta_programmer_agent"
    description: str = "An advanced agent that can analyze and improve its own codebase."

    system_prompt: str = META_PROGRAMMER_PROMPT

    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            FileTool(),
            ShellTool(),
            GitTool(),
            Terminate()
        )
    )

    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    async def analyze_performance(self, log_path: str = "app.log") -> Dict[str, Any]:
        """
        Analyze logs to identify performance bottlenecks and errors.
        (Chapter 49.2: Monitoramento de Performance / Análise de Falhas)
        """
        if not os.path.exists(log_path):
            return {"error": "Log file not found", "path": log_path}

        issues = []
        metrics = {"errors": 0, "warnings": 0}

        try:
            with open(log_path, 'r') as f:
                logs = f.readlines()

            # Simple heuristic analysis
            for line in logs[-1000:]: # Analyze last 1000 lines
                if "ERROR" in line:
                    metrics["errors"] += 1
                    issues.append(line.strip())
                elif "WARNING" in line:
                    metrics["warnings"] += 1

            # Identify slow tool calls (if any structured logs exist)
            # This is a placeholder for more complex log parsing

            analysis_result = {
                "metrics": metrics,
                "critical_issues": issues[:10], # Top 10 errors
                "recommendation": "Review critical issues." if issues else "System stable."
            }
            return analysis_result
        except Exception as e:
            logger.error(f"MetaProgrammer: Failed to analyze logs: {e}")
            return {"error": str(e)}

    async def propose_code_change(self, file_path: str, issue_description: str) -> str:
        """
        Propose a code change (patch) to fix an issue or improve performance.
        (Chapter 49.4: Propose Code Change)
        """
        if not os.path.exists(file_path):
            return f"Error: File {file_path} not found."

        try:
            with open(file_path, 'r') as f:
                code_content = f.read()

            # Use the LLM to generate a patch
            prompt = f"""
            You are the Meta-Programmer.
            I have identified an issue in `{file_path}`:
            {issue_description}

            Here is the current content of the file:
            ```python
            {code_content}
            ```

            Please provide a unified diff or a rewritten version of the code to fix this issue.
            Focus on performance, safety, and maintainability.
            """

            # Use the agent's LLM to generate the response
            # We access the LLM directly here, assuming it's initialized
            response = await self.llm.ask(prompt)
            return response

        except Exception as e:
            logger.error(f"MetaProgrammer: Failed to propose change: {e}")
            return f"Error: {e}"

    async def run_self_improvement_cycle(self, log_path: str = "app.log"):
        """
        Orchestrate the self-improvement loop.
        (Chapter 49.2: Ciclo de Auto-Melhoria)
        """
        logger.info("MetaProgrammer: Starting self-improvement cycle...")

        # 1. Analyze
        analysis = await self.analyze_performance(log_path)
        logger.info(f"MetaProgrammer: Analysis complete. Found {analysis.get('metrics', {}).get('errors', 0)} errors.")

        if analysis.get('metrics', {}).get('errors', 0) > 0:
            # 2. Identify Issue (take the first one for now)
            issue = analysis['critical_issues'][0]

            # Extract file path from log if possible (very naive heuristic)
            # In a real system, logs would have structured context
            # Here we assume a hypothetical file for demonstration if not found
            target_file = "app/agent/core.py"

            logger.info(f"MetaProgrammer: Targeting {target_file} for improvement based on: {issue}")

            # 3. Propose Change
            proposal = await self.propose_code_change(target_file, issue)
            logger.info(f"MetaProgrammer: Generated proposal:\n{proposal[:200]}...")

            return proposal

        return "No critical issues found to improve."
