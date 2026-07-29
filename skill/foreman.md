---
name: foreman
description: Orchestrate coding tasks to a local SLM with independent verification. Use for routine code writing tasks where you can define clear acceptance criteria and held-out tests.
---

# Foreman: Local Agent Orchestration Skill

## Purpose

Foreman allows you to delegate routine coding tasks to a fast, cheap local SLM while maintaining full accountability through independent verification. You write compact task specs, dispatch them to the local SLM, and independently verify results before accepting.

## Philosophy: Full Accountability

**You hold full responsibility for correctness.** If a delegated task is wrong, that's because you didn't verify it well enough — not because the SLM misbehaved. The SLM is doing its best on what it's told, not judging its own work.

## When to Use This Skill

**Use Foreman when:**
- Task is routine code writing (CRUD, boilerplate, tests, simple features)
- You can write clear acceptance criteria
- You can create a held-out test that would catch wrong implementations
- Task is feature/domain-slice granularity (not too small, not too large)
- Speed and cost matter more than creative problem-solving

**Don't use Foreman for:**
- Novel architectural decisions
- Complex debugging requiring deep investigation
- Tasks where you can't define clear acceptance criteria
- Sensitive code (auth, payments, crypto) unless you have strong verification
- Single-file trivial changes (just do it yourself)

## Workflow

### 1. Decomposition

Before delegating:
- Break request into feature/domain-slices
- Check for file overlap between slices
- Define shared interfaces upfront if multiple tasks will interact
- Only parallelize tasks with no file conflicts

### 2. Delegation Gate

For each task, ask:
- **Can I write a held-out test that would catch a wrong implementation?**
  - ✅ Yes → Proceed with delegation
  - ❌ No → Do it yourself or improve acceptance criteria

Risk scoring (computed, not hardcoded):
- High blast radius (changes many dependencies)
- Sensitive primitives (crypto, auth, secrets, payments)
- → Raises required verification bar

### 3. Dispatch

Use the `dispatch_task` MCP tool:

```json
{
  "task_id": "unique-id",
  "objective": "Clear, specific description of what needs to be done",
  "scope": {
    "editable": ["src/feature.py", "src/utils.py"],
    "readonly": ["tests/test_feature.py", "README.md"]
  },
  "acceptance_criteria": [
    "All existing tests pass",
    "New functionality matches specification",
    "Code follows project style guide",
    "No security vulnerabilities introduced"
  ],
  "output_format": "unified diff",
  "context_ref": "docs/standing-context.md"
}
```

**Key points:**
- Objective is specific and actionable
- Scope clearly separates editable vs. read-only files
- Acceptance criteria are verifiable (you can test them)
- Test files are read-only (SLM can't tamper)

### 4. Monitor

Use `check_status` to monitor progress:

```json
{
  "task_id": "unique-id"
}
```

### 5. Verify Independently

**Critical: Never trust the SLM's self-report.**

When you get the report via `get_report`:
1. Read the diff carefully
2. Run held-out tests (tests the SLM couldn't see or modify)
3. Check acceptance criteria independently
4. Look for edge cases the SLM might have missed
5. Verify no security issues introduced

### 6. Verdict

Based on verification:

**Accept:**
- All held-out tests pass
- All acceptance criteria met
- No security issues
- Code quality acceptable

**Retry:**
- Minor issues found
- Acceptance criteria can be clarified
- Try once with refined criteria

**Escalate:**
- Re-decompose into smaller sub-slices and retry once
- If that fails, you take over the task directly
- Only escalate to user if there's a genuine requirements contradiction

## Test Trust Model

**Two-tier testing:**

1. **Visible tests** - SLM can read and run these for fast iteration
   - Unit tests in readonly scope
   - Linting and type checking
   - Public integration tests

2. **Held-out tests** - Only you run these, gate final acceptance
   - Edge case tests
   - Security tests
   - Integration tests with sensitive components
   - Performance benchmarks

## Parallel Dispatch

For multiple independent tasks:

1. Run file-level overlap check
2. Tasks with shared files → sequence them
3. Tasks with no overlap → dispatch in parallel
4. Define shared interfaces upfront for dependent tasks

## Cooperative Decomposition (Hybrid Pattern)

When task complexity is uncertain, the SLM can signal it needs help by returning `status: "needs_decomposition"`.

### Pattern 1: Preemptive Parallel Dispatch

**Use when you can decompose upfront:**

1. Analyze the request and identify independent slices
2. Check file overlap between slices
3. For non-overlapping slices: dispatch in parallel
4. Define shared interfaces upfront for dependent slices
5. Verify all results independently

**Example:**
```
User: Add user management feature

You decompose:
- Task A: User model + migrations (models/user.py)
- Task B: Auth endpoints (routes/auth.py)
- Task C: User CRUD (routes/users.py)

No file overlap → dispatch all 3 in parallel
```

### Pattern 2: Cooperative Decomposition

**Use when complexity is uncertain:**

1. Dispatch the task to SLM
2. Monitor for `needs_decomposition` status
3. **Review the suggested breakdown** - SLM proposes subtasks
4. **Decide:**
   - ✅ Accept: Validate suggestions, define interfaces, dispatch subtasks
   - ⚠️ Modify: Refine the suggestions, then dispatch
   - ❌ Reject: Take over the task yourself
5. Verify all subtask results independently

**Example workflow:**

```json
// Initial dispatch
dispatch_task({
  "task_id": "user-auth",
  "objective": "Add full user authentication system",
  "scope": {
    "editable": ["routes/auth.py", "models/user.py", "middleware/"],
    "readonly": ["tests/"]
  },
  "acceptance_criteria": [
    "JWT token generation works",
    "Password hashing uses bcrypt",
    "All auth tests pass"
  ]
})

// SLM realizes this is too complex
report = get_report("user-auth")
// report.status == "needs_decomposition"
// report.suggested_subtasks = [
//   {
//     "objective": "Create User model with password hashing",
//     "scope": {"editable": ["models/user.py"]},
//     "rationale": "Foundation for auth system",
//     "estimated_complexity": "medium"
//   },
//   {
//     "objective": "Implement JWT token generation and validation",
//     "scope": {"editable": ["utils/jwt.py"]},
//     "rationale": "Separate concern from routes",
//     "requires": ["User model interface"],
//     "estimated_complexity": "medium"
//   },
//   {
//     "objective": "Add /auth/register and /auth/login endpoints",
//     "scope": {"editable": ["routes/auth.py"]},
//     "rationale": "Wire up auth flow",
//     "requires": ["User model", "JWT utilities"],
//     "estimated_complexity": "low"
//   }
// ]
// report.decomposition_reasoning = "Task touches 3 concerns with complex dependencies"

// You review and decide
if (validate_decomposition(report.suggested_subtasks)) {
  // Define shared interfaces
  interfaces = {
    "User model": "class User with .hash_password() and .verify_password()",
    "JWT utilities": "generate_token(user_id) and verify_token(token)"
  }

  // Dispatch subtasks with interface contracts
  for (subtask in report.suggested_subtasks) {
    dispatch_task({
      "task_id": `user-auth-${subtask.objective}`,
      "objective": subtask.objective,
      "scope": subtask.scope,
      "context_ref": interfaces,  // Shared interfaces
      "acceptance_criteria": [...]
    })
  }

  // Verify each independently
  for (subtask_id in subtask_ids) {
    result = get_report(subtask_id)
    run_held_out_tests(result.diff)
  }
}
```

**Critical rules for cooperative decomposition:**

1. **Never auto-accept suggestions** - Always review the breakdown
2. **Define interfaces explicitly** - Don't let subtasks guess at contracts
3. **Verify independently** - Each subtask gets held-out tests
4. **You stay accountable** - If subtasks fail, you didn't decompose well enough

### When to Use Which Pattern

| Pattern | Use When | Don't Use When |
|---------|----------|----------------|
| **Preemptive** | Clear independent slices, known complexity | Uncertain what's involved |
| **Cooperative** | Complex task, unclear scope, many dependencies | Simple task you can decompose easily |

**Hybrid approach:** Start with Preemptive. If a slice is harder than expected, that slice can request Cooperative decomposition.

## Merge Strategy

**Hybrid batching:**
- Low-risk, low fan-in diffs → batch-apply + single integration test
- High-risk diffs → apply and verify individually
- On batch failure → bisect by binary search, not linear replay

## Example Session

```
User: Add CRUD endpoints for the User model

You:
1. Decomposition
   - Task 1: Create User model and database migration
   - Task 2: Add POST /users endpoint
   - Task 3: Add GET /users/:id endpoint
   - Task 4: Add PUT /users/:id endpoint
   - Task 5: Add DELETE /users/:id endpoint

2. Check file overlap
   - All tasks touch routes/users.py
   - → Sequence them or combine into one larger task

3. Delegation gate
   - Can write held-out tests? Yes (integration tests, auth tests)
   - Risk score: Medium (auth-adjacent, but not auth itself)
   - → Proceed with elevated verification bar

4. Dispatch combined task
   [dispatch_task with clear spec]

5. Monitor
   [check_status until complete]

6. Verify
   - Review diff for security issues
   - Run held-out integration tests
   - Check auth boundaries
   - Verify input validation

7. Verdict
   - Issue: Missing input validation on email field
   - Action: Retry with refined acceptance criteria

8. Re-dispatch
   [dispatch_task with explicit validation requirement]

9. Re-verify
   - All tests pass
   - Security checks pass
   - Input validation present
   - Action: Accept
```

## Economics Tracking

Track these metrics for each delegated task:
- Tokens used (your spec + verification vs. doing it yourself)
- Time saved (wall clock)
- Success rate (accept vs. retry vs. escalate)

Compare against baseline: you doing it directly.

## Current Limitations (MVP)

- No automatic re-decomposition on failure (manual for now)
- No risk score computation (use judgment)
- No batch merge (apply diffs individually)
- Manual serving layer startup required for llama.cpp

## MCP Server Connection

The Foreman skill requires the Foreman MCP server to be running. See `mcp-server/README.md` for setup instructions.

The skill uses three MCP tools:
- `dispatch_task` - Send work to local SLM
- `check_status` - Monitor task progress
- `get_report` - Get results for verification

## Remember

- **You are accountable, not the SLM**
- **Never trust self-reports, always verify independently**
- **Only delegate what you can verify**
- **When in doubt, do it yourself**
