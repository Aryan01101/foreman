# Design Decisions

This document tracks the key architectural and implementation decisions for Foreman, versioned alongside the code.

## Decision Log

| Area | Decision | Rationale | Date |
|------|----------|-----------|------|
| **Test trust model** | Two-tier: visible tests the SLM can run itself for fast iteration, plus held-out tests only the orchestrator runs, which gate final acceptance. Test files live in read-only scope so the SLM can't tamper. | Balances SLM autonomy with orchestrator accountability. Held-out tests prevent gaming and ensure independent verification. | 2026-07-28 |
| **Capacity handling** | No LLM-judged memory monitoring. Capacity limits are enforced deterministically at the serving layer (admission control); orchestrator only gets aggregate state for scheduling. | Avoids unreliable LLM-based capacity estimation. Deterministic enforcement at serving layer is more predictable. | 2026-07-28 |
| **Decomposition unit** | Dispatch at feature/domain-slice granularity. Run a file-level overlap check before parallelizing — slices sharing files get sequenced instead. Claude defines shared interfaces up front rather than letting two SLMs guess at a contract. | Prevents merge conflicts and ensures coherent interfaces when tasks span multiple files. | 2026-07-28 |
| **Delegation gate** | Verifiability-first: only delegate if Claude can write a held-out test that would actually catch a wrong implementation. Rejected a static category exclusion list (e.g. hardcoded "auth/payments" list) as unmaintainable. Instead, a computed risk score (dependency blast radius, sensitive primitives like crypto/auth/secrets) raises the required verification bar for risky tasks. | Ensures all delegated tasks can be independently verified. Risk scoring adapts to codebase evolution. | 2026-07-28 |
| **Model choice** | Keep the model layer modular/swappable, not hard-locked. **Default: Devstral Small 24B** — chosen over Qwen3-Coder because it's bred for multi-step, spec-following agentic work, which matters more here than raw benchmark score given the verification layer is already the safety net. | Prioritizes instruction-following and agentic capabilities over pure coding benchmarks. Modular design allows experimentation. | 2026-07-28 |
| **Serving layer** | Build/test on own Apple Silicon Mac. Try a custom concurrency/admission-control layer on llama.cpp first. If that's too much work, fall back to **native (non-containerized)** Ollama + MLX. Containerizing Ollama was ruled out — Docker on macOS can't pass through the Metal GPU, forcing CPU-only inference. | Metal GPU access is critical for performance. Custom admission control on llama.cpp offers maximum control but has fallback. | 2026-07-28 |
| **Tool-call mechanism** | A thin local MCP server wrapping the llama.cpp/Ollama endpoint (`dispatch_task` / `check_status` / `get_report` as typed tools) — not a bash/CLI wrapper, to support async parallel dispatch rather than blocking calls. | MCP protocol enables typed, async tool calls. Parallel dispatch is essential for performance. | 2026-07-28 |
| **Data locality** | Only SLM inference and MCP server compute stay local. Claude itself (writing specs, reviewing diffs, running held-out tests) is inherently cloud — so this is local *compute*, not local *data*. Confirmed fine: the goal was cost/speed, not data locality. | Clarifies scope: optimization is about compute economics, not data privacy. | 2026-07-28 |
| **Merge strategy** | Hybrid batching: reuse the delegation risk score to route low-risk/low-fan-in diffs into a batch-apply + single integration test pass; higher-risk diffs get applied and reverified individually. On batch failure, bisect by binary search rather than linear replay. | Balances efficiency (batching low-risk changes) with safety (individual verification for risky changes). | 2026-07-28 |
| **Escalation path** | Staged: re-decompose the failing task into smaller sub-slices and retry once → if that also fails, Claude takes the task over directly → escalate to the user only if re-decomposition surfaces a genuine contradiction in the acceptance criteria itself (a requirements gap, not a capability failure). | Maximizes automation while preserving accountability. User escalation only for genuine requirements issues. | 2026-07-28 |
| **Packaging** | Build as a **Claude Skill** first, not a shipped tool. The MCP server is already the real mechanism — the skill is just the thin "how to use it well" layer. Validate the idea and its economics before investing in installers/multi-hardware support for a fuller product. | Validates viability before significant product investment. Skill is lightweight wrapper around MCP server. | 2026-07-28 |
| **MCP Server Language** | Python with official MCP SDK | Python has official MCP SDK support and good ML/AI tooling integration. | 2026-07-28 |
| **Initial Implementation Scope** | MVP - basic dispatch/report/verdict flow only | Validate core concept and economics before building full feature set. | 2026-07-28 |

## Open Questions

These remain to be validated through implementation and testing:

1. **Token/time economics** — Does this system actually save tokens/time vs. solo Claude or native subagents?
2. **llama.cpp admission control complexity** — How much custom work is really needed before falling back to Ollama+MLX?
3. **Real-world merge/escalation behavior** — How do the merge and escalation strategies perform on actual multi-file tasks?
4. **Risk scoring effectiveness** — Does the computed risk score accurately identify tasks that need higher verification bars?
5. **Parallel dispatch performance** — What's the practical speedup from parallel task execution?

## Future Considerations

Items deferred for later phases:

- **Cross-platform support** — Currently Mac-only; expand to Linux/Windows if economics prove out
- **Advanced merge strategies** — Batch-apply with bisection on failure
- **Full escalation workflow** — Re-decomposition and automatic orchestrator takeover
- **Risk scoring system** — Dependency blast radius and sensitive primitive detection
- **Shared interface definition** — Automated interface contract generation for parallel tasks
- **Production packaging** — Installers, multi-hardware support, distribution

## Changelog

### 2026-07-28 - Initial decisions
- All initial design decisions locked in
- MVP scope defined
- MCP server language chosen (Python)
- Repository structure established
