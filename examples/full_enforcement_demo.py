#!/usr/bin/env python3
"""
TrustChain Full Enforcement Demo

Demonstrates the complete tool execution enforcement system that prevents
agents from hallucinating tool results by requiring all tool calls to
go through cryptographic verification.
"""

import json
import time
from typing import Dict, Any

# TrustChain imports
from trustchain import (
    get_signature_engine, TrustedTool
)
from trustchain.monitoring.tool_enforcement import (
    create_tool_enforcer,
    wrap_agent_with_enforcement,
    ResponseVerifier
)


print("🛡️ TrustChain Full Enforcement Demo")
print("="*60)
print("Demonstrating COMPLETE protection against agent hallucinations")
print("by enforcing cryptographic verification of ALL tool claims.")
print("="*60)


# ===== STEP 1: Create Verified Tools =====
print("\n🔧 STEP 1: Creating cryptographically verified tools...")

@TrustedTool("weather_api", require_nonce=False)
def get_weather(city: str) -> Dict[str, Any]:
    """Get real weather data (simulated)."""
    weather_data = {
        "city": city,
        "temperature": 18.5,
        "humidity": 72,
        "conditions": "Light rain",
        "wind_speed": 12,
        "timestamp": int(time.time())
    }
    print(f"🌧️  Real weather API called for {city}")
    return weather_data


@TrustedTool("stock_api", require_nonce=False)
def get_stock_price(symbol: str) -> Dict[str, Any]:
    """Get real stock data (simulated)."""
    stock_data = {
        "symbol": symbol.upper(),
        "price": 184.50,
        "change": "+3.25",
        "volume": 2456789,
        "market": "NASDAQ",
        "timestamp": int(time.time())
    }
    print(f"📊 Real stock API called for {symbol}")
    return stock_data


@TrustedTool("news_api", require_nonce=False)
def get_news(topic: str) -> Dict[str, Any]:
    """Get real news data (simulated)."""
    news_data = {
        "topic": topic,
        "headlines": [
            f"Latest developments in {topic}",
            f"Market analysis: {topic} trends",
            f"Expert insights on {topic}"
        ],
        "source_count": 15,
        "timestamp": int(time.time())
    }
    print(f"📰 Real news API called for {topic}")
    return news_data


# ===== STEP 2: Setup Enforcement System =====
print("\n🔒 STEP 2: Setting up enforcement system...")

# Create signature engine
signature_engine = get_signature_engine()

# Create enforcer and register tools
enforcer = create_tool_enforcer(signature_engine, [
    get_weather._trustchain_tool,
    get_stock_price._trustchain_tool,
    get_news._trustchain_tool
])

print(f"✅ Enforcer created with {len(enforcer.registered_tools)} registered tools")


# ===== STEP 3: Simulate Agent Without Enforcement =====
print("\n🚨 STEP 3: Demonstrating agent WITHOUT enforcement (DANGEROUS)...")

class UnprotectedAgent:
    """Simulates an agent that can hallucinate tool results."""
    
    def run(self, query: str) -> str:
        """Simulate agent responses that might include hallucinations."""
        if "weather" in query.lower():
            return """I checked the weather API for New York:
            - Temperature: 25°C (perfect!)  
            - Humidity: 45%
            - Conditions: Sunny and clear
            - Wind: 8 mph from southwest
            
            Great weather for outdoor activities!"""
        
        elif "stock" in query.lower():
            return """I retrieved the latest stock data from our API:
            - AAPL: $195.75 (+4.2%)
            - MSFT: $412.30 (+1.8%) 
            - GOOGL: $142.85 (+2.1%)
            
            Tech stocks are performing well today!"""
        
        elif "news" in query.lower():
            return """I searched our news database for AI developments:
            - 5 major AI breakthroughs announced this week
            - Tech companies investing $50B in AI research
            - New regulations proposed for AI safety
            
            AI sector is very active right now!"""
        
        else:
            return "I can help with weather, stocks, or news information."

# Test unprotected agent
unprotected_agent = UnprotectedAgent()
verifier = ResponseVerifier(enforcer)

print("\n🧪 Testing unprotected agent responses...")

test_queries = [
    "What's the weather in New York?",
    "Give me current stock prices",
    "What's the latest AI news?"
]

for query in test_queries:
    print(f"\n❓ Query: {query}")
    response = unprotected_agent.run(query)
    print(f"🤖 Agent response: {response[:100]}...")
    
    # Verify the response
    verified_response, proofs, unverified = verifier.verify_response(response)
    
    print(f"📊 Verification results:")
    print(f"   ✅ Verified claims: {len(proofs)}")
    print(f"   ❌ Unverified claims: {len(unverified)}")
    print(f"   🚨 DANGER LEVEL: {'🔴 HIGH' if unverified else '🟢 LOW'}")
    
    if unverified:
        print(f"   💀 HALLUCINATED CLAIMS:")
        for claim in unverified[:2]:  # Show first 2
            print(f"      - {claim.claim_text}")


# ===== STEP 4: Demonstrate Enforcement System =====
print("\n\n🛡️ STEP 4: Demonstrating agent WITH enforcement (PROTECTED)...")

class SimulatedEnforcedAgent:
    """Agent that claims to use tools but can be verified."""
    
    def __init__(self, enforcer):
        self.enforcer = enforcer
    
    def run(self, query: str) -> str:
        """Simulate agent that might try to hallucinate, but we can verify."""
        if "weather" in query.lower():
            # Actually execute the tool (this gets recorded)
            execution = self.enforcer.execute_tool("weather_api", "New York")
            
            # Agent response that correctly references the real data
            return f"""I checked the weather API for New York:
            - Temperature: {execution.result['temperature']}°C
            - Humidity: {execution.result['humidity']}%
            - Conditions: {execution.result['conditions']}
            - Request ID: {execution.request_id[:8]}
            
            Current weather conditions retrieved from verified API."""
        
        elif "stock" in query.lower():
            # Mix of real and hallucinated data
            execution = self.enforcer.execute_tool("stock_api", "AAPL")
            
            # Agent tries to add extra info that wasn't from API
            return f"""I retrieved stock information:
            
            Real data from API:
            - AAPL: ${execution.result['price']} ({execution.result['change']})
            
            Additional analysis (NOT from API):
            - MSFT: $412.30 (+1.8%) 
            - GOOGL: $142.85 (+2.1%)
            
            Mixed response with both verified and unverified claims."""
        
        elif "news" in query.lower():
            # Agent makes claims without calling API
            return """I searched for AI news and found:
            - 3 major AI announcements this week
            - $25B invested in AI startups
            - New AI safety guidelines released
            
            This should be flagged as unverified!"""
        
        else:
            return "I can help with weather, stocks, or news."

# Test enforced agent
enforced_agent = SimulatedEnforcedAgent(enforcer)
wrapped_agent = wrap_agent_with_enforcement(enforced_agent, enforcer, strict_mode=False)

print("\n🧪 Testing enforced agent responses...")

for query in test_queries:
    print(f"\n❓ Query: {query}")
    
    # Run agent with enforcement
    result = wrapped_agent.run(query)
    
    print(f"🤖 Agent response (first 150 chars): {result['response'][:150]}...")
    print(f"\n📊 Enforcement results:")
    print(f"   ✅ Verified claims: {len(result['proofs'])}")
    print(f"   ❌ Unverified claims: {len(result['unverified_claims'])}")
    print(f"   🔒 Fully verified: {'YES' if result['fully_verified'] else 'NO'}")
    print(f"   📈 Total tool executions: {result['total_executions']}")
    
    if result['proofs']:
        print(f"   ✅ PROOF SOURCES:")
        for proof in result['proofs']:
            exec_data = proof['execution']
            print(f"      - {exec_data['tool_name']} ({exec_data['request_id'][:8]}) - {proof['confidence_score']:.1%} confidence")
    
    if result['unverified_claims']:
        print(f"   ❌ UNVERIFIED CLAIMS:")
        for claim in result['unverified_claims']:
            print(f"      - {claim['claim_text'][:80]}...")


# ===== STEP 5: Demonstrate Strict Mode =====
print("\n\n🚫 STEP 5: Demonstrating STRICT MODE (Zero tolerance for hallucinations)...")

strict_agent = wrap_agent_with_enforcement(enforced_agent, enforcer, strict_mode=True)

print("\n🧪 Testing strict mode with hallucination attempt...")

hallucination_query = "What's the latest AI news?"
result = strict_agent.run(hallucination_query)

print(f"❓ Query: {hallucination_query}")
print(f"🤖 Agent response: {result['response']}")
print(f"🚫 Verification failed: {result.get('verification_failed', False)}")

if result.get('verification_failed'):
    print(f"✋ BLOCKED: Agent tried to make {len(result['unverified_claims'])} unverified claims")


# ===== STEP 6: Show Verification Dashboard =====
print("\n\n📊 STEP 6: Enforcement System Statistics...")

stats = enforcer.registry.get_stats()
print(f"📈 Registry Statistics:")
print(f"   Total executions: {stats['total_executions']}")
print(f"   Tools registered: {stats['tools_used']}")
print(f"   Recent executions: {stats['recent_count']}")

print(f"\n🔧 Tools used:")
for tool, count in stats['tools'].items():
    print(f"   - {tool}: {count} executions")

recent_executions = enforcer.registry.get_recent_executions(5)
print(f"\n⏰ Recent executions (last 5):")
for execution in recent_executions:
    print(f"   - {execution.tool_name} ({execution.request_id[:8]}) - {execution.execution_time_ms:.1f}ms")


# ===== SUMMARY =====
print("\n" + "="*60)
print("✅ DEMO SUMMARY")
print("="*60)
print("\n🎯 Key Results:")
print("1. 📍 WITHOUT enforcement: Agents can freely hallucinate tool results")
print("2. 🛡️  WITH enforcement: All tool claims are cryptographically verified")
print("3. 🚫 Strict mode: Completely blocks responses with unverified claims")
print("4. 📊 Full audit trail: Every tool execution is tracked and signed")
print("5. ✅ Real-time verification: Claims are matched against real executions")

print(f"\n💡 Benefits achieved:")
print(f"   - 🔒 Cryptographic proof for all tool results")
print(f"   - 🚨 Automatic hallucination detection")
print(f"   - 📋 Complete audit trail of tool usage")
print(f"   - 🎯 User confidence in AI responses")
print(f"   - 🛡️  Protection against false information")

print(f"\n🚀 Next steps:")
print(f"   - Integrate with your existing LangChain agents")
print(f"   - Add custom tools to the enforcer")
print(f"   - Configure strict mode for production")
print(f"   - Monitor verification statistics")

print(f"\n✨ TrustChain: Making AI Agents Verifiably Trustworthy! ✨")


if __name__ == "__main__":
    print("\n🏁 Full enforcement demo completed!")
    print("Run with: python examples/full_enforcement_demo.py") 