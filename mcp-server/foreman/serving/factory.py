"""Factory for creating serving backends."""

import logging
import os
from typing import Optional

from .base import ServingBackend
from .ollama_backend import OllamaBackend
from .llamacpp_backend import LlamaCppBackend

logger = logging.getLogger(__name__)


async def create_backend(
    backend_type: Optional[str] = None,
    **kwargs
) -> Optional[ServingBackend]:
    """
    Create and initialize a serving backend.

    Strategy:
    1. Try llama.cpp first if requested or auto-detecting
    2. Fall back to Ollama + MLX if llama.cpp fails
    3. Return None if all backends fail

    Args:
        backend_type: Backend type ("llamacpp", "ollama", or None for auto)
        **kwargs: Backend-specific configuration

    Returns:
        Optional[ServingBackend]: Initialized backend or None
    """
    # Auto-detect or use specified backend
    if backend_type is None:
        backend_type = os.getenv("FOREMAN_BACKEND", "auto")

    backends_to_try = []

    if backend_type == "auto":
        # Try llama.cpp first, then Ollama
        backends_to_try = ["llamacpp", "ollama"]
    elif backend_type in ["llamacpp", "ollama"]:
        backends_to_try = [backend_type]
    else:
        logger.error(f"Unknown backend type: {backend_type}")
        return None

    for backend_name in backends_to_try:
        try:
            logger.info(f"Attempting to initialize {backend_name} backend...")

            if backend_name == "llamacpp":
                backend = LlamaCppBackend(
                    model_path=kwargs.get("model_path", os.getenv("FOREMAN_MODEL_PATH", "")),
                    server_port=kwargs.get("server_port", 8080),
                    max_concurrent=kwargs.get("max_concurrent", 4),
                    n_ctx=kwargs.get("n_ctx", 4096),
                    n_gpu_layers=kwargs.get("n_gpu_layers", -1)
                )
            elif backend_name == "ollama":
                backend = OllamaBackend(
                    model_name=kwargs.get("model_name", os.getenv("FOREMAN_MODEL_NAME", "devstral:latest")),
                    base_url=kwargs.get("base_url", "http://localhost:11434"),
                    max_concurrent=kwargs.get("max_concurrent", 4)
                )
            else:
                continue

            # Try to initialize
            success = await backend.initialize()

            if success:
                logger.info(f"Successfully initialized {backend.name} backend")
                return backend
            else:
                logger.warning(f"{backend.name} backend initialization failed")

        except Exception as e:
            logger.warning(f"Failed to create {backend_name} backend: {e}")
            continue

    logger.error("All backends failed to initialize")
    return None
