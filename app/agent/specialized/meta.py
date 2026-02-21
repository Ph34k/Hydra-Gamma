import os
import re
import json
import ast
import shutil
import tempfile
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
    Enhanced with concrete analysis, validation, and deployment capabilities.
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

            # Use the LLM to generate a full file replacement or a diff
            # For robustness, we ask for the full new content of the file
            prompt = f"""
            You are the Meta-Programmer.
            I have identified an issue in `{file_path}`:
            {issue_description}

            Here is the current content of the file:
            ```python
            {code_content}
            ```

            Please provide the FULL corrected content of the file in a python code block.
            Ensure syntax is correct.
            """

            response = await self.llm.ask(prompt)

            # Extract code from markdown block
            code_match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
            if code_match:
                return code_match.group(1)

            return response # Fallback: return raw response (might fail validation)

        except Exception as e:
            logger.error(f"MetaProgrammer: Failed to propose change: {e}")
            return f"Error: {e}"

    def validate_change(self, new_code: str) -> bool:
        """
        Validate the syntax of the proposed code change.
        (Chapter 49.5: Riscos e Salvaguardas)
        """
        try:
            ast.parse(new_code)
            return True
        except SyntaxError as e:
            logger.error(f"MetaProgrammer: Proposed code has syntax error: {e}")
            return False
        except Exception as e:
            logger.error(f"MetaProgrammer: Validation failed: {e}")
            return False

    def deploy_change(self, file_path: str, new_code: str) -> bool:
        """
        Deploy the validated change to the codebase.
        Includes backup mechanism.
        """
        backup_path = f"{file_path}.bak"
        try:
            # Create backup
            shutil.copy2(file_path, backup_path)

            # Write new code
            with open(file_path, 'w') as f:
                f.write(new_code)

            logger.info(f"MetaProgrammer: Deployed change to {file_path}. Backup at {backup_path}")
            return True
        except Exception as e:
            logger.error(f"MetaProgrammer: Failed to deploy change: {e}")
            # Restore backup if possible
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, file_path)
            return False

    async def run_self_improvement_cycle(self, log_path: str = "app.log"):
        """
        Orchestrate the full self-improvement loop.
        (Chapter 49.2: Ciclo de Auto-Melhoria)
        """
        logger.info("MetaProgrammer: Starting self-improvement cycle...")

        # 1. Analyze
        analysis = await self.analyze_performance(log_path)
        logger.info(f"MetaProgrammer: Analysis complete. Found {analysis.get('metrics', {}).get('errors', 0)} errors.")

        if analysis.get('metrics', {}).get('errors', 0) > 0:
            # 2. Identify Issue
            issue = analysis['critical_issues'][0]

            # Heuristic target file selection
            target_file = "app/agent/core.py"
            if "sandbox" in issue.lower():
                target_file = "app/sandbox/docker.py"

            logger.info(f"MetaProgrammer: Targeting {target_file} based on: {issue}")

            # 3. Propose Change
            new_code = await self.propose_code_change(target_file, issue)

            if not new_code or "Error" in new_code:
                logger.warning("MetaProgrammer: Failed to generate valid code.")
                return "Failed to generate code."

            # 4. Validate
            if self.validate_change(new_code):
                logger.info("MetaProgrammer: Code validation passed.")

                # 5. Deploy (In a real scenario, run tests before deploy)
                if self.deploy_change(target_file, new_code):
                    return f"Successfully patched {target_file}"
                else:
                    return "Deployment failed."
            else:
                logger.warning("MetaProgrammer: Code validation failed.")
                return "Validation failed."

        return "No critical issues found to improve."
