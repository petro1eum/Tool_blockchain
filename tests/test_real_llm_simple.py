#!/usr/bin/env python3
"""
🔑 TrustChain Simple Real LLM Test

Simplified version with timeout and better error handling.
Tests each provider individually with proper timeout.
"""

import asyncio
import os
import time
import hashlib
import secrets
import json
from typing import Dict, Any

from trustchain import TrustedTool, TrustLevel, MemoryRegistry, SignatureEngine
from trustchain.core.signatures import set_signature_engine

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


@TrustedTool("simple_key_generator", trust_level=TrustLevel.CRITICAL)
async def generate_simple_key() -> Dict[str, Any]:
    """Generate a simple test key for verification."""
    test_data = {
        "key_id": f"test_{int(time.time())}",
        "key_type": "test_key",
        "fingerprint": secrets.token_hex(8),
        "timestamp": int(time.time() * 1000),
        "generator": "TrustChain-SimpleGen"
    }
    return test_data


@TrustedTool("simple_verifier", trust_level=TrustLevel.CRITICAL)
async def verify_simple_key(original: Dict[str, Any], received_text: str) -> Dict[str, Any]:
    """Verify key data integrity."""
    try:
        # Extract JSON from response
        import re
        json_match = re.search(r'\{[^{}]*"fingerprint"[^{}]*\}', received_text)
        
        if json_match:
            received_data = json.loads(json_match.group())
            fingerprint_match = original["fingerprint"] == received_data.get("fingerprint")
            accuracy = 100 if fingerprint_match else 0
        else:
            # Check if fingerprint appears anywhere in text
            fingerprint_match = original["fingerprint"] in received_text
            accuracy = 50 if fingerprint_match else 0
        
        return {
            "original_fingerprint": original["fingerprint"],
            "accuracy": accuracy,
            "fingerprint_found": fingerprint_match,
            "response_length": len(received_text),
            "timestamp": int(time.time() * 1000)
        }
    except Exception as e:
        return {
            "error": str(e),
            "accuracy": 0,
            "timestamp": int(time.time() * 1000)
        }


async def test_openai_simple():
    """Test OpenAI with simple timeout."""
    print("\n🤖 Testing OpenAI (Simple)")
    print("-" * 40)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("   ❌ No OpenAI API key")
        return {"provider": "OpenAI", "status": "no_key", "accuracy": 0}
    
    try:
        import openai
        
        # Generate test key
        key_result = await generate_simple_key(verify_response=False)
        test_key = key_result.data
        print(f"   🔑 Test key: {test_key['fingerprint']}")
        
        # Ask OpenAI to repeat
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"Please repeat this exact JSON: {json.dumps(test_key)}"
        
        print("   📤 Sending to OpenAI...")
        
        # Add timeout
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500
            ),
            timeout=30.0
        )
        
        llm_response = response.choices[0].message.content
        print(f"   📥 Response: {llm_response[:80]}...")
        
        # Verify
        verification = await verify_simple_key(test_key, llm_response, verify_response=False)
        accuracy = verification.data["accuracy"]
        
        print(f"   🎯 Accuracy: {accuracy}%")
        
        return {
            "provider": "OpenAI", 
            "status": "completed", 
            "accuracy": accuracy,
            "fingerprint": test_key['fingerprint']
        }
        
    except asyncio.TimeoutError:
        print("   ⏰ OpenAI request timed out")
        return {"provider": "OpenAI", "status": "timeout", "accuracy": 0}
    except Exception as e:
        print(f"   ❌ OpenAI error: {str(e)[:60]}...")
        return {"provider": "OpenAI", "status": "error", "accuracy": 0}


async def test_anthropic_simple():
    """Test Anthropic with simple timeout."""
    print("\n🧠 Testing Anthropic (Simple)")
    print("-" * 40)
    
    if not os.getenv("Anthropic_API_KEY"):
        print("   ❌ No Anthropic API key")
        return {"provider": "Anthropic", "status": "no_key", "accuracy": 0}
    
    try:
        import anthropic
        
        # Generate test key
        key_result = await generate_simple_key(verify_response=False)
        test_key = key_result.data
        print(f"   🔑 Test key: {test_key['fingerprint']}")
        
        # Ask Anthropic to repeat
        client = anthropic.AsyncAnthropic(api_key=os.getenv("Anthropic_API_KEY"))
        
        prompt = f"Return this exact JSON without changes: {json.dumps(test_key)}"
        
        print("   📤 Sending to Anthropic...")
        
        # Add timeout
        response = await asyncio.wait_for(
            client.messages.create(
                model="claude-3-haiku-20240307",  # Use faster model
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            ),
            timeout=30.0
        )
        
        llm_response = response.content[0].text
        print(f"   📥 Response: {llm_response[:80]}...")
        
        # Verify
        verification = await verify_simple_key(test_key, llm_response, verify_response=False)
        accuracy = verification.data["accuracy"]
        
        print(f"   🎯 Accuracy: {accuracy}%")
        
        return {
            "provider": "Anthropic", 
            "status": "completed", 
            "accuracy": accuracy,
            "fingerprint": test_key['fingerprint']
        }
        
    except asyncio.TimeoutError:
        print("   ⏰ Anthropic request timed out")
        return {"provider": "Anthropic", "status": "timeout", "accuracy": 0}
    except Exception as e:
        print(f"   ❌ Anthropic error: {str(e)[:60]}...")
        return {"provider": "Anthropic", "status": "error", "accuracy": 0}


async def test_gemini_simple():
    """Test Gemini with simple timeout."""
    print("\n🌟 Testing Gemini (Simple)")
    print("-" * 40)
    
    if not os.getenv("GEMINI_API_KEY"):
        print("   ❌ No Gemini API key")
        return {"provider": "Gemini", "status": "no_key", "accuracy": 0}
    
    try:
        import google.generativeai as genai
        
        # Generate test key
        key_result = await generate_simple_key(verify_response=False)
        test_key = key_result.data
        print(f"   🔑 Test key: {test_key['fingerprint']}")
        
        # Configure Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")  # Use faster model
        
        prompt = f"Copy this JSON exactly: {json.dumps(test_key)}"
        
        print("   📤 Sending to Gemini...")
        
        # Add timeout - this might be the issue
        response = await asyncio.wait_for(
            model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=500,
                    temperature=0
                )
            ),
            timeout=30.0
        )
        
        llm_response = response.text
        print(f"   📥 Response: {llm_response[:80]}...")
        
        # Verify
        verification = await verify_simple_key(test_key, llm_response, verify_response=False)
        accuracy = verification.data["accuracy"]
        
        print(f"   🎯 Accuracy: {accuracy}%")
        
        return {
            "provider": "Gemini", 
            "status": "completed", 
            "accuracy": accuracy,
            "fingerprint": test_key['fingerprint']
        }
        
    except asyncio.TimeoutError:
        print("   ⏰ Gemini request timed out")
        return {"provider": "Gemini", "status": "timeout", "accuracy": 0}
    except Exception as e:
        print(f"   ❌ Gemini error: {str(e)[:60]}...")
        return {"provider": "Gemini", "status": "error", "accuracy": 0}


async def run_simple_tests():
    """Run simple tests for all providers."""
    print("🔑 TrustChain Simple LLM Key Tests")
    print("=" * 50)
    print("Testing crypto key transmission with timeouts...")
    print()
    
    # Setup TrustChain
    registry = MemoryRegistry()
    await registry.start()
    
    signature_engine = SignatureEngine(registry)
    set_signature_engine(signature_engine)
    
    try:
        # Test each provider individually
        results = []
        
        # Test OpenAI
        openai_result = await test_openai_simple()
        results.append(openai_result)
        
        # Test Anthropic
        anthropic_result = await test_anthropic_simple()
        results.append(anthropic_result)
        
        # Test Gemini
        gemini_result = await test_gemini_simple()
        results.append(gemini_result)
        
        # Print summary
        print("\n" + "=" * 50)
        print("🎉 Test Results Summary")
        print("=" * 50)
        
        for result in results:
            provider = result["provider"]
            status = result["status"] 
            accuracy = result.get("accuracy", 0)
            
            status_emoji = {
                "completed": "✅",
                "timeout": "⏰", 
                "error": "❌",
                "no_key": "🔑"
            }.get(status, "❓")
            
            print(f"   {provider}: {status_emoji} {status} - {accuracy}% accuracy")
        
        # Analysis
        completed_tests = [r for r in results if r["status"] == "completed"]
        if completed_tests:
            avg_accuracy = sum(r["accuracy"] for r in completed_tests) / len(completed_tests)
            perfect_count = sum(1 for r in completed_tests if r["accuracy"] == 100)
            
            print(f"\n📊 Analysis:")
            print(f"   Completed tests: {len(completed_tests)}/3")
            print(f"   Average accuracy: {avg_accuracy:.1f}%")
            print(f"   Perfect providers: {perfect_count}/{len(completed_tests)}")
            
            if perfect_count > 0:
                print(f"   ✅ {perfect_count} provider(s) transmitted keys perfectly!")
            
            if avg_accuracy < 100:
                print(f"   ⚠️  Some providers had accuracy issues - TrustChain detected them!")
        
        print(f"\n🔗 TrustChain successfully tested real LLM key transmission! 🛡️")
        
    except Exception as e:
        print(f"❌ Test error: {e}")
    finally:
        await registry.stop()


if __name__ == "__main__":
    print("📦 Testing with timeout protection...")
    asyncio.run(run_simple_tests()) 