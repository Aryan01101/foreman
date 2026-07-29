"""Data models for Foreman protocol."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class TaskStatus(str, Enum):
    """Task execution status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_DECOMPOSITION = "needs_decomposition"  # SLM signals task is too complex


class TaskDispatch(BaseModel):
    """Dispatch message from orchestrator to SLM."""
    task_id: str = Field(..., description="Unique identifier for the task")
    objective: str = Field(..., description="Clear description of what needs to be done")
    scope: Dict[str, List[str]] = Field(
        ...,
        description="Files the SLM can edit vs. read-only files",
        example={"editable": ["src/main.py"], "readonly": ["tests/test_main.py"]}
    )
    acceptance_criteria: List[str] = Field(
        ...,
        description="How to verify success"
    )
    output_format: str = Field(
        ...,
        description="Expected format of the result"
    )
    context_ref: Optional[str] = Field(
        None,
        description="Reference to shared standing-context file"
    )


class SuggestedSubtask(BaseModel):
    """Suggested subtask when SLM requests decomposition."""
    objective: str = Field(..., description="What this subtask should accomplish")
    scope: Dict[str, List[str]] = Field(
        ...,
        description="Files for this subtask",
        example={"editable": ["src/models.py"], "readonly": ["tests/"]}
    )
    rationale: str = Field(..., description="Why this subtask is needed")
    requires: Optional[List[str]] = Field(
        None,
        description="Dependencies or shared interfaces needed"
    )
    estimated_complexity: Optional[str] = Field(
        None,
        description="Complexity estimate (low/medium/high)"
    )


class TaskReport(BaseModel):
    """Report from SLM back to orchestrator."""
    task_id: str = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Success or failure")
    diff: Optional[str] = Field(None, description="Code changes made")
    assumptions: List[str] = Field(
        default_factory=list,
        description="Any assumptions made during implementation"
    )
    self_check: Optional[str] = Field(
        None,
        description="SLM's self-assessment"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if task failed"
    )
    # Cooperative decomposition fields
    suggested_subtasks: Optional[List[SuggestedSubtask]] = Field(
        None,
        description="Subtasks suggested when status is needs_decomposition"
    )
    decomposition_reasoning: Optional[str] = Field(
        None,
        description="Why the SLM thinks this task needs decomposition"
    )


class TaskVerdict(BaseModel):
    """Verdict from orchestrator after verification."""
    task_id: str = Field(..., description="Task identifier")
    passed: bool = Field(..., description="Boolean indicating acceptance")
    failures: List[str] = Field(
        default_factory=list,
        description="List of issues found during verification"
    )
    action: str = Field(
        ...,
        description="Next action (accept/retry/escalate)"
    )


class TaskState(BaseModel):
    """Internal task state tracking."""
    task_id: str
    dispatch: TaskDispatch
    status: TaskStatus
    report: Optional[TaskReport] = None
    verdict: Optional[TaskVerdict] = None
    created_at: float
    updated_at: float
