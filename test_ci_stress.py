#!/usr/bin/env python3
"""
🔥 CI Stress Test - Race Conditions & Edge Cases

This test tries to reproduce the EXACT failure conditions that happen in CI:
- Parallel tool creation (race conditions)
- Mixed sync/async execution
- Global state pollution
- Memory pressure
- Timing-sensitive operations

Author: Ed Cherednik
"""

import asyncio
import threading
import time
import sys
import gc
from concurrent.futures import ThreadPoolExecutor
import subprocess

async def test_parallel_tool_creation():
    """Test parallel tool creation - common source of race conditions."""
    print("🏃‍♂️ Testing parallel tool creation...")
    
    # Reset global state
    modules_to_clear = [mod for mod in sys.modules.keys() if mod.startswith('trustchain')]
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]
    
    from trustchain import TrustedTool
    
    # Create multiple tools in parallel
    tools = []
    
    def create_tool(i):
        @TrustedTool(f"parallel_tool_{i}")
        async def parallel_tool(data: str):
            return {"tool_id": i, "data": data}
        return parallel_tool
    
    # Create tools in parallel threads (like CI might do)
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(create_tool, i) for i in range(10)]
        tools = [f.result() for f in futures]
    
    # Try to use them all
    results = []
    for i, tool in enumerate(tools):
        try:
            result = await tool(f"test_{i}")
            results.append(result.is_verified)
            print(f"   Tool {i}: {'✅' if result.is_verified else '❌'}")
        except Exception as e:
            print(f"   Tool {i}: ❌ Failed: {e}")
            results.append(False)
    
    success = all(results)
    print(f"   Result: {'✅ All parallel tools work' if success else '❌ Some tools failed'}")
    return success

async def test_global_state_pollution():
    """Test if global state gets polluted between operations."""
    print("🦠 Testing global state pollution...")
    
    from trustchain import TrustedTool
    from trustchain.core.signatures import get_signature_engine
    
    # Check initial state
    initial_engine = get_signature_engine()
    initial_signers = len(initial_engine._signers) if initial_engine else 0
    print(f"   Initial signers: {initial_signers}")
    
    # Create tools and mess with global state
    @TrustedTool("pollution_test_1")
    async def tool1(data: str):
        return {"source": "tool1", "data": data}
    
    @TrustedTool("pollution_test_2") 
    async def tool2(data: str):
        return {"source": "tool2", "data": data}
    
    # Use tools
    result1 = await tool1("test")
    result2 = await tool2("test")
    
    # Check if state is polluted
    final_engine = get_signature_engine()
    final_signers = len(final_engine._signers) if final_engine else 0
    print(f"   Final signers: {final_signers}")
    
    # Each tool should create its own signer
    expected_growth = 2  # tool1 + tool2
    actual_growth = final_signers - initial_signers
    
    if actual_growth != expected_growth:
        print(f"   ❌ Unexpected signer growth: {actual_growth} (expected {expected_growth})")
        return False
    
    if not (result1.is_verified and result2.is_verified):
        print(f"   ❌ Tools not verified: tool1={result1.is_verified}, tool2={result2.is_verified}")
        return False
    
    print("   ✅ Global state clean")
    return True

def test_memory_pressure():
    """Test under memory pressure conditions."""
    print("💾 Testing under memory pressure...")
    
    try:
        # Create memory pressure
        big_data = []
        for i in range(100):
            big_data.append([0] * 10000)  # Allocate some memory
        
        # Force garbage collection
        gc.collect()
        
        # Test subprocess under pressure
        test_code = '''
import asyncio
from trustchain import TrustedTool

@TrustedTool("memory_pressure_tool")
async def pressure_tool(data: str):
    return {"processed": data, "size": len(data)}

async def main():
    try:
        result = await pressure_tool("test_data")
        print(f"SUCCESS: {result.is_verified}")
        return 0
    except Exception as e:
        print(f"FAILED: {e}")
        return 1

exit(asyncio.run(main()))
        '''
        
        result = subprocess.run([sys.executable, "-c", test_code], 
                              capture_output=True, text=True, timeout=30)
        
        success = result.returncode == 0 and "SUCCESS: True" in result.stdout
        print(f"   {'✅' if success else '❌'} Memory pressure test: {result.stdout.strip()}")
        if result.stderr:
            print(f"   Stderr: {result.stderr.strip()}")
        
        return success
        
    except Exception as e:
        print(f"   ❌ Memory pressure test failed: {e}")
        return False

async def test_timing_sensitivity():
    """Test timing-sensitive operations that might fail in CI."""
    print("⏰ Testing timing-sensitive operations...")
    
    from trustchain import TrustedTool
    
    # Create tool with very fast execution
    @TrustedTool("timing_test_tool")
    async def timing_tool(data: str):
        # No delay - test immediate execution
        return {"data": data, "timestamp": time.time()}
    
    # Execute multiple times rapidly
    results = []
    start_time = time.time()
    
    for i in range(20):
        try:
            result = await timing_tool(f"rapid_{i}")
            results.append(result.is_verified)
        except Exception as e:
            print(f"   ❌ Rapid execution {i} failed: {e}")
            results.append(False)
    
    end_time = time.time()
    duration = end_time - start_time
    
    success_rate = sum(results) / len(results)
    print(f"   Rapid execution: {len(results)} calls in {duration:.3f}s")
    print(f"   Success rate: {success_rate:.2%}")
    
    if success_rate < 0.95:  # 95% success rate required
        print("   ❌ Too many timing failures")
        return False
    
    print("   ✅ Timing-sensitive operations passed")
    return True

async def test_mixed_sync_async():
    """Test mixed sync/async execution patterns."""
    print("🔄 Testing mixed sync/async patterns...")
    
    from trustchain import TrustedTool
    
    # Mix of sync and async tools
    @TrustedTool("sync_tool")
    def sync_tool(data: str):
        return {"type": "sync", "data": data}
    
    @TrustedTool("async_tool")
    async def async_tool(data: str):
        await asyncio.sleep(0.01)  # Small delay
        return {"type": "async", "data": data}
    
    # Execute them in mixed pattern
    try:
        result1 = await sync_tool("test1")
        result2 = await async_tool("test2") 
        result3 = await sync_tool("test3")
        
        all_verified = all([result1.is_verified, result2.is_verified, result3.is_verified])
        
        if not all_verified:
            print(f"   ❌ Mixed execution failed: sync1={result1.is_verified}, async={result2.is_verified}, sync2={result3.is_verified}")
            return False
        
        print("   ✅ Mixed sync/async execution passed")
        return True
        
    except Exception as e:
        print(f"   ❌ Mixed execution error: {e}")
        return False

async def test_edge_case_operations():
    """Test edge cases that might break in CI."""
    print("🔍 Testing edge cases...")
    
    from trustchain import TrustedTool
    
    # Edge case: Empty data
    @TrustedTool("edge_case_tool")
    async def edge_tool(data):
        return {"input": data, "type": type(data).__name__}
    
    edge_cases = [
        ("", "empty string"),
        (None, "None value"),
        ({}, "empty dict"),
        ([], "empty list"),
        (0, "zero"),
        (False, "False boolean"),
    ]
    
    results = []
    for data, desc in edge_cases:
        try:
            result = await edge_tool(data)
            success = result.is_verified
            print(f"   {desc}: {'✅' if success else '❌'}")
            results.append(success)
        except Exception as e:
            print(f"   {desc}: ❌ Error: {e}")
            results.append(False)
    
    success_rate = sum(results) / len(results)
    print(f"   Edge cases success rate: {success_rate:.2%}")
    
    return success_rate > 0.8  # Allow some edge cases to fail

async def main():
    """Run all stress tests."""
    print("🔥 CI Stress Test - Finding the Real Problems!")
    print("=" * 60)
    
    tests = [
        ("Parallel tool creation", test_parallel_tool_creation()),
        ("Global state pollution", test_global_state_pollution()),
        ("Memory pressure", test_memory_pressure()),
        ("Timing sensitivity", test_timing_sensitivity()),
        ("Mixed sync/async", test_mixed_sync_async()),
        ("Edge cases", test_edge_case_operations()),
    ]
    
    passed = 0
    total = len(tests)
    failed_tests = []
    
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
                failed_tests.append(name)
        except Exception as e:
            print(f"💥 {name} CRASHED: {e}")
            failed_tests.append(f"{name} (crashed)")
    
    print(f"\n📊 Stress Test Results: {passed}/{total} passed")
    
    if failed_tests:
        print("🚨 Failed tests:")
        for test in failed_tests:
            print(f"   • {test}")
        print("\n💡 These failures might explain CI problems!")
    else:
        print("🎉 All stress tests passed!")
        print("🤔 CI failures might be environment-specific...")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 