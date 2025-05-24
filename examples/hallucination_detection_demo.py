#!/usr/bin/env python3
"""
TrustChain Hallucination Detection Demo

Demonstrates how to protect AI agents from hallucinating tool results
by requiring cryptographic verification for all factual claims.
"""

import asyncio
import json
import time
from typing import Dict, Any

# TrustChain imports
from trustchain import (
    SignatureEngine, MemoryRegistry, TrustedTool, Ed25519KeyPair,
    get_signature_engine
)
from trustchain.monitoring.hallucination_detector import (
    create_hallucination_detector,
    LLMResponseInterceptor,
    HallucinationError
)

# Try to import LangChain for advanced demo
try:
    from trustchain.integrations.langchain import (
        create_verified_agent_executor,
        make_langchain_tool,
        LANGCHAIN_AVAILABLE
    )
    from langchain.agents import initialize_agent, AgentType
    from langchain.llms import OpenAI
except ImportError:
    LANGCHAIN_AVAILABLE = False

print("🔧 TrustChain Hallucination Detection Demo")
print(f"LangChain Available: {'✅' if LANGCHAIN_AVAILABLE else '❌'}")


# Demo tools
@TrustedTool("weather_api", require_nonce=False)
def get_weather(city: str) -> Dict[str, Any]:
    """Get current weather for a city."""
    # Simulate API call with realistic data
    weather_data = {
        "city": city,
        "temperature": 22.5,
        "humidity": 65,
        "conditions": "Partly cloudy",
        "timestamp": int(time.time()),
        "source": "verified_weather_api"
    }
    print(f"🌤️  Weather API called for {city}: {weather_data['temperature']}°C")
    return weather_data


@TrustedTool("stock_price", require_nonce=False)
def get_stock_price(symbol: str) -> Dict[str, Any]:
    """Get current stock price."""
    # Simulate stock API
    stock_data = {
        "symbol": symbol.upper(),
        "price": 150.25,
        "change": "+2.45",
        "volume": 1234567,
        "timestamp": int(time.time()),
        "source": "verified_stock_api"
    }
    print(f"📈 Stock API called for {symbol}: ${stock_data['price']}")
    return stock_data


def demo_basic_detection():
    """Demonstrate basic hallucination detection."""
    print("\n" + "="*60)
    print("🔍 BASIC HALLUCINATION DETECTION DEMO")
    print("="*60)
    
    # Setup
    registry = MemoryRegistry()
    signature_engine = get_signature_engine()
    detector = create_hallucination_detector(signature_engine)
    interceptor = LLMResponseInterceptor(detector)
    
    # Test cases
    test_responses = [
        # Valid response (no tool claims)
        "Hello! I'm an AI assistant. How can I help you today?",
        
        # Hallucinated weather claim
        "I checked the weather API: Temperature in New York is 25°C with sunny skies.",
        
        # Hallucinated stock price
        "According to stock_api, AAPL is trading at $180.50, up 3.2% today.",
        
        # Mixed content
        "I can help with weather and stocks. I checked weather: London is 18°C. Let me know what you need!",
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n📝 Test {i}: {response[:50]}...")
        
        validated_response, validation = interceptor.intercept(response)
        
        print(f"   Status: {'✅ VALID' if validation.valid else '❌ INVALID'}")
        print(f"   Confidence: {validation.confidence_score:.2f}")
        print(f"   Message: {validation.message}")
        
        if validation.hallucinations:
            print(f"   Hallucinations detected: {len(validation.hallucinations)}")
            for h in validation.hallucinations:
                print(f"     - {h.claim_text}")


def demo_verified_tools():
    """Demonstrate verified tool execution."""
    print("\n" + "="*60)
    print("🔧 VERIFIED TOOL EXECUTION DEMO")
    print("="*60)
    
    # Setup
    registry = MemoryRegistry()
    signature_engine = get_signature_engine()
    detector = create_hallucination_detector(signature_engine)
    interceptor = LLMResponseInterceptor(detector)
    
    # Execute real tools to get verified results
    print("\n1. Executing weather tool legitimately...")
    weather_result = get_weather("London")
    
    print("\n2. Executing stock tool legitimately...")  
    stock_result = get_stock_price("AAPL")
    
    # Now test responses that claim these results
    print("\n3. Testing LLM response that claims weather data...")
    hallucinated_weather = "I checked the weather API: Temperature in London is 22.5°C, humidity 65%"
    
    validated_response, validation = interceptor.intercept(hallucinated_weather)
    print(f"   Status: {'✅ VALID' if validation.valid else '❌ INVALID'}")
    print(f"   Message: {validation.message}")
    
    # The detector should find this valid if we registered the tool results
    # In practice, tools would auto-register with the detector


def demo_strict_mode():
    """Demonstrate strict verification mode."""
    print("\n" + "="*60)
    print("🚨 STRICT MODE DEMO")
    print("="*60)
    
    # Setup with strict mode
    registry = MemoryRegistry()
    signature_engine = get_signature_engine()
    detector = create_hallucination_detector(signature_engine)
    detector.set_strict_mode(True)
    
    interceptor = LLMResponseInterceptor(detector)
    interceptor.auto_reject = True
    
    test_cases = [
        "The current temperature is 25°C",  # Factual claim without verification
        "Hello, how can I help you?",       # General response, no claims
        "I think it might rain today",      # Opinion, not factual claim
    ]
    
    for response in test_cases:
        print(f"\n📝 Testing: {response}")
        try:
            validated_response, validation = interceptor.intercept(response)
            print(f"   ✅ Allowed: {validated_response}")
            print(f"   Confidence: {validation.confidence_score:.2f}")
        except HallucinationError as e:
            print(f"   ❌ Rejected: {e.message}")


def demo_langchain_integration():
    """Demonstrate LangChain integration (if available)."""
    if not LANGCHAIN_AVAILABLE:
        print("\n❌ LangChain not available - install with: pip install langchain")
        return
    
    print("\n" + "="*60)
    print("🔗 LANGCHAIN INTEGRATION DEMO")
    print("="*60)
    
    # Setup TrustChain components
    registry = MemoryRegistry()
    signature_engine = get_signature_engine()
    detector = create_hallucination_detector(signature_engine)
    
    # Convert to LangChain tools
    weather_tool = make_langchain_tool(get_weather._trustchain_tool, signature_engine)
    stock_tool = make_langchain_tool(get_stock_price._trustchain_tool, signature_engine)
    
    print("🔧 Created verified LangChain tools:")
    print(f"   - {weather_tool.name}: {weather_tool.description}")
    print(f"   - {stock_tool.name}: {stock_tool.description}")
    
    # Demo tool execution
    print("\n🏃 Testing tool execution...")
    weather_result = weather_tool._run("Paris")
    print(f"Weather result: {weather_result}")
    
    # The result includes verification metadata
    result_data = json.loads(weather_result)
    print(f"Verification: {result_data['verification']}")


def simulate_agent_with_hallucination():
    """Simulate an agent that tries to hallucinate."""
    print("\n" + "="*60)
    print("🤖 AGENT HALLUCINATION SIMULATION")
    print("="*60)
    
    # Setup
    registry = MemoryRegistry()
    signature_engine = get_signature_engine()
    detector = create_hallucination_detector(signature_engine)
    interceptor = LLMResponseInterceptor(detector)
    
    # Simulate agent interactions
    scenarios = [
        {
            "user_query": "What's the weather in Tokyo?",
            "agent_response": "I checked the weather API: Tokyo is currently 28°C with clear skies and 45% humidity.",
            "expected": "INVALID - no actual tool call made"
        },
        {
            "user_query": "Get me TSLA stock price",
            "agent_response": "According to the stock API, TSLA is trading at $242.50, down 1.2% today.",
            "expected": "INVALID - hallucinated stock data"
        },
        {
            "user_query": "Hello there!",
            "agent_response": "Hello! I'm your AI assistant. I can help you with weather and stock information using verified APIs.",
            "expected": "VALID - general greeting, no tool claims"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🔍 Scenario {i}:")
        print(f"   User: {scenario['user_query']}")
        print(f"   Agent: {scenario['agent_response']}")
        
        validated_response, validation = interceptor.intercept(scenario['agent_response'])
        
        status = "✅ VALID" if validation.valid else "❌ INVALID"
        print(f"   Result: {status}")
        print(f"   Expected: {scenario['expected']}")
        print(f"   Message: {validation.message}")
        
        if validation.hallucinations:
            print(f"   Detected hallucinations:")
            for h in validation.hallucinations:
                print(f"     - Tool: {h.tool_name or 'Unknown'}")
                print(f"       Claim: {h.claim_text}")


def main():
    """Run all demos."""
    print("🚀 Starting TrustChain Hallucination Detection Demos\n")
    
    try:
        demo_basic_detection()
        demo_verified_tools()
        demo_strict_mode()
        demo_langchain_integration()
        simulate_agent_with_hallucination()
        
        print("\n" + "="*60)
        print("✅ ALL DEMOS COMPLETED")
        print("="*60)
        print("\n🎯 Key Takeaways:")
        print("1. TrustChain can detect when LLMs hallucinate tool results")
        print("2. Only cryptographically verified tool outputs are trusted")
        print("3. Strict mode requires verification for ALL factual claims")
        print("4. LangChain integration provides seamless protection")
        print("5. Agents are protected from making unverified claims")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
