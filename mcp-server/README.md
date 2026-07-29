# Foreman MCP Server

Python-based MCP server for the Foreman local agent orchestrator.

## Overview

This MCP server provides three core tools for orchestrating tasks with a local SLM:

1. **dispatch_task** - Send a task to the local SLM for execution
2. **check_status** - Check the status of a dispatched task
3. **get_report** - Retrieve the report for a completed task

## Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the server

```bash
# From the mcp-server directory
python main.py
```

### Tool Schemas

#### dispatch_task

Dispatches a task to the local SLM for execution.

**Input:**
```json
{
  "task_id": "optional-unique-id",
  "objective": "Clear description of what needs to be done",
  "scope": {
    "editable": ["src/file1.py", "src/file2.py"],
    "readonly": ["tests/test_file.py"]
  },
  "acceptance_criteria": [
    "All tests pass",
    "Code follows style guide"
  ],
  "output_format": "unified diff",
  "context_ref": "path/to/context.md"
}
```

**Output:**
- Task ID
- Confirmation that task was queued

#### check_status

Checks the current status of a task.

**Input:**
```json
{
  "task_id": "task-identifier"
}
```

**Output:**
- Current status (queued/running/completed/failed)
- Timestamps
- Report availability

#### get_report

Retrieves the full report for a completed task.

**Input:**
```json
{
  "task_id": "task-identifier"
}
```

**Output:**
- Task status
- Code diff
- Assumptions made by SLM
- Self-check from SLM
- Any errors

## Architecture

```
foreman/
├── __init__.py          — Package initialization
├── models.py            — Pydantic models for protocol messages
├── task_manager.py      — Task state management
└── server.py            — MCP server implementation
```

## Development Status

**Current Phase**: MVP - Basic task dispatch/status/report flow

The server currently:
- ✅ Accepts task dispatches
- ✅ Tracks task state
- ✅ Provides status checks
- ✅ Returns task reports

**TODO**:
- [ ] Integrate with serving layer (llama.cpp or Ollama+MLX)
- [ ] Implement actual SLM task execution
- [ ] Add parallel task dispatch support
- [ ] Add error handling and retry logic

## Protocol

The server implements the three-part Foreman protocol:

1. **Dispatch** - Orchestrator sends task spec with acceptance criteria
2. **Report** - SLM returns diff, assumptions, and self-check
3. **Verdict** - Orchestrator evaluates and decides (accept/retry/escalate)

See the [main README](../README.md) for full protocol details.
