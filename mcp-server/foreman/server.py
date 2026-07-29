"""Foreman MCP Server implementation."""

import asyncio
import logging
from typing import Any, Dict, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .task_manager import TaskManager
from .models import TaskDispatch, TaskReport, TaskStatus, TaskVerdict
from .executor import TaskExecutor
from .serving import create_backend, ServingBackend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ForemanServer:
    """Foreman MCP Server - manages task dispatch and orchestration."""

    def __init__(self):
        """Initialize the Foreman server."""
        self.server = Server("foreman")
        self.task_manager = TaskManager()
        self.backend: Optional[ServingBackend] = None
        self.executor: Optional[TaskExecutor] = None
        self._setup_handlers()

    async def initialize_backend(self):
        """Initialize the serving backend and executor."""
        logger.info("Initializing serving backend...")
        self.backend = await create_backend()

        if self.backend is None:
            logger.error("Failed to initialize any backend!")
            raise RuntimeError("No serving backend available")

        self.executor = TaskExecutor(self.backend)
        logger.info(f"Backend initialized: {self.backend.name}")

    def _setup_handlers(self):
        """Set up MCP server handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="dispatch_task",
                    description="Dispatch a task to the local SLM for execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "Unique identifier for the task (optional, will be generated if not provided)"
                            },
                            "objective": {
                                "type": "string",
                                "description": "Clear description of what needs to be done"
                            },
                            "scope": {
                                "type": "object",
                                "properties": {
                                    "editable": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of files the SLM can edit"
                                    },
                                    "readonly": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "List of read-only files"
                                    }
                                },
                                "required": ["editable", "readonly"],
                                "description": "Files the SLM can edit vs. read-only files"
                            },
                            "acceptance_criteria": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "How to verify success"
                            },
                            "output_format": {
                                "type": "string",
                                "description": "Expected format of the result"
                            },
                            "context_ref": {
                                "type": "string",
                                "description": "Reference to shared standing-context file"
                            }
                        },
                        "required": ["objective", "scope", "acceptance_criteria", "output_format"]
                    }
                ),
                Tool(
                    name="check_status",
                    description="Check the status of a dispatched task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "ID of the task to check"
                            }
                        },
                        "required": ["task_id"]
                    }
                ),
                Tool(
                    name="get_report",
                    description="Get the report for a completed task",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "ID of the completed task"
                            }
                        },
                        "required": ["task_id"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool calls."""
            if name == "dispatch_task":
                return await self._dispatch_task(arguments)
            elif name == "check_status":
                return await self._check_status(arguments)
            elif name == "get_report":
                return await self._get_report(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")

    async def _dispatch_task(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """
        Dispatch a task to the local SLM.

        Args:
            arguments: Task dispatch arguments

        Returns:
            list[TextContent]: Confirmation message with task ID
        """
        try:
            # Create dispatch message
            dispatch = TaskDispatch(**arguments)

            # Create task in task manager
            task = self.task_manager.create_task(dispatch)

            logger.info(f"Task {task.task_id} dispatched: {dispatch.objective}")

            # Check if executor is initialized
            if self.executor is None:
                logger.error("Executor not initialized - backend may have failed to start")
                self.task_manager.update_task_status(task.task_id, TaskStatus.FAILED)
                return [
                    TextContent(
                        type="text",
                        text=f"Error: Backend not initialized. Please check server logs."
                    )
                ]

            # Mark as queued initially
            self.task_manager.update_task_status(task.task_id, TaskStatus.QUEUED)

            # Execute task asynchronously in background
            asyncio.create_task(self._execute_task_async(task.task_id, dispatch))

            return [
                TextContent(
                    type="text",
                    text=f"Task dispatched successfully.\n\nTask ID: {task.task_id}\nStatus: queued\n\nThe task is being processed by the local SLM. Use check_status to monitor progress."
                )
            ]

        except Exception as e:
            logger.error(f"Error dispatching task: {e}")
            return [
                TextContent(
                    type="text",
                    text=f"Error dispatching task: {str(e)}"
                )
            ]

    async def _execute_task_async(self, task_id: str, dispatch: TaskDispatch):
        """
        Execute a task asynchronously in the background.

        Args:
            task_id: Task ID
            dispatch: Task dispatch message
        """
        try:
            # Update status to running
            self.task_manager.update_task_status(task_id, TaskStatus.RUNNING)
            logger.info(f"Task {task_id} started execution")

            # Execute the task
            report = await self.executor.execute_task(dispatch)

            # Update task with report
            self.task_manager.update_task_report(task_id, report)
            self.task_manager.update_task_status(task_id, report.status)

            logger.info(f"Task {task_id} completed with status: {report.status}")

        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            # Create error report
            error_report = TaskReport(
                task_id=task_id,
                status=TaskStatus.FAILED,
                error=str(e)
            )
            self.task_manager.update_task_report(task_id, error_report)
            self.task_manager.update_task_status(task_id, TaskStatus.FAILED)

    async def _check_status(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """
        Check the status of a task.

        Args:
            arguments: Status check arguments

        Returns:
            list[TextContent]: Task status information
        """
        task_id = arguments.get("task_id")

        if not task_id:
            return [
                TextContent(
                    type="text",
                    text="Error: task_id is required"
                )
            ]

        task = self.task_manager.get_task(task_id)

        if not task:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Task {task_id} not found"
                )
            ]

        status_text = f"Task ID: {task.task_id}\nStatus: {task.status}\n"
        status_text += f"Created: {task.created_at}\nUpdated: {task.updated_at}\n"

        if task.report:
            status_text += f"\nReport available: Yes"
        else:
            status_text += f"\nReport available: No"

        return [
            TextContent(
                type="text",
                text=status_text
            )
        ]

    async def _get_report(self, arguments: Dict[str, Any]) -> list[TextContent]:
        """
        Get the report for a completed task.

        Args:
            arguments: Report retrieval arguments

        Returns:
            list[TextContent]: Task report
        """
        task_id = arguments.get("task_id")

        if not task_id:
            return [
                TextContent(
                    type="text",
                    text="Error: task_id is required"
                )
            ]

        task = self.task_manager.get_task(task_id)

        if not task:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Task {task_id} not found"
                )
            ]

        if not task.report:
            return [
                TextContent(
                    type="text",
                    text=f"Error: Task {task_id} has no report yet (status: {task.status})"
                )
            ]

        # Format report
        report_text = f"Task ID: {task.task_id}\n"
        report_text += f"Status: {task.report.status}\n\n"

        # Check for cooperative decomposition
        if task.report.status == TaskStatus.NEEDS_DECOMPOSITION:
            if task.report.decomposition_reasoning:
                report_text += f"Decomposition Reasoning:\n{task.report.decomposition_reasoning}\n\n"

            if task.report.suggested_subtasks:
                report_text += f"Suggested Subtasks ({len(task.report.suggested_subtasks)}):\n"
                for i, subtask in enumerate(task.report.suggested_subtasks, 1):
                    report_text += f"\n{i}. {subtask.objective}\n"
                    report_text += f"   Complexity: {subtask.estimated_complexity or 'unknown'}\n"
                    report_text += f"   Rationale: {subtask.rationale}\n"
                    if subtask.requires:
                        report_text += f"   Requires: {', '.join(subtask.requires)}\n"
                    report_text += f"   Scope: {len(subtask.scope.get('editable', []))} editable files\n"
                report_text += "\n"

        if task.report.diff:
            report_text += f"Diff:\n{task.report.diff}\n\n"

        if task.report.assumptions:
            report_text += f"Assumptions:\n"
            for assumption in task.report.assumptions:
                report_text += f"  - {assumption}\n"
            report_text += "\n"

        if task.report.self_check:
            report_text += f"Self-check:\n{task.report.self_check}\n\n"

        if task.report.error:
            report_text += f"Error:\n{task.report.error}\n"

        return [
            TextContent(
                type="text",
                text=report_text
            )
        ]

    async def run(self):
        """Run the MCP server."""
        # Initialize backend before starting server
        await self.initialize_backend()

        async with stdio_server() as (read_stream, write_stream):
            logger.info("Foreman MCP Server starting...")
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """Main entry point."""
    server = ForemanServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
