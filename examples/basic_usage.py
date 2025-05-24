#!/usr/bin/env python3
"""Basic usage example for TrustChain library v2."""

import asyncio
import sys
import time
from typing import Any, Dict

from trustchain.v2 import TrustChain, TrustChainConfig

# Create TrustChain instance with configuration
tc = TrustChain(TrustChainConfig(
    enable_nonce=False,  # Disable nonce for simpler examples
    cache_ttl=3600,
    max_cached_responses=100,
))


# Example 1: Simple trusted tool
@tc.tool("weather_api_v1")
def get_weather(location: str) -> Dict[str, Any]:
    """Get weather information for a location."""
    # Simulate API call
    time.sleep(0.1)

    return {
        "location": location,
        "temperature": 22.5,
        "humidity": 65,
        "conditions": "Partly cloudy",
        "timestamp": int(time.time() * 1000),
    }


# Example 2: High-security financial tool
@tc.tool("payment_processor_v1")
def process_payment(
    amount: float, recipient: str, currency: str = "USD"
) -> Dict[str, Any]:
    """Process a financial payment."""
    if amount <= 0:
        raise ValueError("Amount must be positive")

    if amount > 10000:
        # High-value transaction
        transaction_id = f"HV_{int(time.time())}"
    else:
        transaction_id = f"TX_{int(time.time())}"

    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "recipient": recipient,
        "currency": currency,
        "status": "completed",
        "fee": amount * 0.01,  # 1% fee
        "processed_at": int(time.time() * 1000),
    }


# Example 3: Simple calculator (no nonce required for speed)
@tc.tool("calculator_v1")
def calculate(operation: str, a: float, b: float) -> Dict[str, Any]:
    """Perform basic mathematical operations."""
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None,
    }

    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")

    result = operations[operation](a, b)

    return {
        "operation": operation,
        "operands": [a, b],
        "result": result,
        "valid": result is not None,
    }


# Example 4: Data analysis tool - now async
@tc.tool("data_analyzer_v1")
async def analyze_data(data: list, analysis_type: str = "basic") -> Dict[str, Any]:
    """Analyze numerical data."""
    if not data:
        return {"error": "No data provided"}

    # Simulate async processing
    await asyncio.sleep(0.01)

    # Basic statistics
    total = sum(data)
    count = len(data)
    average = total / count
    minimum = min(data)
    maximum = max(data)

    result = {
        "analysis_type": analysis_type,
        "count": count,
        "sum": total,
        "average": average,
        "min": minimum,
        "max": maximum,
        "range": maximum - minimum,
    }

    if analysis_type == "advanced":
        # Calculate variance and standard deviation
        variance = sum((x - average) ** 2 for x in data) / count
        std_dev = variance**0.5

        result.update(
            {
                "variance": variance,
                "standard_deviation": std_dev,
                "median": sorted(data)[count // 2],
            }
        )

    return result


async def main():
    """Main example function."""
    print("🔗 TrustChain Basic Usage Example (v2)")
    print("=" * 50)

    # TrustChain v2 works out of the box - no setup needed!
    print("\n🔧 TrustChain v2 initialized...")
    print("   ✅ Simple API - just use @tc.tool() decorator")

    # Example 1: Weather API
    print("\n1. Weather API Example:")
    weather_response = get_weather("New York")
    print(f"   Tool ID: {weather_response.tool_id}")
    print(f"   Signature ID: {weather_response.signature_id}")
    print(f"   Data: {weather_response.data}")
    print(f"   Verified: {weather_response.is_verified}")
    print(f"   Signature: {weather_response.signature[:32]}...")

    # Example 2: Payment processing
    print("\n2. Payment Processing Example:")
    try:
        payment_response = process_payment(
            amount=1500.00, recipient="merchant@example.com", currency="USD"
        )
        print(f"   Tool ID: {payment_response.tool_id}")
        print(f"   Transaction: {payment_response.data['transaction_id']}")
        print(f"   Amount: ${payment_response.data['amount']}")
        print(f"   Fee: ${payment_response.data['fee']}")
        print(f"   Verified: {payment_response.is_verified}")
        print(f"   Signature: {payment_response.signature[:32]}...")
    except Exception as e:
        print(f"   Error: {e}")

    # Example 3: Calculator (synchronous function)
    print("\n3. Calculator Example:")
    calc_response = calculate("multiply", 15, 4)
    print(f"   Tool ID: {calc_response.tool_id}")
    print(f"   Operation: {calc_response.data['operation']}")
    print(f"   Result: {calc_response.data['result']}")
    print(f"   Verified: {calc_response.is_verified}")
    print(f"   Signature: {calc_response.signature[:32]}...")

    # Example 4: Data analysis (async)
    print("\n4. Data Analysis Example:")
    sample_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    analysis_response = await analyze_data(sample_data, "advanced")
    print(f"   Tool ID: {analysis_response.tool_id}")
    print(f"   Average: {analysis_response.data['average']}")
    print(f"   Std Dev: {analysis_response.data['standard_deviation']:.2f}")
    print(f"   Verified: {analysis_response.is_verified}")
    print(f"   Signature: {analysis_response.signature[:32]}...")

    # Example 5: Show tool statistics
    print("\n5. Tool Statistics:")
    weather_stats = tc.get_tool_stats("weather_api_v1")
    print(f"   Weather API calls: {weather_stats['call_count']}")
    print(f"   Last execution time: {weather_stats.get('last_execution_time', 0) * 1000:.2f}ms")
    
    # Overall stats
    overall_stats = tc.get_stats()
    print(f"\n   Overall statistics:")
    print(f"   Total tools: {overall_stats['total_tools']}")
    print(f"   Total calls: {overall_stats['total_calls']}")
    print(f"   Cache size: {overall_stats['cache_size']}")

    # Example 6: Verify signatures manually
    print("\n6. Manual Signature Verification:")
    is_valid = tc.verify(weather_response)
    print(f"   Weather response valid: {is_valid}")
    print(f"   Algorithm used: {tc._signer.algorithm}")
    print(f"   Signature ID: {weather_response.signature_id}")
    print(f"   Timestamp: {weather_response.timestamp}")
    
    # Verify other responses too
    print(f"   Payment response valid: {tc.verify(payment_response)}")
    print(f"   Calculator response valid: {tc.verify(calc_response)}")
    print(f"   Analysis response valid: {tc.verify(analysis_response)}")

    # Example 7: Error handling
    print("\n7. Error Handling Example:")
    try:
        # This should fail due to invalid amount
        process_payment(-100, "test@example.com")
    except Exception as e:
        print(f"   Expected error caught: {type(e).__name__}: {e}")
    
    # Now try with valid amount
    try:
        valid_payment = process_payment(50.0, "test@example.com")
        print(f"   Valid payment successful: {valid_payment.is_verified}")
        print(f"   Transaction ID: {valid_payment.data['transaction_id']}")
        print(f"   Signature: {valid_payment.signature[:32]}...")
    except Exception as e:
        print(f"   Unexpected error: {e}")

    print("\n✅ All examples completed successfully!")
    print("\nKey Benefits of v2:")
    print("  • Simpler API - just @tc.tool() decorator")
    print("  • No global state - explicit TrustChain instances")
    print("  • Automatic sync/async detection")
    print("  • Built-in statistics and caching")
    print("  • Configuration-based - no hardcoded values")


if __name__ == "__main__":
    asyncio.run(main())
