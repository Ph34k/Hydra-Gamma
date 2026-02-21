from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
from app.agent.core import AgentCore
from app.logger import logger
from app.tool.file_tool import FileTool
from app.tool.shell_tool import ShellTool
from app.tool.python_execute import PythonExecute


class ImprovementHypothesis(BaseModel):
    """Data model for a proposed improvement."""
    target_component: str
    problem_description: str
    proposed_solution: str
    confidence_score: float


class CodePatch(BaseModel):
    """Data model for a code patch."""
    file_path: str
    diff_content: str
    description: str


class TestResult(BaseModel):
    """Data model for validation result."""
    passed: bool
    output: str
    error: Optional[str] = None


class MetaProgrammerAgent(AgentCore):
    """
    The Meta-Programmer Agent (Chapter 49).
    Responsible for analyzing agent performance, proposing code improvements,
    validating changes in a sandbox, and deploying them.
    """
    name: str = "MetaProgrammerAgent"
    description: str = "Self-improvement agent for code analysis and fixes."

    # Tools for code manipulation
    file_tool: FileTool = Field(default_factory=FileTool)
    shell_tool: ShellTool = Field(default_factory=ShellTool)
    python_tool: PythonExecute = Field(default_factory=PythonExecute)

    def analyze_performance(
        self,
        metrics_data: Dict[str, Any]
    ) -> Optional[ImprovementHypothesis]:
        """
        Analyze performance metrics to identify bottlenecks.
        (Chapter 49.3 Step 1)
        """
        logger.info("MetaProgrammer: Analyzing performance metrics...")

        # Heuristic: Detect high failure rate tools
        failure_counts = metrics_data.get("failure_counts", {})
        for tool_name, failure_count in failure_counts.items():
            if failure_count > 3:
                return ImprovementHypothesis(
                    target_component=f"Tool:{tool_name}",
                    problem_description=f"High failure rate in {tool_name}",
                    proposed_solution=f"Review error handling for {tool_name}",
                    confidence_score=0.8
                )
        return None

    async def propose_code_change(
        self,
        hypothesis: ImprovementHypothesis
    ) -> Optional[CodePatch]:
        """
        Generate a code patch based on the hypothesis using the LLM.
        (Chapter 49.3 Step 2)
        """
        logger.info(f"Proposing fix for {hypothesis.target_component}")

        # Read the target file
        target_file = f"app/tool/{hypothesis.target_component.split(':')[1]}.py"
        try:
            current_code = await self.file_tool.read(target_file)
        except Exception as e:
            logger.warning(f"Could not read target file {target_file}: {e}")
            return None

        prompt = f"""
        You are an expert Python developer optimization agent.
        Problem: {hypothesis.problem_description}
        Solution Idea: {hypothesis.proposed_solution}

        Target File: {target_file}

        Current Code:
        ```python
        {current_code}
        ```

        Generate the FULL content of the fixed file. Do not use diffs.
        Ensure you handle edge cases and import necessary modules.
        """

        if self.llm:
            try:
                from app.schema import Message
                response = await self.llm.ask(
                    messages=[Message.user_message(prompt)]
                )

                # Extract code block if present
                content = response
                if "```python" in content:
                    content = content.split("```python")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]

                return CodePatch(
                    file_path=target_file,
                    diff_content=content.strip(),
                    description=f"Fix for {hypothesis.problem_description}"
                )
            except Exception as e:
                logger.error(f"MetaProgrammer LLM generation failed: {e}")
                return None

        # Fallback for tests without mocked LLM response
        return CodePatch(
            file_path=target_file,
            diff_content="# LLM Unavailable - Patch Stub",
            description=f"Fix for {hypothesis.problem_description}"
        )

    async def validate_change(self, patch: CodePatch) -> TestResult:
        """
        Validate the patch in a sandbox environment.
        (Chapter 49.3 Step 3)
        """
        logger.info(f"MetaProgrammer: Validating patch for {patch.file_path}")

        # 1. Create a temporary test file
        test_file = patch.file_path + ".test_ver"
        try:
            await self.file_tool.write(test_file, patch.diff_content)

            # 2. Run syntax check
            cmd = f"python3 -m py_compile {test_file}"
            result = await self.shell_tool.execute(command=cmd)

            if "Error" in result or "Exception" in result:
                return TestResult(
                    passed=False,
                    output=result,
                    error="Syntax Error"
                )

            return TestResult(passed=True, output="Syntax Check Passed")

        except Exception as e:
            return TestResult(
                passed=False,
                output=str(e),
                error="Validation Exception"
            )
        finally:
            # Cleanup
            try:
                await self.shell_tool.execute(command=f"rm {test_file}")
            except Exception:
                pass  # Ignore cleanup errors

    async def deploy_change(self, patch: CodePatch) -> bool:
        """
        Deploy the validated change to the codebase.
        (Chapter 49.3 Step 4)
        """
        logger.info(f"MetaProgrammer: Deploying patch to {patch.file_path}")
        try:
            # 1. Backup original
            backup_path = patch.file_path + ".bak"
            original_content = await self.file_tool.read(patch.file_path)
            await self.file_tool.write(backup_path, original_content)

            # 2. Apply patch (Overwrite for now)
            await self.file_tool.write(patch.file_path, patch.diff_content)

            logger.info("MetaProgrammer: Deployment successful.")
            return True
        except Exception as e:
            logger.error(f"MetaProgrammer: Deployment failed: {e}")
            return False
