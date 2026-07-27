"""Ollama serving backend implementation."""

import asyncio
import logging
import subprocess
from typing import Optional, Dict, Any
import httpx

from .base import ServingBackend

logger = logging.getLogger(__name__)


class OllamaBackend(ServingBackend):
    """Ollama + MLX serving backend."""

    def __init__(
        self,
        model_name: str = "devstral:latest",
        base_url: str = "http://localhost:11434",
        max_concurrent: int = 4
    ):
        """
        Initialize Ollama backend.

        Args:
            model_name: Name of the model to use
            base_url: Base URL for Ollama API
            max_concurrent: Maximum concurrent requests
        """
        self.model_name = model_name
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._initialized = False
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        """Backend name."""
        return "ollama"

    async def initialize(self) -> bool:
        """Initialize the Ollama backend."""
        try:
            # Check if Ollama is running
            self._client = httpx.AsyncClient(timeout=30.0)
            response = await self._client.get(f"{self.base_url}/api/tags")

            if response.status_code != 200:
                logger.error("Ollama is not responding")
                return False

            # Check if model is available
            models = response.json().get("models", [])
            model_names = [m.get("name") for m in models]

            if self.model_name not in model_names:
                logger.warning(f"Model {self.model_name} not found in Ollama. Attempting to pull...")
                await self._pull_model()

            self._initialized = True
            logger.info(f"Ollama backend initialized with model: {self.model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Ollama backend: {e}")
            return False

    async def _pull_model(self):
        """Pull the model from Ollama registry."""
        try:
            response = await self._client.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model_name}
            )
            logger.info(f"Model {self.model_name} pull initiated")
        except Exception as e:
            logger.error(f"Failed to pull model: {e}")
            raise

    async def is_available(self) -> bool:
        """Check if Ollama is available."""
        if not self._initialized:
            return False

        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
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
        Generate text using Ollama.

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
                response = await self._client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                            **kwargs
                        }
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("response")
                else:
                    logger.error(f"Ollama generation failed: {response.status_code}")
                    return None

            except Exception as e:
                logger.error(f"Error during generation: {e}")
                return None

    async def get_capacity(self) -> Dict[str, Any]:
        """Get current capacity information."""
        # Simple capacity tracking based on semaphore
        available = self._semaphore._value
        total = self.max_concurrent

        return {
            "available_slots": available,
            "total_slots": total,
            "in_use": total - available
        }

    async def shutdown(self):
        """Shutdown the Ollama backend."""
        if self._client:
            await self._client.aclose()
        self._initialized = False
        logger.info("Ollama backend shutdown")
