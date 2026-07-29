"""Task state management."""

import time
import uuid
from typing import Dict, Optional
from .models import TaskState, TaskDispatch, TaskReport, TaskStatus, TaskVerdict


class TaskManager:
    """Manages task state and lifecycle."""

    def __init__(self):
        """Initialize task manager with empty state."""
        self._tasks: Dict[str, TaskState] = {}

    def create_task(self, dispatch: TaskDispatch) -> TaskState:
        """
        Create a new task from a dispatch message.

        Args:
            dispatch: Task dispatch message

        Returns:
            TaskState: Created task state
        """
        task_id = dispatch.task_id or str(uuid.uuid4())
        dispatch.task_id = task_id

        now = time.time()
        task = TaskState(
            task_id=task_id,
            dispatch=dispatch,
            status=TaskStatus.QUEUED,
            created_at=now,
            updated_at=now
        )

        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[TaskState]:
        """
        Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Optional[TaskState]: Task state if found, None otherwise
        """
        return self._tasks.get(task_id)

    def update_task_status(self, task_id: str, status: TaskStatus) -> Optional[TaskState]:
        """
        Update task status.

        Args:
            task_id: Task identifier
            status: New status

        Returns:
            Optional[TaskState]: Updated task state if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if task:
            task.status = status
            task.updated_at = time.time()
        return task

    def set_task_report(self, task_id: str, report: TaskReport) -> Optional[TaskState]:
        """
        Set task report.

        Args:
            task_id: Task identifier
            report: Task report from SLM

        Returns:
            Optional[TaskState]: Updated task state if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if task:
            task.report = report
            task.status = report.status
            task.updated_at = time.time()
        return task

    def set_task_verdict(self, task_id: str, verdict: TaskVerdict) -> Optional[TaskState]:
        """
        Set task verdict.

        Args:
            task_id: Task identifier
            verdict: Verdict from orchestrator

        Returns:
            Optional[TaskState]: Updated task state if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if task:
            task.verdict = verdict
            task.updated_at = time.time()
        return task

    def list_tasks(self) -> Dict[str, TaskState]:
        """
        List all tasks.

        Returns:
            Dict[str, TaskState]: All tasks
        """
        return self._tasks.copy()
