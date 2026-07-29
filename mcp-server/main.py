#!/usr/bin/env python3
"""Foreman MCP Server - Main entry point."""

import asyncio
from foreman.server import main

if __name__ == "__main__":
    asyncio.run(main())
