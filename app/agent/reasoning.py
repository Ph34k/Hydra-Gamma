import asyncio
from typing import List, Optional, Dict, Any
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

    async def tree_of_thought(self, context: str, candidates: int = 3) -> str:
        """
        Implement Tree-of-Thought: Generate multiple paths, simulate results, score them, pick the best.
        """
        # 1. Generate Candidates
        candidates_prompt = f"""
        Context: {context}

        Generate {candidates} distinct valid next steps or plans to solve the current problem.
        Format them as:
        Option 1: ...
        Option 2: ...
        """
        options_text = await self.llm.ask([Message.user_message(candidates_prompt)], stream=False)

        # 2. Simulate & Evaluate
        # We ask the LLM to perform the simulation and scoring as part of its reasoning process
        eval_prompt = f"""
        Context: {context}

        Proposed Options:
        {options_text}

        For each option:
        1. Simulate the likely outcome: What happens if we take this step? What are the risks?
        2. Assign a feasibility score (0-10) based on the simulation.

        After analyzing all options, select the single best one.
        Return ONLY the content of the best option (do not include the score or simulation in the final output).
        """
        best_option = await self.llm.ask([Message.user_message(eval_prompt)], stream=False)

        logger.info(f"ToT Selected: {best_option}")
        return best_option

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
