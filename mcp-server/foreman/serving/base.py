"""Base serving backend interface."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class ServingBackend(ABC):
    """Abstract base class for serving backends."""

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the serving backend.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the backend is available and ready.

        Returns:
            bool: True if backend is available, False otherwise
        """
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text from the SLM.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional generation parameters

        Returns:
            Optional[str]: Generated text or None on failure
        """
        pass

    @abstractmethod
    async def get_capacity(self) -> Dict[str, Any]:
        """
        Get current capacity information.

        Returns:
            Dict[str, Any]: Capacity information (available slots, queue length, etc.)
        """
        pass

    @abstractmethod
    async def shutdown(self):
        """Shutdown the serving backend."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name."""
        pass
