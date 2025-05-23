#!/usr/bin/env python3
"""
🧠 Simple AI Hallucination Test

Quick test to show the difference between real and hallucinated responses.

Author: Ed Cherednik (edcherednik@gmail.com)
Telegram: @EdCher

Run: python examples/simple_hallucination_test.py
"""

import asyncio

from trustchain import TrustedTool, TrustLevel
from trustchain.core.models import SignedResponse


@TrustedTool("bank_api", trust_level=TrustLevel.HIGH)
async def get_account_balance(account_id: str) -> dict:
    """Get account balance - cryptographically signed."""
    return {
        "account_id": account_id,
        "balance": 5000.0,
        "currency": "USD",
        "bank": "TrustBank",
    }


async def main():
    print("🧠 TrustChain vs AI Hallucinations - Quick Test")
    print("=" * 50)

    # ✅ Real response from trusted tool
    print("\n✅ REAL RESPONSE (from TrustedTool):")
    real_response = await get_account_balance("acc_001")
    print(f"   Type: {type(real_response)}")
    print(f"   Balance: ${real_response.data['balance']}")
    print(f"   Has signature: {hasattr(real_response, 'signature')}")
    print(f"   Is verified: {real_response.is_verified}")
    if hasattr(real_response, "signature"):
        print(f"   Signature preview: {real_response.signature.signature[:20]}...")

    # ❌ Fake response (AI hallucination)
    print("\n❌ FAKE RESPONSE (AI hallucination):")
    fake_response = {
        "account_id": "acc_001",
        "balance": 999999.99,  # Fake balance!
        "currency": "USD",
        "bank": "TrustBank",
        "WARNING": "This is hallucinated data!",
    }
    print(f"   Type: {type(fake_response)}")
    print(f"   Balance: ${fake_response['balance']}")
    print(f"   Has signature: {hasattr(fake_response, 'signature')}")
    print(f"   Is verified: {isinstance(fake_response, SignedResponse)}")

    # Analysis
    print("\n🔍 ANALYSIS:")
    print("   ✅ Real response: Cryptographically signed & verified")
    print("   ❌ Fake response: No signature = HALLUCINATION DETECTED!")

    print("\n💡 CONCLUSION:")
    print("   TrustChain makes it IMPOSSIBLE for AI to hide hallucinations!")
    print("   No signature = No trust = Immediate detection!")


if __name__ == "__main__":
    asyncio.run(main())
