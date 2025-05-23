#!/usr/bin/env python3
"""Basic usage example for TrustChain library."""

import asyncio
import time
from typing import Dict, Any

from trustchain import (
    TrustedTool, 
    MemoryRegistry,
    SignatureAlgorithm,
    TrustLevel
)


# Example 1: Simple trusted tool
@TrustedTool("weather_api_v1")
async def get_weather(location: str) -> Dict[str, Any]:
    """Get weather information for a location."""
    # Simulate API call
    await asyncio.sleep(0.1)
    
    return {
        "location": location,
        "temperature": 22.5,
        "humidity": 65,
        "conditions": "Partly cloudy",
        "timestamp": int(time.time() * 1000)
    }


# Example 2: High-security financial tool  
@TrustedTool(
    "payment_processor_v1",
    trust_level=TrustLevel.HIGH,
    algorithm=SignatureAlgorithm.ED25519,
    description="Secure payment processing tool"
)
async def process_payment(amount: float, recipient: str, currency: str = "USD") -> Dict[str, Any]:
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
        "processed_at": int(time.time() * 1000)
    }


# Example 3: Simple calculator (no nonce required for speed)
@TrustedTool(
    "calculator_v1",
    require_nonce=False,
    trust_level=TrustLevel.LOW,
    description="Basic mathematical operations"
)
def calculate(operation: str, a: float, b: float) -> Dict[str, Any]:
    """Perform basic mathematical operations."""
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None
    }
    
    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation}")
    
    result = operations[operation](a, b)
    
    return {
        "operation": operation,
        "operands": [a, b],
        "result": result,
        "valid": result is not None
    }


# Example 4: Data analysis tool
@TrustedTool(
    "data_analyzer_v1", 
    trust_level=TrustLevel.MEDIUM,
    description="Analyze data and provide insights"
)
async def analyze_data(data: list, analysis_type: str = "basic") -> Dict[str, Any]:
    """Analyze numerical data."""
    if not data:
        return {"error": "No data provided"}
    
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
        "range": maximum - minimum
    }
    
    if analysis_type == "advanced":
        # Calculate variance and standard deviation
        variance = sum((x - average) ** 2 for x in data) / count
        std_dev = variance ** 0.5
        
        result.update({
            "variance": variance,
            "standard_deviation": std_dev,
            "median": sorted(data)[count // 2]
        })
    
    return result


async def main():
    """Main example function."""
    print("🔗 TrustChain Basic Usage Example")
    print("=" * 50)
    
    # Example 1: Weather API
    print("\n1. Weather API Example:")
    weather_response = await get_weather("New York")
    print(f"   Tool ID: {weather_response.tool_id}")
    print(f"   Request ID: {weather_response.request_id}")
    print(f"   Data: {weather_response.data}")
    print(f"   Verified: {weather_response.is_verified}")
    print(f"   Execution time: {weather_response.execution_time_ms:.2f}ms")
    
    # Example 2: Payment processing
    print("\n2. Payment Processing Example:")
    try:
        payment_response = await process_payment(
            amount=1500.00,
            recipient="merchant@example.com",
            currency="USD"
        )
        print(f"   Tool ID: {payment_response.tool_id}")
        print(f"   Transaction: {payment_response.data['transaction_id']}")
        print(f"   Amount: ${payment_response.data['amount']}")
        print(f"   Fee: ${payment_response.data['fee']}")
        print(f"   Verified: {payment_response.is_verified}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 3: Calculator (synchronous function)
    print("\n3. Calculator Example:")
    calc_response = await calculate("multiply", 15, 4)
    print(f"   Tool ID: {calc_response.tool_id}")
    print(f"   Operation: {calc_response.data['operation']}")
    print(f"   Result: {calc_response.data['result']}")
    print(f"   Verified: {calc_response.is_verified}")
    
    # Example 4: Data analysis
    print("\n4. Data Analysis Example:")
    sample_data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    analysis_response = await analyze_data(sample_data, "advanced")
    print(f"   Tool ID: {analysis_response.tool_id}")
    print(f"   Average: {analysis_response.data['average']}")
    print(f"   Std Dev: {analysis_response.data['standard_deviation']:.2f}")
    print(f"   Verified: {analysis_response.is_verified}")
    
    # Example 5: Show tool statistics
    print("\n5. Tool Statistics:")
    weather_stats = await get_weather.get_statistics()
    print(f"   Weather API calls: {weather_stats['stats']['total_calls']}")
    print(f"   Success rate: {weather_stats['success_rate']:.2%}")
    print(f"   Avg execution time: {weather_stats['avg_execution_time_ms']:.2f}ms")
    
    # Example 6: Verify signatures manually
    print("\n6. Manual Signature Verification:")
    from trustchain.core.signatures import get_signature_engine
    
    signature_engine = get_signature_engine()
    if signature_engine:
        verification_result = signature_engine.verify_response(weather_response)
        print(f"   Verification valid: {verification_result.valid}")
        print(f"   Algorithm used: {verification_result.algorithm_used.value}")
        print(f"   Trust level: {verification_result.trust_level.value}")
        print(f"   Verification time: {verification_result.verification_time_ms:.2f}ms")
    
    # Example 7: Error handling
    print("\n7. Error Handling Example:")
    try:
        # This should fail due to invalid amount
        await process_payment(-100, "test@example.com")
    except Exception as e:
        print(f"   Expected error caught: {type(e).__name__}: {e}")
    
    print("\n✅ All examples completed successfully!")
    print("\nKey Benefits Demonstrated:")
    print("  • Automatic signature generation and verification")
    print("  • Replay protection with nonces")
    print("  • Performance tracking and statistics")
    print("  • Different trust levels for different use cases")
    print("  • Seamless integration with async and sync functions")


if __name__ == "__main__":
    asyncio.run(main()) 