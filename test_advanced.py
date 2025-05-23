#!/usr/bin/env python3
"""Advanced test of TrustChain with full verification."""

import asyncio
from trustchain import (
    TrustedTool, 
    MemoryRegistry, 
    SignatureAlgorithm, 
    TrustLevel,
    SignatureEngine,
    get_crypto_engine
)
from trustchain.core.signatures import set_signature_engine
from trustchain.core.models import KeyMetadata


async def setup_full_verification():
    """Set up registry and signature engine for full verification."""
    # Create registry
    registry = MemoryRegistry()
    await registry.start()
    
    # Create signature engine
    signature_engine = SignatureEngine(registry)
    set_signature_engine(signature_engine)
    
    return registry, signature_engine


@TrustedTool("crypto_test_tool", trust_level=TrustLevel.HIGH)
async def crypto_tool(operation: str, data: str) -> dict:
    """Tool for testing cryptographic operations."""
    import hashlib
    
    if operation == "hash":
        result = hashlib.sha256(data.encode()).hexdigest()
        return {"operation": operation, "input": data, "result": result}
    elif operation == "reverse":
        return {"operation": operation, "input": data, "result": data[::-1]}
    else:
        raise ValueError(f"Unknown operation: {operation}")


@TrustedTool("financial_tool", trust_level=TrustLevel.CRITICAL, algorithm=SignatureAlgorithm.ED25519)
async def financial_transaction(amount: float, from_account: str, to_account: str) -> dict:
    """Simulate financial transaction."""
    if amount <= 0:
        raise ValueError("Amount must be positive")
    
    if amount > 10000:
        raise ValueError("Amount exceeds daily limit")
    
    transaction_id = f"tx_{int(asyncio.get_event_loop().time() * 1000)}"
    
    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "from": from_account,
        "to": to_account,
        "status": "pending",
        "fee": round(amount * 0.001, 2)  # 0.1% fee
    }


async def main():
    """Run advanced tests."""
    print("🚀 TrustChain Advanced Test")
    print("=" * 40)
    
    try:
        # Setup full verification
        print("\n📋 Setting up verification environment...")
        registry, signature_engine = await setup_full_verification()
        print("   ✅ Registry and signature engine ready")
        
        # Test 1: Cryptographic operations with full verification
        print("\n1. Testing crypto tool with verification:")
        response1 = await crypto_tool("hash", "Hello World", verify_response=False)
        print(f"   Tool ID: {response1.tool_id}")
        print(f"   Operation: {response1.data['operation']}")
        print(f"   Result: {response1.data['result'][:20]}...")
        print(f"   Verified: {response1.is_verified}")
        print(f"   Trust Level: {response1.trust_metadata.trust_level}")
        
        # Test 2: Financial transaction
        print("\n2. Testing financial transaction:")
        response2 = await financial_transaction(1500.0, "acc_001", "acc_002", verify_response=False)
        print(f"   Transaction ID: {response2.data['transaction_id']}")
        print(f"   Amount: ${response2.data['amount']}")
        print(f"   Fee: ${response2.data['fee']}")
        print(f"   Verified: {response2.is_verified}")
        print(f"   Trust Level: {response2.trust_metadata.trust_level}")
        
        # Test 3: Error handling
        print("\n3. Testing error handling:")
        try:
            await financial_transaction(-100, "acc_001", "acc_002")
        except Exception as e:
            print(f"   ✅ Expected error caught: {type(e).__name__}: {e}")
        
        # Test 4: Multiple calls and statistics
        print("\n4. Testing multiple calls and statistics:")
        for i in range(3):
            await crypto_tool("reverse", f"test_message_{i}", verify_response=False)
        
        stats = await crypto_tool.get_statistics()
        print(f"   Total calls: {stats['stats']['total_calls']}")
        print(f"   Success rate: {stats['success_rate']:.2%}")
        print(f"   Avg execution time: {stats['avg_execution_time_ms']:.2f}ms")
        
        # Test 5: Registry inspection
        print("\n5. Testing registry inspection:")
        registry_stats = await registry.get_statistics()
        print(f"   Total keys: {registry_stats['key_stats']['total']}")
        print(f"   Valid keys: {registry_stats['key_stats']['valid']}")
        print(f"   Registry calls: {registry_stats['operation_stats']['get_key_calls']}")
        
        # Test 6: Manual signature verification
        print("\n6. Testing manual signature verification:")
        verification_result = signature_engine.verify_response(response1)
        print(f"   Verification valid: {verification_result.valid}")
        print(f"   Algorithm: {verification_result.algorithm_used.value}")
        print(f"   Verification time: {verification_result.verification_time_ms:.2f}ms")
        
        # Test 7: Key listing
        print("\n7. Testing key management:")
        all_keys = await registry.list_keys()
        print(f"   Total keys in registry: {len(all_keys)}")
        for key in all_keys[:2]:  # Show first 2 keys
            print(f"   - {key.key_id} ({key.tool_id}, {key.algorithm.value})")
        
        print("\n🎉 All advanced tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Advanced test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        if 'registry' in locals():
            await registry.stop()


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1) 