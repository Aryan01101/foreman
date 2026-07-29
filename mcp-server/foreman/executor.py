"""Task executor using serving backend."""

import logging
from typing import Optional
from .models import TaskDispatch, TaskReport, TaskStatus
from .serving import ServingBackend

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executes tasks using the serving backend."""

    def __init__(self, backend: ServingBackend):
        """
        Initialize task executor.

        Args:
            backend: Serving backend to use for execution
        """
        self.backend = backend

    async def execute_task(self, dispatch: TaskDispatch) -> TaskReport:
        """
        Execute a task using the SLM.

        Args:
            dispatch: Task dispatch message

        Returns:
            TaskReport: Task execution report
        """
        try:
            # Build prompt for the SLM
            prompt = self._build_prompt(dispatch)

            # Generate response from SLM
            logger.info(f"Executing task {dispatch.task_id}: {dispatch.objective}")
            response = await self.backend.generate(
                prompt=prompt,
                max_tokens=4096,
                temperature=0.3  # Lower temperature for code generation
            )

            if response is None:
                return TaskReport(
                    task_id=dispatch.task_id,
                    status=TaskStatus.FAILED,
                    error="Failed to generate response from SLM"
                )

            # Parse response (simplified for MVP)
            # In production, this would parse structured output from the SLM
            report = TaskReport(
                task_id=dispatch.task_id,
                status=TaskStatus.COMPLETED,
                diff=response,  # For MVP, treat full response as diff
                assumptions=[],
                self_check="Task completed"
            )

            return report

        except Exception as e:
            logger.error(f"Error executing task {dispatch.task_id}: {e}")
            return TaskReport(
                task_id=dispatch.task_id,
                status=TaskStatus.FAILED,
                error=str(e)
            )

    def _build_prompt(self, dispatch: TaskDispatch) -> str:
        """
        Build prompt for the SLM.

        Args:
            dispatch: Task dispatch message

        Returns:
            str: Formatted prompt
        """
        prompt = f"""You are a code generation agent. Complete the following task:

## Objective
{dispatch.objective}

## Scope
Editable files: {', '.join(dispatch.scope.get('editable', []))}
Read-only files: {', '.join(dispatch.scope.get('readonly', []))}

## Acceptance Criteria
"""
        for i, criterion in enumerate(dispatch.acceptance_criteria, 1):
            prompt += f"{i}. {criterion}\n"

        prompt += f"\n## Output Format\n{dispatch.output_format}\n"

        if dispatch.context_ref:
            prompt += f"\n## Context Reference\n{dispatch.context_ref}\n"

        prompt += """
## Instructions
1. Analyze the objective and scope
2. Generate the required code changes
3. Provide a unified diff showing all changes
4. List any assumptions you made
5. Perform a self-check against the acceptance criteria

Generate your response now:
"""

        return prompt
