# Foreman

**Local agent orchestrator**

> **Name rationale:** a foreman assigns work, checks it, and is the one accountable if it's wrong — which is exactly the escalation/accountability philosophy this project is built on, not just a description of what it does.

## The Problem

Large language models like Claude are powerful but expensive for routine coding tasks. Small language models (SLMs) running locally are cheap and fast but less reliable. Foreman bridges this gap: Claude acts as an orchestrator, writing compact task specs and dispatching them to a local SLM that does the actual code writing, while independently verifying every result.

## Philosophy

**The orchestrator holds full accountability for correctness.** If a delegated task turns out wrong, that's because Claude didn't verify it well enough — not because the SLM misbehaved. The SLM is an agent doing its best on what it's told, not a judge of its own work.

## Protocol

Three-part JSON exchange between orchestrator and SLM:

1. **Dispatch** — Claude sends:
   - `task_id`: Unique identifier
   - `objective`: Clear description of what needs to be done
   - `scope`: Which files are editable vs. read-only
   - `acceptance_criteria`: How to verify success
   - `output_format`: Expected format of the result
   - `context_ref`: Reference to shared standing-context file

2. **Report** — SLM returns:
   - `status`: Success or failure
   - `diff`: Code changes made
   - `assumptions`: Any assumptions made during implementation
   - `self_check`: SLM's self-assessment

3. **Verdict** — Claude evaluates:
   - `passed`: Boolean indicating acceptance
   - `failures`: List of issues found during verification
   - `action`: Next action (accept/retry/escalate)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Claude (Orchestrator)                 │
│  - Writes task specs                                     │
│  - Independently verifies results                        │
│  - Holds full accountability                             │
└─────────────────┬───────────────────────────────────────┘
                  │ MCP Protocol
                  │ (dispatch_task, check_status, get_report)
                  ▼
┌─────────────────────────────────────────────────────────┐
│                    MCP Server (Python)                   │
│  - Receives task dispatches                              │
│  - Manages task queue and state                          │
│  - Interfaces with serving layer                         │
└─────────────────┬───────────────────────────────────────┘
                  │
                  │ llama.cpp / Ollama+MLX
                  ▼
┌─────────────────────────────────────────────────────────┐
│          Local SLM (Devstral Small 24B)                  │
│  - Executes code writing tasks                           │
│  - Runs on Apple Silicon with Metal GPU                  │
│  - Fast, cheap, local inference                          │
└─────────────────────────────────────────────────────────┘
```

## Key Design Decisions

| Area | Decision |
|------|----------|
| **Test trust model** | Two-tier: visible tests the SLM can run, plus held-out tests only the orchestrator runs |
| **Delegation gate** | Only delegate if Claude can write a held-out test that would catch a wrong implementation |
| **Model choice** | Devstral Small 24B (bred for agentic work, spec-following) |
| **Serving layer** | llama.cpp with custom admission control, or Ollama+MLX fallback (native, non-containerized) |
| **Tool-call mechanism** | MCP server wrapping the llama.cpp/Ollama endpoint for async parallel dispatch |
| **Escalation path** | Re-decompose → Claude takes over → escalate to user (only for genuine requirements gaps) |
| **Packaging** | Claude Skill first, validate economics before building a full shipped tool |

## Repository Structure

```
foreman/
├── README.md              — this file
├── LICENSE
├── .gitignore             — excludes model weights, local .env, served model cache
├── mcp-server/            — the dispatch_task / check_status / get_report server
├── skill/                 — the Claude Skill definition that calls it
└── docs/
    └── decisions.md       — versioned decision log
```

## Getting Started

### Prerequisites

- Python 3.9+
- Apple Silicon Mac with Metal GPU support
- llama.cpp or Ollama installed
- Devstral Small 24B model weights

### Installation

```bash
# Clone the repository
git clone https://github.com/Aryan01101/foreman.git
cd foreman

# Install MCP server dependencies
cd mcp-server
pip install -r requirements.txt

# Configure the skill in Claude
# (Instructions coming soon)
```

### Usage

```python
# Example: Using Foreman via Claude
# Claude will automatically dispatch tasks to the local SLM
# and verify results independently
```

## Development Status

**Current Phase**: Initial implementation (MVP)

This is an experimental project to validate the economics of orchestrated local SLM delegation versus solo Claude or native subagents. The focus is on:

- Building the core MCP server with dispatch/status/report tools
- Integrating the serving layer (llama.cpp or Ollama+MLX)
- Packaging as a Claude Skill
- Tracking token/time economics on real tasks

## North Star Vision

Longer-term: an OS-agnostic, full-screen interface where a master orchestrator commands genuinely autonomous agents working in parallel, with the human role shifting to observing — watching diffs, commands, and tests pass in real time rather than writing code directly.

This skill is step one toward that vision.

## License

See [LICENSE](LICENSE) file for details.

## Contributing

This is currently an experimental validation project. Once the economics and viability are proven, contributions will be welcome.
