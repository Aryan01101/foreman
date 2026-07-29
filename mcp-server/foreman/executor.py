"""Task executor using serving backend."""

import json
import logging
import re
from typing import Optional, Dict, Any, List
from .models import TaskDispatch, TaskReport, TaskStatus, SuggestedSubtask
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

            # Parse structured response
            report = self._parse_response(dispatch.task_id, response)

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
        Build prompt for the SLM with structured output guidance.

        Args:
            dispatch: Task dispatch message

        Returns:
            str: Formatted prompt
        """
        prompt = f"""You are Devstral, a code generation agent. Your task is to generate precise code changes following a structured output format.

## Objective
{dispatch.objective}

## Scope
Editable files: {', '.join(dispatch.scope.get('editable', []))}
Read-only files: {', '.join(dispatch.scope.get('readonly', []))}

## Acceptance Criteria
"""
        for i, criterion in enumerate(dispatch.acceptance_criteria, 1):
            prompt += f"{i}. {criterion}\n"

        if dispatch.context_ref:
            prompt += f"\n## Context Reference\n{dispatch.context_ref}\n"

        prompt += """
## Output Format

You MUST respond with a JSON object in a markdown code block. The JSON must follow this schema:

```json
{
  "status": "completed" | "needs_decomposition",
  "diff": "unified diff format code changes",
  "assumptions": ["assumption 1", "assumption 2"],
  "self_check": "brief verification against acceptance criteria",
  "needs_decomposition": false,
  "decomposition_reasoning": "why this task needs to be broken down (only if needs_decomposition=true)",
  "suggested_subtasks": [
    {
      "objective": "clear description of subtask",
      "scope": {
        "editable": ["file1.py"],
        "readonly": ["test1.py"]
      },
      "rationale": "why this subtask is needed",
      "requires": ["dependency 1"],
      "estimated_complexity": "low" | "medium" | "high"
    }
  ]
}
```

## When to Signal needs_decomposition

Signal needs_decomposition=true if:
- Task touches multiple concerns (auth + database + API)
- Complex dependencies between components
- Requires coordinated changes across 4+ files
- Uncertainty about how pieces should interact
- You estimate the task would take 200+ lines of changes

## Examples

### Example 1: Simple Task (Complete Directly)
Task: "Add email validation to User model"
Response:
```json
{
  "status": "completed",
  "diff": "--- a/models/user.py\\n+++ b/models/user.py\\n@@ -10,6 +10,12 @@\\n class User:\\n     email: str\\n+\\n+    def validate_email(self):\\n+        import re\\n+        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\\\.[a-zA-Z]{2,}$'\\n+        return re.match(pattern, self.email) is not None",
  "assumptions": ["Using standard email regex", "No external email validation service"],
  "self_check": "Added validation method, follows project style, handles edge cases",
  "needs_decomposition": false
}
```

### Example 2: Complex Task (Request Decomposition)
Task: "Add full user authentication system"
Response:
```json
{
  "status": "needs_decomposition",
  "needs_decomposition": true,
  "decomposition_reasoning": "Task involves 3 separate concerns: password hashing (security-critical), JWT tokens (shared utility), and auth endpoints (API layer). Each requires careful implementation and independent verification.",
  "suggested_subtasks": [
    {
      "objective": "Create User model with secure password hashing",
      "scope": {
        "editable": ["models/user.py"],
        "readonly": ["tests/test_user.py"]
      },
      "rationale": "Foundation layer - must be secure and well-tested before building on it",
      "requires": [],
      "estimated_complexity": "medium"
    },
    {
      "objective": "Implement JWT token generation and validation utilities",
      "scope": {
        "editable": ["utils/jwt.py"],
        "readonly": ["tests/test_jwt.py"]
      },
      "rationale": "Separate concern - reusable across multiple auth flows",
      "requires": ["User model interface"],
      "estimated_complexity": "medium"
    },
    {
      "objective": "Add login and registration endpoints",
      "scope": {
        "editable": ["routes/auth.py"],
        "readonly": ["tests/test_auth.py"]
      },
      "rationale": "Wire up the pieces - depends on User model and JWT utils being correct",
      "requires": ["User model", "JWT utilities"],
      "estimated_complexity": "low"
    }
  ]
}
```

## Instructions

1. **Analyze** the objective and scope carefully
2. **Decide**: Can you complete this in one go with confidence?
   - If YES: Generate the code changes and return status="completed"
   - If NO: Set needs_decomposition=true and suggest subtasks
3. **Generate** either:
   - Complete diff if status="completed"
   - Thoughtful subtask breakdown if needs_decomposition=true
4. **Self-check** your work against acceptance criteria
5. **Format** your response as JSON in a markdown code block

Generate your response now:
"""

        return prompt

    def _parse_response(self, task_id: str, response: str) -> TaskReport:
        """
        Parse structured response from SLM.

        Expected format: JSON in markdown code blocks
        ```json
        {
          "status": "completed" | "needs_decomposition",
          "diff": "...",
          "assumptions": ["..."],
          "self_check": "...",
          "needs_decomposition": false,
          "decomposition_reasoning": "...",
          "suggested_subtasks": [...]
        }
        ```

        Args:
            task_id: Task ID
            response: Raw SLM response

        Returns:
            TaskReport: Parsed report
        """
        try:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)

            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str)
            else:
                # Fallback: try to parse the entire response as JSON
                try:
                    data = json.loads(response)
                except json.JSONDecodeError:
                    # Last resort: treat as unstructured diff
                    logger.warning(f"Task {task_id}: Could not parse JSON, treating as diff")
                    return TaskReport(
                        task_id=task_id,
                        status=TaskStatus.COMPLETED,
                        diff=response,
                        assumptions=[],
                        self_check="Response not in structured format"
                    )

            # Extract fields
            status_str = data.get("status", "completed")
            needs_decomp = data.get("needs_decomposition", False)

            # Determine status
            if needs_decomp or status_str == "needs_decomposition":
                status = TaskStatus.NEEDS_DECOMPOSITION
            elif status_str == "failed":
                status = TaskStatus.FAILED
            else:
                status = TaskStatus.COMPLETED

            # Parse suggested subtasks if present
            suggested_subtasks = None
            if status == TaskStatus.NEEDS_DECOMPOSITION:
                subtasks_data = data.get("suggested_subtasks", [])
                if subtasks_data:
                    suggested_subtasks = [
                        SuggestedSubtask(**subtask) for subtask in subtasks_data
                    ]

            # Build report
            report = TaskReport(
                task_id=task_id,
                status=status,
                diff=data.get("diff", ""),
                assumptions=data.get("assumptions", []),
                self_check=data.get("self_check", ""),
                error=data.get("error"),
                suggested_subtasks=suggested_subtasks,
                decomposition_reasoning=data.get("decomposition_reasoning")
            )

            return report

        except Exception as e:
            logger.error(f"Error parsing response for task {task_id}: {e}")
            # Return a failed report with the error
            return TaskReport(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=f"Failed to parse SLM response: {str(e)}"
            )
