# Foreman Quickstart Guide

Get Foreman running locally in 5 minutes and see the hybrid orchestration pattern in action.

## Prerequisites

- **Python 3.9+** (for MCP server)
- **Ollama** OR **llama.cpp** (for local SLM)
- **Claude Code** (to use the skill)

---

## Step 1: Install Ollama (Recommended for MVP)

```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve
```

In a separate terminal:

```bash
# Pull Devstral Small 24B model (recommended)
ollama pull devstral

# Alternative: Qwen 2.5 Coder (also good)
ollama pull qwen2.5-coder:14b
```

**Verify it's working:**
```bash
ollama list
# Should show: devstral:latest
```

---

## Step 2: Set Up the MCP Server

```bash
# Clone the repo (if you haven't already)
cd /path/to/foreman

# Install Python dependencies
cd mcp-server
pip install -r requirements.txt

# Test the server starts
python main.py
```

**Expected output:**
```
Foreman MCP Server v0.1.0
Starting with Ollama backend...
✓ Connected to Ollama at http://localhost:11434
✓ Model: devstral:latest
Server ready on stdio
```

Press `Ctrl+C` to stop (we'll configure it properly next).

---

## Step 3: Configure Claude Code

### Option A: Global MCP Configuration

Edit `~/.claude/mcp_settings.json`:

```json
{
  "mcpServers": {
    "foreman": {
      "command": "python",
      "args": ["/absolute/path/to/foreman/mcp-server/main.py"],
      "env": {
        "FOREMAN_BACKEND": "auto",
        "FOREMAN_MODEL_NAME": "devstral:latest"
      }
    }
  }
}
```

**⚠️ Important:** Replace `/absolute/path/to/foreman` with your actual path.

### Option B: Project-Specific Configuration

Create `.claude/settings.local.json` in your project:

```json
{
  "mcpServers": {
    "foreman": {
      "command": "python",
      "args": ["/absolute/path/to/foreman/mcp-server/main.py"],
      "env": {
        "FOREMAN_BACKEND": "auto",
        "FOREMAN_MODEL_NAME": "devstral:latest"
      }
    }
  }
}
```

---

## Step 4: Install the Foreman Skill

```bash
# Create Claude skills directory if it doesn't exist
mkdir -p ~/.claude/skills

# Symlink the skill (for easy updates during development)
ln -sf /absolute/path/to/foreman/skill/foreman.md ~/.claude/skills/foreman.md
ln -sf /absolute/path/to/foreman/skill/skill.json ~/.claude/skills/foreman.json

# OR copy the files:
cp /path/to/foreman/skill/foreman.md ~/.claude/skills/foreman.md
cp /path/to/foreman/skill/skill.json ~/.claude/skills/foreman.json
```

---

## Step 5: Verify Installation

Start a new Claude Code conversation:

```
Do you have access to the Foreman skill and MCP tools?
```

**Expected response:**
```
Yes, I have access to:

1. Foreman skill - For orchestrating tasks to local SLM
2. MCP tools:
   - dispatch_task - Send work to local SLM
   - check_status - Monitor task progress
   - get_report - Get results for verification

The skill includes both Pattern 1 (Preemptive Parallel Dispatch)
and Pattern 2 (Cooperative Decomposition) workflows.
```

---

## Step 6: Test the Hybrid Pattern

Try this test case to see cooperative decomposition in action:

```
Use Foreman to add a simple user authentication system.

I want to see the cooperative decomposition pattern where the SLM
might signal needs_decomposition if the task is complex.

Just show me how you would approach this, don't actually execute yet.
```

**What to look for:**

Claude should:
1. Recognize this might be complex
2. Explain it would dispatch the task
3. Describe monitoring for `needs_decomposition` status
4. Show how it would review suggested subtasks
5. Explain defining shared interfaces
6. Describe independent verification

---

## Step 7: Run a Real Task (Optional)

Once you're comfortable, try a real task:

```
Use Foreman to add input validation to the User model in models/user.py.

Requirements:
- Email must be valid format
- Password must be 8+ characters
- Username must be alphanumeric

Add validation methods and update tests.
```

Watch how Claude:
1. Checks if it can write held-out tests (yes)
2. Dispatches to the SLM
3. Gets the report back
4. Verifies independently
5. Accepts or retries

---

## Troubleshooting

### "MCP server not connecting"

```bash
# Check Ollama is running
ollama list

# Test MCP server manually
cd mcp-server
python main.py

# Look for connection success message
```

### "Skill not appearing"

```bash
# Verify files exist
ls -la ~/.claude/skills/foreman*

# Check permissions
chmod 644 ~/.claude/skills/foreman.md
chmod 644 ~/.claude/skills/foreman.json

# Restart Claude Code
```

### "Model not found"

```bash
# List available models
ollama list

# Pull if missing
ollama pull devstral

# Or try alternative:
ollama pull qwen2.5-coder:14b
```

### "Task execution fails"

Check the server logs - the MCP server outputs to stderr/stdout. Common issues:

1. **Model too large for memory** - Try smaller model or reduce context
2. **Ollama not responding** - Restart `ollama serve`
3. **Invalid task spec** - Check acceptance criteria are clear

---

## Configuration Options

### Environment Variables

Create `.env` in `mcp-server/`:

```bash
# Backend selection (auto tries llama.cpp then falls back to Ollama)
FOREMAN_BACKEND=auto  # or "ollama" or "llamacpp"

# Model configuration
FOREMAN_MODEL_NAME=devstral:latest
FOREMAN_OLLAMA_URL=http://localhost:11434

# For llama.cpp (advanced)
FOREMAN_LLAMACPP_URL=http://localhost:8080
FOREMAN_MODEL_PATH=/path/to/model.gguf

# Capacity management
FOREMAN_MAX_WORKERS=3  # Parallel task limit
```

### Skill Trigger Keywords

The skill auto-triggers on these keywords:
- "delegate"
- "dispatch task"
- "local slm"
- "foreman"
- "routine task"
- "parallelize"

Or explicitly: `"Use Foreman to..."`

---

## Next Steps

1. **Try Pattern 1** - Give Claude a task with clear independent slices
2. **Try Pattern 2** - Give a complex task and watch cooperative decomposition
3. **Track economics** - Note token usage and time saved
4. **Iterate** - Adjust acceptance criteria and verification based on results

---

## Learning Opportunities

If something doesn't work as expected, **that's valuable data**:

1. **SLM makes mistakes** → Are your acceptance criteria clear enough?
2. **Verification catches issues** → Good! The accountability model works
3. **Decomposition suggestions are wrong** → SLM needs better context
4. **Tasks take longer than doing it yourself** → Maybe the task isn't routine enough

**Remember the philosophy:** You hold full accountability. If delegation fails, it's a learning signal about what can/can't be delegated effectively.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│ Foreman Skill (foreman.md)                  │
│ - Pattern 1: Preemptive Parallel            │
│ - Pattern 2: Cooperative Decomposition      │
└──────────────────┬──────────────────────────┘
                   ↓ guides Claude
┌─────────────────────────────────────────────┐
│ Claude Code (You)                            │
│ - Makes all decisions                       │
│ - Holds full accountability                 │
│ - Verifies independently                    │
└──────────────────┬──────────────────────────┘
                   ↓ uses MCP tools
┌─────────────────────────────────────────────┐
│ Foreman MCP Server (Python)                 │
│ - dispatch_task, check_status, get_report   │
│ - Task queue management                     │
│ - Worker pool coordination                  │
└──────────────────┬──────────────────────────┘
                   ↓ executes on
┌─────────────────────────────────────────────┐
│ Ollama / llama.cpp                          │
│ - Devstral Small 24B (or Qwen 2.5 Coder)   │
│ - Metal GPU acceleration (macOS)            │
│ - Fast, cheap inference                     │
└─────────────────────────────────────────────┘
```

---

## Ready to Test!

You're all set. Start a Claude Code conversation and say:

```
Let's test Foreman! I want to add a simple feature to [your project].
```

Watch the hybrid orchestration pattern in action! 🚀
