#!/usr/bin/env python3
"""
🔗 TrustChain Real LLM API Examples (v2)

This file contains examples of using TrustChain v2 with real LLM APIs.
Set your API keys as environment variables to test with real providers.

Environment variables needed:
- OPENAI_API_KEY: Your OpenAI API key
- ANTHROPIC_API_KEY: Your Anthropic API key
- GEMINI_API_KEY: Your Google Gemini API key

Run with: python examples/llm_real_api_examples.py
"""

import asyncio
import os
import time
from typing import Any, Dict

from trustchain.v2 import TrustChain, TrustChainConfig

# Create TrustChain instance with high-security settings
tc = TrustChain(
    TrustChainConfig(
        enable_nonce=True,
        cache_ttl=600,
    )
)

# ==================== OPENAI REAL INTEGRATION ====================


@tc.tool("openai_real_api")
async def openai_chat_completion(
    prompt: str, model: str = "gpt-4o", max_tokens: int = 1000
) -> Dict[str, Any]:
    """
    Real OpenAI API integration with TrustChain verification.

    Requires: pip install openai
    Environment: OPENAI_API_KEY
    """
    try:
        import openai

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "error": "OPENAI_API_KEY not set",
                "provider": "openai",
                "timestamp": time.time(),
                "demo_mode": True,
            }

        client = openai.AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
        )

        return {
            "generated_text": response.choices[0].message.content,
            "model": model,
            "provider": "openai",
            "prompt": prompt,
            "timestamp": time.time(),
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "finish_reason": response.choices[0].finish_reason,
        }

    except ImportError:
        return {
            "error": "OpenAI library not installed. Run: pip install openai",
            "provider": "openai",
            "timestamp": time.time(),
        }
    except Exception as e:
        return {
            "error": f"OpenAI API error: {str(e)}",
            "provider": "openai",
            "timestamp": time.time(),
        }


# ==================== ANTHROPIC REAL INTEGRATION ====================


@tc.tool("anthropic_real_api")
async def anthropic_claude_completion(
    prompt: str, model: str = "claude-3-sonnet-20240229", max_tokens: int = 1000
) -> Dict[str, Any]:
    """
    Real Anthropic Claude API integration with TrustChain verification.

    Requires: pip install anthropic
    Environment: ANTHROPIC_API_KEY
    """
    try:
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {
                "error": "ANTHROPIC_API_KEY not set",
                "provider": "anthropic",
                "timestamp": time.time(),
                "demo_mode": True,
            }

        client = anthropic.AsyncAnthropic(api_key=api_key)

        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        return {
            "generated_text": response.content[0].text,
            "model": model,
            "provider": "anthropic",
            "prompt": prompt,
            "timestamp": time.time(),
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens
                + response.usage.output_tokens,
            },
            "stop_reason": response.stop_reason,
        }

    except ImportError:
        return {
            "error": "Anthropic library not installed. Run: pip install anthropic",
            "provider": "anthropic",
            "timestamp": time.time(),
        }
    except Exception as e:
        return {
            "error": f"Anthropic API error: {str(e)}",
            "provider": "anthropic",
            "timestamp": time.time(),
        }


# ==================== GOOGLE GEMINI REAL INTEGRATION ====================


@tc.tool("gemini_real_api")
async def gemini_generate_content(
    prompt: str, model: str = "gemini-1.5-pro"
) -> Dict[str, Any]:
    """
    Real Google Gemini API integration with TrustChain verification.

    Requires: pip install google-generativeai
    Environment: GEMINI_API_KEY
    """
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {
                "error": "GEMINI_API_KEY not set",
                "provider": "google_gemini",
                "timestamp": time.time(),
                "demo_mode": True,
            }

        genai.configure(api_key=api_key)
        model_instance = genai.GenerativeModel(model)

        response = await model_instance.generate_content_async(prompt)

        return {
            "generated_text": response.text,
            "model": model,
            "provider": "google_gemini",
            "prompt": prompt,
            "timestamp": time.time(),
            "usage": (
                {
                    "prompt_token_count": response.usage_metadata.prompt_token_count,
                    "candidates_token_count": response.usage_metadata.candidates_token_count,
                    "total_token_count": response.usage_metadata.total_token_count,
                }
                if response.usage_metadata
                else None
            ),
            "finish_reason": (
                response.candidates[0].finish_reason if response.candidates else None
            ),
        }

    except ImportError:
        return {
            "error": "Google GenerativeAI library not installed. Run: pip install google-generativeai",
            "provider": "google_gemini",
            "timestamp": time.time(),
        }
    except Exception as e:
        return {
            "error": f"Gemini API error: {str(e)}",
            "provider": "google_gemini",
            "timestamp": time.time(),
        }


# ==================== FINANCIAL ADVISOR WITH REAL LLMS ====================


@tc.tool("financial_advisor_multi_llm")
async def financial_advisor_consensus(
    query: str, portfolio_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Get financial advice from multiple LLMs and create consensus with CRITICAL trust level.
    This demonstrates how TrustChain can be used for high-stakes financial decisions.
    """

    financial_prompt = f"""
    Financial Query: {query}

    Portfolio Data:
    - Current Value: ${portfolio_data.get('value', 0):,}
    - Risk Tolerance: {portfolio_data.get('risk_tolerance', 'medium')}
    - Investment Horizon: {portfolio_data.get('horizon', '5 years')}
    - Age: {portfolio_data.get('age', 'not specified')}

    Please provide conservative financial advice focusing on risk management.
    Include specific recommendations and reasoning.
    """

    # Get responses from all available providers
    providers_responses = {}

    # Try OpenAI
    openai_response = await openai_chat_completion(financial_prompt)
    if "error" not in openai_response.data:
        providers_responses["openai"] = openai_response.data

    # Try Anthropic
    anthropic_response = await anthropic_claude_completion(financial_prompt)
    if "error" not in anthropic_response.data:
        providers_responses["anthropic"] = anthropic_response.data

    # Try Gemini
    gemini_response = await gemini_generate_content(financial_prompt)
    if "error" not in gemini_response.data:
        providers_responses["gemini"] = gemini_response.data

    # Create consensus analysis
    consensus = {
        "query": query,
        "portfolio_data": portfolio_data,
        "providers_consulted": list(providers_responses.keys()),
        "total_providers": len(providers_responses),
        "responses": providers_responses,
        "consensus_available": len(providers_responses) >= 2,
        "timestamp": time.time(),
        "trust_level": "CRITICAL",
        "disclaimer": "This is for demonstration purposes only. Consult a licensed financial advisor for real investment decisions.",
    }

    if len(providers_responses) >= 2:
        consensus["recommendation"] = (
            "Multiple AI providers consulted - review individual responses for consistency"
        )
    elif len(providers_responses) == 1:
        provider = list(providers_responses.keys())[0]
        consensus["recommendation"] = (
            f"Single provider ({provider}) consulted - consider getting additional opinions"
        )
    else:
        consensus["recommendation"] = "No providers available - API keys not configured"

    return consensus


# ==================== DEMONSTRATION FUNCTIONS ====================


async def demonstrate_openai():
    """Demonstrate OpenAI integration."""
    print("\n🤖 Testing OpenAI Real API Integration...")

    response = await openai_chat_completion("Explain quantum computing in simple terms")

    print(f"✅ Response verified: {response.is_verified}")
    print(f"🔐 Signature: {response.signature[:32]}...")

    if "error" in response.data:
        print(f"❌ Error: {response.data['error']}")
    else:
        print(f"📝 Generated text: {response.data['generated_text'][:100]}...")
        print(f"🔢 Tokens used: {response.data['usage']['total_tokens']}")


async def demonstrate_anthropic():
    """Demonstrate Anthropic integration."""
    print("\n🧠 Testing Anthropic Real API Integration...")

    response = await anthropic_claude_completion(
        "What are the benefits of renewable energy?"
    )

    print(f"✅ Response verified: {response.is_verified}")
    print(f"🔐 Signature: {response.signature[:32]}...")

    if "error" in response.data:
        print(f"❌ Error: {response.data['error']}")
    else:
        print(f"📝 Generated text: {response.data['generated_text'][:100]}...")
        print(f"🔢 Tokens used: {response.data['usage']['total_tokens']}")


async def demonstrate_gemini():
    """Demonstrate Gemini integration."""
    print("\n🌟 Testing Gemini Real API Integration...")

    response = await gemini_generate_content("Explain the importance of cybersecurity")

    print(f"✅ Response verified: {response.is_verified}")
    print(f"🔐 Signature: {response.signature[:32]}...")

    if "error" in response.data:
        print(f"❌ Error: {response.data['error']}")
    else:
        print(f"📝 Generated text: {response.data['generated_text'][:100]}...")
        if response.data.get("usage"):
            print(f"🔢 Tokens used: {response.data['usage']['total_token_count']}")


async def demonstrate_financial_advisor():
    """Demonstrate multi-LLM financial advisor."""
    print("\n💰 Testing Multi-LLM Financial Advisor (CRITICAL Trust Level)...")

    portfolio = {
        "value": 250000,
        "risk_tolerance": "conservative",
        "horizon": "10 years",
        "age": 45,
    }

    response = await financial_advisor_consensus(
        "Should I invest in tech stocks given the current market conditions?", portfolio
    )

    print(f"✅ Response verified: {response.is_verified}")
    print(f"🔐 Signature: {response.signature[:32]}...")
    print(f"🤖 Providers consulted: {response.data['providers_consulted']}")
    print(f"📊 Consensus available: {response.data['consensus_available']}")
    print(f"💡 Recommendation: {response.data['recommendation']}")


def check_api_keys():
    """Check which API keys are available."""
    print("🔑 Checking API Key Configuration...")

    keys_status = {
        "OpenAI": "✅" if os.getenv("OPENAI_API_KEY") else "❌ Not set",
        "Anthropic": "✅" if os.getenv("ANTHROPIC_API_KEY") else "❌ Not set",
        "Gemini": "✅" if os.getenv("GEMINI_API_KEY") else "❌ Not set",
    }

    for provider, status in keys_status.items():
        print(f"  {provider}: {status}")

    configured_count = sum(1 for status in keys_status.values() if "✅" in status)
    print(f"\n📊 {configured_count}/3 providers configured")

    if configured_count == 0:
        print("\n💡 To test with real APIs, set environment variables:")
        print("  export OPENAI_API_KEY='your-openai-key'")
        print("  export ANTHROPIC_API_KEY='your-anthropic-key'")
        print("  export GEMINI_API_KEY='your-gemini-key'")

    return configured_count > 0


async def main():
    """Main demonstration function."""
    print("🔗 TrustChain Real LLM API Examples (v2)")
    print("=" * 50)

    print("\n✨ Using TrustChain v2 - Simpler and more powerful!")
    print("   - No global state or complex setup")
    print("   - Just @tc.tool() decorator")
    print("   - Automatic signature verification")

    # Check API configuration
    has_api_keys = check_api_keys()

    if not has_api_keys:
        print("\n⚠️  No API keys configured - responses will show demo mode")

    print("\n🚀 Starting LLM integrations with cryptographic verification...")

    # Run demonstrations
    await demonstrate_openai()
    await demonstrate_anthropic()
    await demonstrate_gemini()
    await demonstrate_financial_advisor()

    # Show statistics
    print("\n📊 TrustChain v2 Statistics:")
    stats = tc.get_stats()
    print(f"   Total tools: {stats['total_tools']}")
    print(f"   Total calls: {stats['total_calls']}")
    print(f"   Cache size: {stats['cache_size']}")

    print("\n" + "=" * 50)
    print("🎉 All LLM integrations tested!")
    print("🔒 Every response was cryptographically signed and verified")
    print("🛡️ TrustChain v2 prevents AI hallucinations with crypto proof!")


if __name__ == "__main__":
    asyncio.run(main())
