# Foreman Claude Skill

This skill enables Claude to orchestrate coding tasks to a local SLM while maintaining full accountability through independent verification.

## Installation

### 1. Set up the MCP Server

First, ensure the Foreman MCP server is installed and running. See [mcp-server/README.md](../mcp-server/README.md) for details.

```bash
# Install MCP server dependencies
cd mcp-server
pip install -r requirements.txt

# Start the server (in a separate terminal)
python main.py
```

### 2. Configure Claude to use the MCP Server

Add the Foreman MCP server to your Claude configuration:

**For Claude Desktop:**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "foreman": {
      "command": "python",
      "args": ["/path/to/foreman/mcp-server/main.py"]
    }
  }
}
```

**For Claude Code:**

Edit `~/.claude/mcp_settings.json`:

```json
{
  "mcpServers": {
    "foreman": {
      "command": "python",
      "args": ["/path/to/foreman/mcp-server/main.py"],
      "env": {
        "FOREMAN_BACKEND": "auto",
        "FOREMAN_MODEL_NAME": "devstral:latest"
      }
    }
  }
}
```

### 3. Install the Skill

**Option A: Copy to Claude skills directory**

```bash
# Copy skill definition to Claude skills directory
cp skill/foreman.md ~/.claude/skills/foreman.md
cp skill/skill.json ~/.claude/skills/foreman.json
```

**Option B: Symlink for development**

```bash
# Symlink for easier updates during development
ln -s /path/to/foreman/skill/foreman.md ~/.claude/skills/foreman.md
ln -s /path/to/foreman/skill/skill.json ~/.claude/skills/foreman.json
```

### 4. Verify Installation

Start a Claude conversation and ask:

```
Do you have access to the Foreman skill?
```

Claude should confirm access to the skill and list the available MCP tools.

## Usage

### Triggering the Skill

The skill can be triggered by:
- Mentioning "delegate" or "foreman" in your request
- Explicitly asking Claude to use Foreman
- Describing a routine coding task that fits Foreman's criteria

### Example Prompts

**Simple delegation:**
```
Use Foreman to add CRUD endpoints for the User model
```

**Explicit workflow:**
```
I have a routine task: implement pagination for the posts list.
Can you delegate this to the local SLM using Foreman?
```

**Parallel tasks:**
```
These three features are independent - can you dispatch them
in parallel using Foreman?
1. Add email validation
2. Implement rate limiting
3. Add request logging
```

## Configuration

### Environment Variables

- `FOREMAN_BACKEND`: Backend type ("auto", "llamacpp", "ollama")
- `FOREMAN_MODEL_PATH`: Path to GGUF model for llama.cpp
- `FOREMAN_MODEL_NAME`: Model name for Ollama (default: "devstral:latest")

### Serving Backend Setup

**Ollama (recommended for MVP):**

```bash
# Install Ollama
brew install ollama

# Start Ollama service
ollama serve

# Pull Devstral model
ollama pull devstral
```

**llama.cpp (advanced):**

```bash
# Download model
wget https://huggingface.co/model/devstral-small-24b.gguf

# Start server
./llama-server -m devstral-small-24b.gguf -c 4096 --port 8080 -ngl -1

# Set environment variable
export FOREMAN_MODEL_PATH=/path/to/devstral-small-24b.gguf
export FOREMAN_BACKEND=llamacpp
```

## Skill Philosophy

Foreman implements these core principles:

1. **Full Accountability**: The orchestrator (Claude) holds full responsibility for correctness
2. **Independent Verification**: Never trust the SLM's self-report; always verify independently
3. **Verifiability Gate**: Only delegate tasks where you can write held-out tests
4. **Risk-Aware**: Higher-risk tasks require stronger verification

See [foreman.md](foreman.md) for complete workflow documentation.

## Troubleshooting

### Skill not appearing

- Verify skill files are in `~/.claude/skills/`
- Restart Claude
- Check file permissions

### MCP server not connecting

- Verify server is running: `ps aux | grep foreman`
- Check MCP configuration in Claude settings
- Look for errors in server logs

### Tasks failing

- Verify serving backend is running (Ollama or llama.cpp)
- Check backend URL/port configuration
- Review task acceptance criteria (are they clear and testable?)

### Model not found

```bash
# For Ollama
ollama list  # Check available models
ollama pull devstral  # Pull if missing

# For llama.cpp
# Verify FOREMAN_MODEL_PATH points to valid .gguf file
```

## Development

To modify the skill:

1. Edit `foreman.md` with your changes
2. If symlinked, changes are immediately available
3. If copied, run: `cp skill/foreman.md ~/.claude/skills/foreman.md`
4. Restart Claude or start a new conversation

## License

MIT License - see [LICENSE](../LICENSE) for details.
