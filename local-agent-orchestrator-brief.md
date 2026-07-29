# Foreman

*Local agent orchestrator — project brief*

> **Name rationale:** a foreman assigns work, checks it, and is the one
> accountable if it's wrong — which is exactly the escalation/accountability
> philosophy this project is built on, not just a description of what it does.

## The idea

Claude acts as an orchestrator: it writes compact task specs and dispatches them
to a cheap local small language model (SLM) that does the actual code writing.
Claude never trusts the SLM's self-report — it independently verifies every
result. Philosophy: **the orchestrator holds full accountability for
correctness.** If a delegated task turns out wrong, that's because Claude
didn't verify it well enough — not because the SLM misbehaved. The SLM is an
agent doing its best on what it's told, not a judge of its own work.

Simplified down to essentially one tool call:
`write_code(spec, acceptance_criteria) → diff, verify, accept/retry`

## Protocol

Three-part JSON exchange between orchestrator and SLM:

1. **Dispatch** — `task_id`, `objective`, `scope` (editable / read-only files),
   `acceptance_criteria`, `output_format`, `context_ref` (points to a shared
   standing-context file so per-task payloads stay small)
2. **Report** — `status`, `diff`, `assumptions`, `self_check`
3. **Verdict** — `passed`, `failures`, `action`

## Decisions locked in

| Area | Decision |
|---|---|
| **Test trust model** | Two-tier: visible tests the SLM can run itself for fast iteration, plus held-out tests only the orchestrator runs, which gate final acceptance. Test files live in read-only scope so the SLM can't tamper. |
| **Capacity handling** | No LLM-judged memory monitoring. Capacity limits are enforced deterministically at the serving layer (admission control); orchestrator only gets aggregate state for scheduling. |
| **Decomposition unit** | Dispatch at feature/domain-slice granularity. Run a file-level overlap check before parallelizing — slices sharing files get sequenced instead. Claude defines shared interfaces up front rather than letting two SLMs guess at a contract. |
| **Delegation gate** | Verifiability-first: only delegate if Claude can write a held-out test that would actually catch a wrong implementation. Rejected a static category exclusion list (e.g. hardcoded "auth/payments" list) as unmaintainable. Instead, a computed risk score (dependency blast radius, sensitive primitives like crypto/auth/secrets) raises the required verification bar for risky tasks. |
| **Model choice** | Keep the model layer modular/swappable, not hard-locked. **Default: Devstral Small 24B** — chosen over Qwen3-Coder because it's bred for multi-step, spec-following agentic work, which matters more here than raw benchmark score given the verification layer is already the safety net. |
| **Serving layer** | Build/test on own Apple Silicon Mac. Try a custom concurrency/admission-control layer on llama.cpp first. If that's too much work, fall back to **native (non-containerized)** Ollama + MLX. Containerizing Ollama was ruled out — Docker on macOS can't pass through the Metal GPU, forcing CPU-only inference. |
| **Tool-call mechanism** | A thin local MCP server wrapping the llama.cpp/Ollama endpoint (`dispatch_task` / `check_status` / `get_report` as typed tools) — not a bash/CLI wrapper, to support async parallel dispatch rather than blocking calls. |
| **Data locality** | Only SLM inference and MCP server compute stay local. Claude itself (writing specs, reviewing diffs, running held-out tests) is inherently cloud — so this is local *compute*, not local *data*. Confirmed fine: the goal was cost/speed, not data locality. |
| **Merge strategy** | Hybrid batching: reuse the delegation risk score to route low-risk/low-fan-in diffs into a batch-apply + single integration test pass; higher-risk diffs get applied and reverified individually. On batch failure, bisect by binary search rather than linear replay. |
| **Escalation path** | Staged: re-decompose the failing task into smaller sub-slices and retry once → if that also fails, Claude takes the task over directly → escalate to the user only if re-decomposition surfaces a genuine contradiction in the acceptance criteria itself (a requirements gap, not a capability failure). |
| **Packaging** | Build as a **Claude Skill** first, not a shipped tool. The MCP server is already the real mechanism — the skill is just the thin "how to use it well" layer. Validate the idea and its economics before investing in installers/multi-hardware support for a fuller product. |

## Repository

```
foreman/
├── README.md          — pulled from this brief: problem, protocol, architecture
├── LICENSE
├── .gitignore          — excludes model weights, local .env, served model cache
├── mcp-server/          — the dispatch_task / check_status / get_report server
├── skill/               — the Claude Skill definition that calls it
└── docs/
    └── decisions.md     — the decisions table above, versioned alongside the code
```

## Open / still to validate

- Token/time economics of this system vs. solo Claude, or Claude Code's native
  subagents — the thing that actually decides whether this is worth
  productizing further
- How much custom work the llama.cpp admission-control layer really needs
  before deciding whether to fall back to Ollama+MLX
- Real-world behavior of the merge and escalation strategies once tested on
  actual multi-file tasks
- **Which language to build the MCP server in** — Python has an official MCP
  SDK; TypeScript/Node is the other common choice and what most example MCP
  servers are written in. Next real fork once the repo exists.

## Next steps

1. Create the `foreman` git repo with the structure above
2. Decide MCP server language (Python vs. TypeScript/Node)
3. Build the MCP server + llama.cpp (or Ollama+MLX fallback) serving layer on
   own machine
4. Package the delegation logic as a Claude Skill
5. Run it on real tasks, track token/time economics honestly against solo
   Claude / native subagents
6. Only then: decide whether a fuller cross-platform shipped tool is worth
   building

## North star (not a near-term goal)

Longer-term vision: an OS-agnostic, full-screen interface where a master
orchestrator commands genuinely autonomous agents working in parallel, with
the human role shifting to observing — watching diffs, commands, and tests
pass in real time rather than writing code directly. This skill is step one
toward that, not a detour from it.
