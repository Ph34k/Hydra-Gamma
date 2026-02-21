import asyncio
import re
from typing import List, Optional, Dict, Any, Tuple
from app.llm import LLM
from app.logger import logger
from app.schema import Message

class ReasoningEngine:
    def __init__(self, llm: LLM):
        self.llm = llm

    async def analyze_complexity(self, context: str) -> str:
        """
        Analyze the complexity of the task to decide the reasoning strategy.
        Returns: 'Low', 'Medium', or 'High'
        """
        prompt = f"""
        Analyze the complexity of the following task/context.
        Classify it as 'Low', 'Medium', or 'High'.

        'Low': Simple factual questions, single-step actions.
        'Medium': Multi-step tasks, linear logic.
        'High': Ambiguous tasks, code debugging, creative writing, complex planning.

        Context:
        {context}

        Return ONLY the classification label.
        """
        try:
            response = await self.llm.ask(
                messages=[Message.user_message(prompt)],
                stream=False,
                temperature=0.1
            )
            complexity = response.strip().replace("'", "").replace('"', "")
            if complexity not in ['Low', 'Medium', 'High']:
                return 'Medium' # Default
            return complexity
        except Exception as e:
            logger.error(f"Error analyzing complexity: {e}")
            return 'Medium'

    async def reflect_and_refine(self, context: str, initial_thought: str) -> str:
        """
        Implement Self-Correction loop.
        """
        # Step 2: Critique
        critique_prompt = f"""
        Context: {context}

        Proposed Thought/Plan:
        {initial_thought}

        Critique the above thought. Identify logical flaws, missing information, or risks.
        Be concise.
        """
        critique = await self.llm.ask([Message.user_message(critique_prompt)], stream=False)

        # Step 3: Refine
        refine_prompt = f"""
        Original Thought: {initial_thought}
        Critique: {critique}

        Refine the original thought based on the critique to create a better plan/response.
        """
        final_thought = await self.llm.ask([Message.user_message(refine_prompt)], stream=False)

        logger.info(f"Refined thought: {final_thought}")
        return final_thought

    async def _generate_candidates(self, context: str, n: int = 3) -> List[str]:
        """Generate N distinct candidate plans."""
        prompt = f"""
        Context: {context}

        Generate {n} DISTINCT and VALID next steps or short-term plans to solve the current problem.
        Ensure they are different approaches.

        Format your response exactly as:
        Option 1: [Description]
        Option 2: [Description]
        ...
        """
        response = await self.llm.ask([Message.user_message(prompt)], stream=False)

        # Parse options
        candidates = []
        for line in response.split("\n"):
            if line.strip().startswith("Option"):
                candidates.append(line.split(":", 1)[1].strip())

        # Fallback if parsing fails
        if not candidates:
            candidates = [response]

        return candidates[:n]

    async def _evaluate_candidates(self, context: str, candidates: List[str]) -> List[Tuple[str, float, str]]:
        """Simulate and score candidates. Returns list of (candidate, score, simulation_log)."""
        results = []
        for candidate in candidates:
            prompt = f"""
            Context: {context}

            Proposed Action: {candidate}

            1. SIMULATE: Mentally simulate the execution of this action. What is the likely outcome? What are the risks?
            2. SCORE: Assign a feasibility score from 0.0 to 10.0 based on effectiveness and safety.

            Return format:
            SCORE: [0-10]
            SIMULATION: [Explanation]
            """
            eval_response = await self.llm.ask([Message.user_message(prompt)], stream=False)

            score = 0.0
            simulation = eval_response

            # Extract score
            match = re.search(r"SCORE:\s*([\d\.]+)", eval_response)
            if match:
                try:
                    score = float(match.group(1))
                except:
                    pass

            results.append((candidate, score, simulation))

        return results

    async def tree_of_thought(self, context: str, candidates: int = 3) -> str:
        """
        Implement Tree-of-Thought: Generate multiple paths, simulate results, score them, pick the best.
        Explicitly separates generation and evaluation.
        """
        logger.info("Starting Tree-of-Thought reasoning...")

        # 1. Generate Candidates
        options = await self._generate_candidates(context, candidates)
        if not options:
            return "Unable to generate options."

        # 2. Simulate & Evaluate
        scored_options = await self._evaluate_candidates(context, options)

        # 3. Select Best
        best_option = max(scored_options, key=lambda x: x[1])

        logger.info(f"ToT Selected: {best_option[0]} (Score: {best_option[1]})")

        return f"""
        Tree of Thought Selection:
        Selected Option: {best_option[0]}
        Reasoning: {best_option[2]}
        """

    async def decide_strategy(self, context: str) -> str:
        """
        Decide and execute the reasoning strategy.
        """
        complexity = await self.analyze_complexity(context[:1000]) # Limit context for analysis
        logger.info(f"Task Complexity: {complexity}")

        if complexity == 'High':
            return await self.tree_of_thought(context)
        elif complexity == 'Medium':
            # Generate initial thought then refine
            initial = await self.llm.ask([Message.user_message(f"Context: {context}\n\nWhat should be the next step?")], stream=False)
            return await self.reflect_and_refine(context, initial)
        else: # Low
            # Standard CoT (handled by default prompt) or simple generation
            return "Proceed with standard execution."
