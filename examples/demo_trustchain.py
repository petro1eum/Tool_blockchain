#!/usr/bin/env python3
"""
🔗 TrustChain Library Demonstration
Comprehensive demo showing all key features of TrustChain.
"""

import asyncio
import time
import json
from typing import Dict, Any

from trustchain import TrustedTool, TrustLevel, SignatureAlgorithm


print("🔗 TrustChain Library Demonstration")
print("=" * 60)
print("Welcome to the comprehensive demo of TrustChain!")
print("This demo showcases cryptographically signed AI tool responses.")
print()


# === DEMO 1: Basic Trusted Tool ===
@TrustedTool("weather_service", trust_level=TrustLevel.MEDIUM)
async def get_weather(location: str) -> Dict[str, Any]:
    """Get weather information for a location."""
    # Simulate API call delay
    await asyncio.sleep(0.1)

    weather_data = {
        "New York": {"temp": 15, "humidity": 65, "condition": "Cloudy"},
        "London": {"temp": 8, "humidity": 80, "condition": "Rainy"},
        "Tokyo": {"temp": 22, "humidity": 55, "condition": "Sunny"},
    }

    result = weather_data.get(
        location, {"temp": 20, "humidity": 60, "condition": "Unknown"}
    )
    result["location"] = location
    result["timestamp"] = int(time.time())

    return result


# === DEMO 2: High-Security Financial Tool ===
@TrustedTool(
    "payment_processor",
    trust_level=TrustLevel.HIGH,
    algorithm=SignatureAlgorithm.ED25519,
)
async def process_payment(
    amount: float, from_account: str, to_account: str
) -> Dict[str, Any]:
    """Process a secure payment transaction."""
    if amount <= 0:
        raise ValueError("Amount must be positive")

    if amount > 5000:
        raise ValueError("Amount exceeds daily limit")

    transaction_id = f"TXN_{int(time.time() * 1000)}"

    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "from_account": from_account,
        "to_account": to_account,
        "status": "completed",
        "fee": round(amount * 0.025, 2),  # 2.5% fee
        "timestamp": int(time.time()),
    }


# === DEMO 3: Low-Latency Calculator (No Nonce) ===
@TrustedTool("calculator", require_nonce=False, trust_level=TrustLevel.LOW)
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


# === DEMO 4: Data Processing Tool ===
@TrustedTool("data_processor", trust_level=TrustLevel.MEDIUM)
async def process_data(data: list, operation: str = "stats") -> Dict[str, Any]:
    """Process data and return analytics."""
    if not data:
        return {"error": "No data provided"}

    if operation == "stats":
        return {
            "count": len(data),
            "sum": sum(data),
            "average": sum(data) / len(data),
            "min": min(data),
            "max": max(data),
            "operation": operation,
        }
    elif operation == "sort":
        return {
            "original": data[:5],  # First 5 elements
            "sorted": sorted(data)[:5],  # First 5 sorted
            "operation": operation,
        }
    else:
        raise ValueError(f"Unknown operation: {operation}")


async def main():
    """Main demonstration function."""
    try:
        print("🚀 Starting TrustChain Demo...")
        print()

        # === Demo 1: Weather Service ===
        print("1️⃣ Weather Service Demo")
        print("-" * 30)

        weather_response = await get_weather("New York", verify_response=False)
        print(f"   🌤️  Weather in {weather_response.data['location']}:")
        print(f"       Temperature: {weather_response.data['temp']}°C")
        print(f"       Condition: {weather_response.data['condition']}")
        print(f"   🔐 Tool ID: {weather_response.tool_id}")
        print(f"   📝 Signature: {weather_response.signature.signature[:20]}...")
        print(f"   ⏱️  Execution: {weather_response.execution_time_ms:.2f}ms")
        print()

        # === Demo 2: Payment Processing ===
        print("2️⃣ Payment Processing Demo")
        print("-" * 30)

        payment_response = await process_payment(
            1250.00, "account_123", "account_456", verify_response=False
        )
        print(f"   💰 Payment processed:")
        print(f"       Transaction ID: {payment_response.data['transaction_id']}")
        print(f"       Amount: ${payment_response.data['amount']:.2f}")
        print(f"       Fee: ${payment_response.data['fee']:.2f}")
        print(f"   🔐 Trust Level: {payment_response.trust_metadata.trust_level}")
        print(f"   📝 Algorithm: {payment_response.signature.algorithm.value}")
        print()

        # === Demo 3: Calculator ===
        print("3️⃣ Calculator Demo (No Nonce)")
        print("-" * 30)

        calc_response = await calculate("multiply", 15.5, 8.2, verify_response=False)
        print(
            f"   🧮 Calculation: {calc_response.data['operands'][0]} × {calc_response.data['operands'][1]} = {calc_response.data['result']:.2f}"
        )
        print(f"   🔐 Tool ID: {calc_response.tool_id}")
        print(f"   ⚡ No nonce required (fast mode)")
        print()

        # === Demo 4: Data Processing ===
        print("4️⃣ Data Processing Demo")
        print("-" * 30)

        sample_data = [23, 45, 12, 67, 34, 89, 56, 78, 45, 23]
        data_response = await process_data(sample_data, "stats", verify_response=False)
        print(f"   📊 Data Analysis Results:")
        print(f"       Count: {data_response.data['count']}")
        print(f"       Average: {data_response.data['average']:.2f}")
        print(
            f"       Range: {data_response.data['min']} - {data_response.data['max']}"
        )
        print(
            f"   🔐 Signature Format: {data_response.signature.signature_format.value}"
        )
        print()

        # === Demo 5: Error Handling ===
        print("5️⃣ Error Handling Demo")
        print("-" * 30)

        try:
            await process_payment(-100, "acc1", "acc2", verify_response=False)
        except Exception as e:
            print(f"   ⚠️  Expected error caught: {type(e).__name__}")
            print(f"       Message: {str(e)}")
        print()

        # === Demo 6: Performance Testing ===
        print("6️⃣ Performance Testing")
        print("-" * 30)

        start_time = time.time()
        tasks = []
        for i in range(10):
            task = calculate("add", i, i * 2, verify_response=False)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        end_time = time.time()

        print(
            f"   ⚡ Processed 10 calculations in {(end_time - start_time)*1000:.2f}ms"
        )
        print(f"   📊 Average per operation: {(end_time - start_time)*100:.2f}ms")
        print()

        # === Demo 7: Statistics ===
        print("7️⃣ Tool Statistics")
        print("-" * 30)

        calc_stats = await calculate.get_statistics()
        weather_stats = await get_weather.get_statistics()

        print(f"   🧮 Calculator:")
        print(f"       Total calls: {calc_stats['stats']['total_calls']}")
        print(f"       Success rate: {calc_stats['success_rate']:.2%}")

        print(f"   🌤️  Weather Service:")
        print(f"       Total calls: {weather_stats['stats']['total_calls']}")
        print(f"       Avg execution: {weather_stats['avg_execution_time_ms']:.2f}ms")
        print()

        # === Demo 8: Signature Uniqueness ===
        print("8️⃣ Signature Uniqueness Demo")
        print("-" * 30)

        response1 = await get_weather("London", verify_response=False)
        response2 = await get_weather("London", verify_response=False)  # Same data

        sig1 = response1.signature.signature[:15]
        sig2 = response2.signature.signature[:15]

        print(f"   🔐 Signature 1: {sig1}...")
        print(f"   🔐 Signature 2: {sig2}...")
        print(f"   ✅ Signatures different: {sig1 != sig2}")
        print(f"       (Same data, different timestamps)")
        print()

        # === Demo 9: JSON Export ===
        print("9️⃣ Data Export Demo")
        print("-" * 30)

        export_data = {
            "tool_id": weather_response.tool_id,
            "timestamp": weather_response.timestamp,
            "data": weather_response.data,
            "signature_algorithm": weather_response.signature.algorithm.value,
            "has_signature": weather_response.signature is not None,
            "trust_level": weather_response.trust_metadata.trust_level.value,
        }

        print(f"   📄 Exported Response Data:")
        print(json.dumps(export_data, indent=6))
        print()

        # === Final Summary ===
        print("🎉 Demo Completed Successfully!")
        print("=" * 60)
        print("✅ All TrustChain features demonstrated:")
        print("   • Cryptographic signatures for all responses")
        print("   • Different trust levels (LOW, MEDIUM, HIGH)")
        print("   • Replay protection with nonces")
        print("   • Error handling and validation")
        print("   • Performance monitoring")
        print("   • Both async and sync function support")
        print("   • Unique signatures for each response")
        print("   • JSON serialization compatibility")
        print()
        print("🔗 TrustChain prevents AI hallucinations through")
        print("   cryptographic proof of authentic responses!")

        return True

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
