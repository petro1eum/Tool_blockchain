"""
Pytest configuration for TrustChain tests.

Handles platform-specific configuration and fixtures.
"""

import asyncio
import platform
import sys

import pytest

# Windows compatibility fix for asyncio
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop_policy():
    """Event loop policy fixture for cross-platform compatibility."""
    if platform.system() == "Windows":
        return asyncio.WindowsProactorEventLoopPolicy()
    else:
        return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="function")
async def event_loop():
    """Create event loop for each test function."""
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    yield loop

    # Clean up the loop
    loop.close()


def pytest_configure(config):
    """Configure pytest for different platforms."""
    if platform.system() == "Windows":
        # Windows-specific configuration
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Add custom markers
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "windows: marks tests as Windows-specific")
    config.addinivalue_line("markers", "linux: marks tests as Linux-specific")
    config.addinivalue_line("markers", "macos: marks tests as macOS-specific")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on platform."""
    skip_windows = pytest.mark.skip(reason="Windows-only test")
    skip_unix = pytest.mark.skip(reason="Unix-only test")

    for item in items:
        if "windows" in item.keywords and platform.system() != "Windows":
            item.add_marker(skip_windows)
        elif "linux" in item.keywords and platform.system() != "Linux":
            item.add_marker(skip_unix)
        elif "macos" in item.keywords and platform.system() != "Darwin":
            item.add_marker(skip_unix)


# Platform-specific async timeout settings
if platform.system() == "Windows":
    # Windows might need longer timeouts
    pytest.DEFAULT_TIMEOUT = 30
else:
    pytest.DEFAULT_TIMEOUT = 10
