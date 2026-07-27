"""Serving layer for local SLM inference."""

from .base import ServingBackend
from .factory import create_backend

__all__ = ["ServingBackend", "create_backend"]
