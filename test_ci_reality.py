#!/usr/bin/env python3
"""
🔍 CI Reality Test - No Cheating!

This test reproduces the EXACT conditions that happen in CI:
- No auto_register=False shortcuts
- No custom registries 
- No pre-configured engines
- Fresh global state like in CI

Author: Ed Cherednik
"""

import asyncio
import subprocess
import sys
import os

# Reset all global state to simulate CI
def reset_global_state():
    """Reset global state like in fresh CI environment."""
    # Clear module cache to force fresh imports
    modules_to_clear = [mod for mod in sys.modules.keys() if mod.startswith('trustchain')]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

async def test_ci_exact_conditions():
    """Test the EXACT conditions that fail in CI."""
    print("🔍 Testing EXACT CI conditions...")
    
    # Reset global state
    reset_global_state()
    
    # Import exactly like in examples (fresh state)
    from trustchain import TrustedTool, TrustLevel, SignatureAlgorithm
    
    # Create tools exactly like in examples - NO SHORTCUTS!
    @TrustedTool("weather_api_v1")  # No auto_register=False!
    async def get_weather(location: str):
        """Exactly like in basic_usage.py"""
        await asyncio.sleep(0.1)
        return {
            "location": location,
            "temperature": 22.5,
            "conditions": "Partly cloudy"
        }
    
    @TrustedTool("calculator_v1", require_nonce=False, trust_level=TrustLevel.LOW)
    def calculate(operation: str, a: float, b: float):
        """Exactly like in basic_usage.py"""
        if operation == "multiply":
            return {"result": a * b, "operation": operation}
        raise ValueError(f"Unsupported operation: {operation}")
    
    # Execute exactly like in CI
    print("   🌤️  Calling weather tool...")
    try:
        weather_response = await get_weather("New York")
        print(f"      Response type: {type(weather_response)}")
        print(f"      Has signature: {hasattr(weather_response, 'signature')}")
        print(f"      Is verified: {weather_response.is_verified}")
        print("   ✅ Weather tool succeeded")
    except Exception as e:
        print(f"   ❌ Weather tool failed: {e}")
        return False
    
    print("   🧮 Calling calculator tool...")
    try:
        calc_response = await calculate("multiply", 15, 4)
        print(f"      Response type: {type(calc_response)}")
        print(f"      Has signature: {hasattr(calc_response, 'signature')}")
        print(f"      Is verified: {calc_response.is_verified}")
        print("   ✅ Calculator tool succeeded")
    except Exception as e:
        print(f"   ❌ Calculator tool failed: {e}")
        return False
    
    print("   🔐 Testing signature verification...")
    try:
        from trustchain.core.signatures import get_signature_engine
        engine = get_signature_engine()
        result = engine.verify_response(weather_response)
        print(f"      Verification valid: {result.valid}")
        print(f"      Error message: {result.error_message if not result.valid else 'None'}")
        if not result.valid:
            print("   ❌ Signature verification failed")
            return False
        print("   ✅ Signature verification succeeded")
    except Exception as e:
        print(f"   ❌ Signature verification error: {e}")
        return False
    
    return True

async def test_multiple_fresh_runs():
    """Test multiple runs like CI does multiple test files."""
    print("\n🔄 Testing multiple fresh runs (like CI)...")
    
    for i in range(3):
        print(f"\n--- Run {i+1} ---")
        success = await test_ci_exact_conditions()
        if not success:
            print(f"❌ Run {i+1} failed!")
            return False
        print(f"✅ Run {i+1} succeeded")
    
    return True

def test_subprocess_isolation():
    """Test in separate process like CI does."""
    print("\n🔀 Testing subprocess isolation...")
    
    test_code = '''
import asyncio
from trustchain import TrustedTool

@TrustedTool("subprocess_tool")
async def subprocess_tool(data: str):
    return {"processed": data}

async def main():
    try:
        response = await subprocess_tool("test")
        print(f"SUCCESS: {response.is_verified}")
        return 0
    except Exception as e:
        print(f"FAILED: {e}")
        return 1

exit(asyncio.run(main()))
    '''
    
    result = subprocess.run([sys.executable, "-c", test_code], 
                          capture_output=True, text=True)
    
    print(f"   Exit code: {result.returncode}")
    print(f"   Stdout: {result.stdout.strip()}")
    if result.stderr:
        print(f"   Stderr: {result.stderr.strip()}")
    
    return result.returncode == 0

async def main():
    """Run all CI reality tests."""
    print("🧪 CI Reality Test - No Shortcuts, No Cheating!")
    print("=" * 60)
    print("Testing the EXACT conditions that cause CI failures...")
    
    tests = [
        ("Fresh state test", test_ci_exact_conditions()),
        ("Multiple runs test", test_multiple_fresh_runs()),
        ("Subprocess isolation", test_subprocess_isolation()),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, test in tests:
        print(f"\n🧪 {name}...")
        try:
            if asyncio.iscoroutine(test):
                success = await test
            else:
                success = test
            
            if success:
                print(f"✅ {name} PASSED")
                passed += 1
            else:
                print(f"❌ {name} FAILED")
        except Exception as e:
            print(f"❌ {name} ERROR: {e}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed - library should work in CI!")
    else:
        print("🚨 Tests failed - this explains CI failures!")
        print("💡 These are the REAL problems we need to fix!")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 