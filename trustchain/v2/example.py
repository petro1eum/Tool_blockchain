#!/usr/bin/env python3
"""Example usage of TrustChain v2."""

import asyncio

from trustchain.v2 import TrustChain, TrustChainConfig


def main():
    """Simple example of TrustChain v2 usage."""

    # Create TrustChain instance with custom config
    tc = TrustChain(
        TrustChainConfig(
            enable_nonce=True,  # Enable replay protection
            cache_ttl=600,  # 10 minutes cache
        )
    )

    # Define a simple tool
    @tc.tool("weather_api")
    def get_weather(city: str):
        """Get weather for a city."""
        return {"city": city, "temperature": 20, "conditions": "Sunny"}

    # Define another tool
    @tc.tool("calculator")
    def calculate(operation: str, a: float, b: float):
        """Simple calculator."""
        operations = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else None,
        }

        if operation not in operations:
            raise ValueError(f"Unknown operation: {operation}")

        return {
            "operation": operation,
            "a": a,
            "b": b,
            "result": operations[operation](a, b),
        }

    print("🔗 TrustChain v2 Example")
    print("=" * 50)

    # Use weather tool
    print("\n1. Weather API:")
    weather_response = get_weather("Paris")
    print(f"   Response: {weather_response.data}")
    print(f"   Signature: {weather_response.signature[:32]}...")
    print(f"   Verified: {weather_response.is_verified}")

    # Use calculator
    print("\n2. Calculator:")
    calc_response = calculate("multiply", 7, 8)
    print(f"   Response: {calc_response.data}")
    print(f"   Verified: {calc_response.is_verified}")

    # Verify manually
    print("\n3. Manual verification:")
    is_valid = tc.verify(weather_response)
    print(f"   Weather response valid: {is_valid}")

    # Show statistics
    print("\n4. Statistics:")
    stats = tc.get_stats()
    print(f"   Total tools: {stats['total_tools']}")
    print(f"   Total calls: {stats['total_calls']}")
    print(f"   Cache size: {stats['cache_size']}")

    # Tool-specific stats
    weather_stats = tc.get_tool_stats("weather_api")
    print("\n   Weather API stats:")
    print(f"   - Call count: {weather_stats['call_count']}")
    print(
        f"   - Last execution time: {weather_stats.get('last_execution_time', 'N/A')}"
    )


async def async_example():
    """Example with async tools."""
    tc = TrustChain()

    @tc.tool("async_api")
    async def fetch_data(url: str):
        """Simulate async API call."""
        await asyncio.sleep(0.1)  # Simulate network delay
        return {"url": url, "status": "success", "data": "example"}

    print("\n5. Async tool example:")
    response = await fetch_data("https://api.example.com")
    print(f"   Response: {response.data}")
    print(f"   Verified: {response.is_verified}")


if __name__ == "__main__":
    # Run sync example
    main()

    # Run async example
    print("\n" + "=" * 50)
    asyncio.run(async_example())
