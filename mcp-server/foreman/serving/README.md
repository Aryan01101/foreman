# Serving Layer

Local SLM inference backends for Foreman.

## Backends

### Ollama + MLX (Fallback)
- Native, non-containerized Ollama
- MLX acceleration on Apple Silicon
- Automatic Metal GPU passthrough
- Simple setup and configuration

### llama.cpp (Primary)
- Custom admission control for concurrency
- Direct Metal GPU access
- Maximum control over inference
- Requires manual server management for MVP

## Architecture

```
ServingBackend (ABC)
├── OllamaBackend
│   ├── HTTP API client
│   ├── Semaphore-based admission control
│   └── Automatic model pulling
└── LlamaCppBackend
    ├── Server process management (TODO)
    ├── HTTP API client
    └── Custom admission control
```

## Usage

### Auto-detection

```python
from foreman.serving import create_backend

# Auto-detect available backend (tries llama.cpp first, then Ollama)
backend = await create_backend()
```

### Explicit backend selection

```python
# Use Ollama
backend = await create_backend(
    backend_type="ollama",
    model_name="devstral:latest",
    max_concurrent=4
)

# Use llama.cpp
backend = await create_backend(
    backend_type="llamacpp",
    model_path="/path/to/model.gguf",
    server_port=8080,
    max_concurrent=4,
    n_gpu_layers=-1  # Use all GPU layers
)
```

### Environment variables

- `FOREMAN_BACKEND`: Backend type ("auto", "llamacpp", "ollama")
- `FOREMAN_MODEL_PATH`: Path to GGUF model for llama.cpp
- `FOREMAN_MODEL_NAME`: Model name for Ollama (default: "devstral:latest")

## Capacity Management

Both backends implement deterministic admission control using semaphores:

```python
capacity = await backend.get_capacity()
# {
#   "available_slots": 2,
#   "total_slots": 4,
#   "in_use": 2
# }
```

## Generation

```python
response = await backend.generate(
    prompt="Write a function that...",
    max_tokens=2048,
    temperature=0.7
)
```

## MVP Status

**Ollama Backend**: ✅ Complete
- HTTP API integration
- Model auto-pull
- Capacity tracking
- Error handling

**llama.cpp Backend**: ⚠️ Partial
- API client complete
- Server management requires manual start
- TODO: Automatic server process management

## Next Steps

1. Automatic llama.cpp server process management
2. Better error recovery and retry logic
3. Streaming support for long-running tasks
4. Model warmup and preloading
5. Advanced admission control strategies
