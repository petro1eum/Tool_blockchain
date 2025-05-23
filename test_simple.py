#!/usr/bin/env python3
"""Simple test of TrustChain functionality."""

import asyncio
from trustchain import TrustedTool, MemoryRegistry, SignatureAlgorithm, TrustLevel


# Simple trusted tool with verification disabled
@TrustedTool("simple_test_tool", auto_register=True)
async def simple_tool(message: str) -> dict:
    """Simple test tool."""
    return {
        "echo": message,
        "status": "success"
    }


# Tool with no nonce requirement for testing
@TrustedTool(
    "no_nonce_tool", 
    require_nonce=False, 
    auto_register=True,
    trust_level=TrustLevel.LOW
)
def sync_tool(a: int, b: int) -> dict:
    """Synchronous tool for testing."""
    return {
        "sum": a + b,
        "product": a * b
    }


async def main():
    """Run simple tests."""
    print("🧪 TrustChain Simple Test")
    print("=" * 30)
    
    try:
        # Test 1: Async tool without verification
        print("\n1. Testing async tool (no verification):")
        response1 = await simple_tool("Hello, TrustChain!", verify_response=False)
        print(f"   Tool ID: {response1.tool_id}")
        print(f"   Data: {response1.data}")
        print(f"   Has signature: {response1.signature is not None}")
        print(f"   Timestamp: {response1.timestamp}")
        
        # Test 2: Sync tool without nonce
        print("\n2. Testing sync tool (no nonce, no verification):")
        response2 = await sync_tool(15, 7, verify_response=False)
        print(f"   Tool ID: {response2.tool_id}")
        print(f"   Data: {response2.data}")
        print(f"   Has signature: {response2.signature is not None}")
        
        # Test 3: Check signatures are different
        print("\n3. Testing signature uniqueness:")
        response3 = await simple_tool("Different message", verify_response=False)
        sig1 = response1.signature.signature[:20] + "..."
        sig3 = response3.signature.signature[:20] + "..."
        print(f"   Signature 1: {sig1}")
        print(f"   Signature 2: {sig3}")
        print(f"   Signatures different: {response1.signature.signature != response3.signature.signature}")
        
        # Test 4: Tool statistics
        print("\n4. Testing statistics:")
        stats = await simple_tool.get_statistics()
        print(f"   Total calls: {stats['stats']['total_calls']}")
        print(f"   Success rate: {stats['success_rate']:.2%}")
        
        print("\n✅ All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1) 