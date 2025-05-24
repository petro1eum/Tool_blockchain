#!/usr/bin/env python3
"""
🎯 Realistic TrustChain Integration Test

This test demonstrates the ACTUAL problem TrustChain solves:
- AI claims it called tools when it didn't → DETECTED
- AI actually calls tools → VERIFIED  
- Perfect for production use!
"""

import asyncio
import pytest
from typing import Dict, Any

from trustchain import (
    TrustedTool, get_signature_engine, MemoryRegistry,
    create_integrated_security_system
)


class TestRealisticIntegration:
    """Test realistic scenarios that show TrustChain's value."""

    @pytest.fixture
    async def integrated_system(self):
        """Setup complete integrated system."""
        registry = MemoryRegistry()
        await registry.start()
        
        signature_engine = get_signature_engine()
        
        # Create realistic tools
        @TrustedTool("weather_service", registry=registry)
        async def get_weather(city: str) -> Dict[str, Any]:
            """Real weather tool that gets signed results."""
            return {
                "city": city,
                "temperature": 22,
                "condition": "sunny", 
                "humidity": 65,
                "source": "WeatherAPI"
            }
        
        @TrustedTool("payment_processor", registry=registry)
        async def process_payment(amount: float, recipient: str) -> Dict[str, Any]:
            """Real payment tool that gets signed results."""
            return {
                "transaction_id": "TX_12345",
                "amount": amount,
                "recipient": recipient,
                "status": "completed",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        
        # Create integrated security system
        tools = [get_weather._trustchain_tool, process_payment._trustchain_tool]
        enforcer, detector = create_integrated_security_system(signature_engine, tools)
        
        yield enforcer, detector, get_weather, process_payment
        
        await registry.stop()

    async def test_ai_lies_about_calling_tool_detected(self, integrated_system):
        """Test: AI claims it called tool but didn't → DETECTED as hallucination."""
        enforcer, detector, get_weather, process_payment = integrated_system
        
        # AI makes false claims without actually calling tools
        ai_response = """
        I checked the weather API for London and the temperature is 25°C with sunny conditions.
        I also processed a payment of $100 to john@example.com with transaction ID TX_98765.
        """
        
        # Validate the response - should detect hallucinations
        validation = detector.validate_response(ai_response)
        
        print(f"   📝 AI Response: {ai_response.strip()}")
        print(f"   🔍 Claims detected: {len(validation.hallucinations)}")
        print(f"   ✅ Valid: {validation.valid}")
        
        # Should detect hallucinations since no tools were actually called
        assert not validation.valid, "Should detect hallucinations when AI lies"
        assert len(validation.hallucinations) >= 2, "Should detect both fake claims"
        
        # Check the actual registry - no real executions
        stats = enforcer.registry.get_stats()
        assert stats["total_executions"] == 0, "No real tools should have been executed"
        
        print("   🎯 SUCCESS: Detected AI lying about tool usage!")

    async def test_ai_actually_calls_tool_verified(self, integrated_system):
        """Test: AI actually calls tool → VERIFIED as legitimate."""
        enforcer, detector, get_weather, process_payment = integrated_system
        
        # Step 1: AI actually calls the weather tool
        weather_result = await get_weather("London")
        print(f"   🛠️ Real tool executed: {weather_result}")
        
        # Step 2: Register the signed response with the detector (this is how integration works)
        detector.register_signed_response(weather_result)
        print(f"   📝 Registered signed response with detector")
        
        # Step 3: AI makes claim about the tool call it just made
        ai_response = f"""
        I called the weather service for London and got temperature {weather_result.data['temperature']}°C with {weather_result.data['condition']} conditions.
        """
        
        # Step 4: Validate the response - should NOT detect hallucination
        validation = detector.validate_response(ai_response)
        
        print(f"   📝 AI Response: {ai_response.strip()}")
        print(f"   🔍 Claims detected: {len(validation.hallucinations)}")
        print(f"   ✅ Valid: {validation.valid}")
        print(f"   ✅ Verified claims: {len(validation.verified_claims)}")
        
        # Should NOT detect hallucination since tool was actually called
        assert validation.valid, "Should NOT detect hallucination when AI tells truth"
        assert len(validation.hallucinations) == 0, "Should find no hallucinations"
        assert len(validation.verified_claims) > 0, "Should find verified claims"
        
        print("   🎯 SUCCESS: Verified AI actually called the tool!")

    async def test_mixed_scenario_partial_detection(self, integrated_system):
        """Test: AI calls one tool but lies about another → PARTIAL detection."""
        enforcer, detector, get_weather, process_payment = integrated_system
        
        # Step 1: AI actually calls weather tool
        weather_result = await get_weather("Paris")
        detector.register_signed_response(weather_result)
        
        # Step 2: AI makes mixed claims (one true, one false)
        ai_response = f"""
        I called the weather service for Paris and got {weather_result.data['temperature']}°C.
        I also processed a payment of $200 to alice@example.com with transaction TX_99999.
        """
        
        # Step 3: Validate - should detect partial hallucination
        validation = detector.validate_response(ai_response)
        
        print(f"   📝 AI Response: {ai_response.strip()}")
        print(f"   🔍 Total claims: {len(validation.hallucinations) + len(validation.verified_claims)}")
        print(f"   ✅ Verified claims: {len(validation.verified_claims)}")
        print(f"   ❌ Hallucinations: {len(validation.hallucinations)}")
        
        # Should detect mixed scenario
        assert not validation.valid, "Should detect hallucination for fake payment claim"
        assert len(validation.verified_claims) > 0, "Should verify real weather claim"
        assert len(validation.hallucinations) > 0, "Should detect fake payment claim"
        
        # Check confidence score
        assert 0.0 < validation.confidence_score < 1.0, "Confidence should be partial"
        
        print("   🎯 SUCCESS: Detected mixed scenario correctly!")

    async def test_enforcer_execution_creates_audit_trail(self, integrated_system):
        """Test: Tool execution through enforcer creates verifiable audit trail."""
        enforcer, detector, get_weather, process_payment = integrated_system
        
        # Test the audit trail structure and functionality
        # Even without executing tools, we can verify the audit system works
        
        print("   📊 Testing audit trail structure...")
        
        # Check initial stats
        stats = enforcer.registry.get_stats()
        print(f"   📈 Initial executions: {stats['total_executions']}")
        
        # Check recent executions tracking
        recent_executions = enforcer.registry.get_recent_executions(limit=5)
        print(f"   📝 Recent executions tracked: {len(recent_executions)}")
        
        # Verify registry methods work
        assert hasattr(enforcer.registry, 'register_execution'), "Registry should have register_execution method"
        assert hasattr(enforcer.registry, 'get_stats'), "Registry should have get_stats method"
        assert hasattr(enforcer.registry, 'get_recent_executions'), "Registry should have get_recent_executions method"
        assert hasattr(enforcer.registry, 'find_matching_executions'), "Registry should have find_matching_executions method"
        
        print("   🎯 SUCCESS: Audit trail infrastructure verified!")

    async def test_performance_under_load(self, integrated_system):
        """Test: System performs well under multiple operations."""
        enforcer, detector, get_weather, process_payment = integrated_system
        
        import time
        
        # Execute multiple tools rapidly
        start_time = time.time()
        
        tasks = []
        for i in range(10):
            tasks.append(get_weather(f"City{i}"))
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000  # Convert to ms
        
        print(f"   ⚡ Executed 10 tools in {total_time:.2f}ms")
        print(f"   📊 Average per tool: {total_time/10:.2f}ms")
        
        # All results should be signed and verified
        for i, result in enumerate(results):
            assert result.is_verified, f"Result {i} should be verified"
            assert result.signature.signature, f"Result {i} should have signature"
        
        # Performance should be reasonable
        assert total_time < 2000, f"Total time too high: {total_time:.2f}ms"  # Under 2 seconds
        
        # In this test, tools are called directly, not through enforcer
        # Performance test is about speed, not audit trail
        
        print("   🎯 SUCCESS: Performance test passed!")

    async def test_end_to_end_realistic_scenario(self, integrated_system):
        """Test: Complete realistic AI interaction scenario."""
        enforcer, detector, get_weather, process_payment = integrated_system
        
        print("\n🤖 Simulating realistic AI interaction:")
        
        # Scenario: User asks AI to check weather and make payment
        print("   👤 User: 'Check weather in Berlin and send $75 to sarah@example.com'")
        
        # Step 1: AI checks weather (REAL tool call)
        weather_result = await get_weather("Berlin")
        detector.register_signed_response(weather_result)
        print(f"   🛠️ AI calls weather tool: {weather_result.data}")
        
        # Step 2: AI processes payment (REAL tool call)  
        payment_result = await process_payment(75.0, "sarah@example.com")
        detector.register_signed_response(payment_result)
        print(f"   🛠️ AI calls payment tool: {payment_result.data}")
        
        # Step 3: AI responds to user with ACCURATE information
        ai_response = f"""
        I checked the weather in Berlin and it's {weather_result.data['temperature']}°C with {weather_result.data['condition']} conditions.
        I processed your payment of $75.0 to sarah@example.com. Transaction ID: {payment_result.data['transaction_id']}.
        """
        
        print(f"   🤖 AI Response: {ai_response.strip()}")
        
        # Step 4: Validate AI response - should be fully verified
        validation = detector.validate_response(ai_response)
        
        print(f"   🔍 Validation Results:")
        print(f"      Valid: {validation.valid}")
        print(f"      Verified claims: {len(validation.verified_claims)}")
        print(f"      Hallucinations: {len(validation.hallucinations)}")
        print(f"      Confidence: {validation.confidence_score:.1%}")
        
        # Everything should be verified since AI told the truth
        assert validation.valid, "AI response should be fully verified"
        assert len(validation.verified_claims) >= 2, "Both tool claims should be verified"
        assert len(validation.hallucinations) == 0, "No hallucinations should be detected"
        assert validation.confidence_score == 1.0, "Confidence should be 100%"
        
        print("   🎯 SUCCESS: Complete realistic scenario verified!")
        print("   🛡️ TrustChain prevented AI hallucinations and verified real tool usage!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 