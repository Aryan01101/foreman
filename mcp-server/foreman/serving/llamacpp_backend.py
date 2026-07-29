"""llama.cpp serving backend implementation."""

import asyncio
import logging
from typing import Optional, Dict, Any
import subprocess
import json

from .base import ServingBackend

logger = logging.getLogger(__name__)


class LlamaCppBackend(ServingBackend):
    """llama.cpp serving backend with custom admission control."""

    def __init__(
        self,
        model_path: str,
        server_port: int = 8080,
        max_concurrent: int = 4,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1  # -1 = use all GPU layers
    ):
        """
        Initialize llama.cpp backend.

        Args:
            model_path: Path to GGUF model file
            server_port: Port for llama.cpp server
            max_concurrent: Maximum concurrent requests
            n_ctx: Context window size
            n_gpu_layers: Number of layers to offload to GPU
        """
        self.model_path = model_path
        self.server_port = server_port
        self.max_concurrent = max_concurrent
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._initialized = False
        self._server_process: Optional[subprocess.Popen] = None

    @property
    def name(self) -> str:
        """Backend name."""
        return "llama.cpp"

    async def initialize(self) -> bool:
        """Initialize the llama.cpp backend."""
        try:
            # Check if model file exists
            import os
            if not os.path.exists(self.model_path):
                logger.error(f"Model file not found: {self.model_path}")
                return False

            # Start llama.cpp server
            # Note: This is a placeholder - actual implementation would use llama-cpp-python
            # or the server binary with proper Metal GPU support
            logger.info(f"Starting llama.cpp server on port {self.server_port}")

            # TODO: Actually start llama.cpp server
            # For MVP, we'll mark this as requiring manual server start
            logger.warning("llama.cpp backend requires manual server start for MVP")
            logger.info(f"Please start llama.cpp server manually:")
            logger.info(f"  ./server -m {self.model_path} -c {self.n_ctx} --port {self.server_port} -ngl {self.n_gpu_layers}")

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize llama.cpp backend: {e}")
            return False

    async def is_available(self) -> bool:
        """Check if llama.cpp server is available."""
        if not self._initialized:
            return False

        try:
            # Check if server is responding
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://localhost:{self.server_port}/health")
                return response.status_code == 200
        except:
            return False

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text using llama.cpp.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional generation parameters

        Returns:
            Optional[str]: Generated text or None on failure
        """
        if not self._initialized:
            logger.error("Backend not initialized")
            return None

        async with self._semaphore:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"http://localhost:{self.server_port}/completion",
                        json={
                            "prompt": prompt,
                            "n_predict": max_tokens,
                            "temperature": temperature,
                            "stream": False,
                            **kwargs
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        return result.get("content")
                    else:
                        logger.error(f"llama.cpp generation failed: {response.status_code}")
                        return None

            except Exception as e:
                logger.error(f"Error during generation: {e}")
                return None

    async def get_capacity(self) -> Dict[str, Any]:
        """Get current capacity information."""
        available = self._semaphore._value
        total = self.max_concurrent

        return {
            "available_slots": available,
            "total_slots": total,
            "in_use": total - available
        }

    async def shutdown(self):
        """Shutdown the llama.cpp backend."""
        if self._server_process:
            self._server_process.terminate()
            self._server_process.wait()
        self._initialized = False
        logger.info("llama.cpp backend shutdown")
