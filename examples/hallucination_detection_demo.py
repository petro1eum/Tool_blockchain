#!/usr/bin/env python3
"""
🧠 AI Hallucination Detection with TrustChain

This demo shows how TrustChain prevents AI hallucinations by providing
cryptographic proof of tool response authenticity.

Author: Ed Cherednik (edcherednik@gmail.com)
Telegram: @EdCher

Run: python examples/hallucination_detection_demo.py
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict

# TrustChain imports
from trustchain import MemoryRegistry, TrustedTool, TrustLevel
from trustchain.core.models import SignedResponse

# ==================== SIMULATION SETUP ====================


@dataclass
class BankAccount:
    """Simple bank account for demo."""

    account_id: str
    balance: float
    owner: str


@dataclass
class NewsArticle:
    """News article structure."""

    title: str
    content: str
    author: str
    timestamp: str
    verified: bool = False


# Demo data
BANK_ACCOUNTS = {
    "acc_001": BankAccount("acc_001", 5000.0, "Alice Johnson"),
    "acc_002": BankAccount("acc_002", 3000.0, "Bob Smith"),
    "acc_003": BankAccount("acc_003", 10000.0, "Charlie Brown"),
}

NEWS_DATABASE = [
    NewsArticle(
        title="Tech Company Reports Q4 Earnings",
        content="XYZ Corp reported strong Q4 earnings with revenue up 15%",
        author="Financial Times",
        timestamp="2025-01-24T09:00:00Z",
    ),
    NewsArticle(
        title="New AI Breakthrough Announced",
        content="Researchers develop new neural architecture with 40% efficiency gains",
        author="Science Daily",
        timestamp="2025-01-24T10:30:00Z",
    ),
]


# ==================== TRUSTED TOOLS ====================


@TrustedTool("banking_system", trust_level=TrustLevel.CRITICAL)
async def check_account_balance(account_id: str) -> Dict[str, Any]:
    """Check bank account balance - cryptographically signed."""
    await asyncio.sleep(0.1)  # Simulate database lookup

    account = BANK_ACCOUNTS.get(account_id)
    if not account:
        return {
            "error": "Account not found",
            "account_id": account_id,
            "status": "error",
        }

    return {
        "account_id": account.account_id,
        "balance": account.balance,
        "owner": account.owner,
        "status": "success",
        "timestamp": int(time.time() * 1000),
        "bank": "TrustBank",
    }


@TrustedTool("news_service", trust_level=TrustLevel.HIGH)
async def get_latest_news(category: str = "tech") -> Dict[str, Any]:
    """Get latest news - cryptographically signed."""
    await asyncio.sleep(0.2)  # Simulate API call

    # Filter news by category
    filtered_news = [
        {
            "title": article.title,
            "content": article.content[:100] + "...",
            "author": article.author,
            "timestamp": article.timestamp,
        }
        for article in NEWS_DATABASE
        if category.lower() in article.title.lower()
        or category.lower() in article.content.lower()
    ]

    return {
        "category": category,
        "articles": filtered_news,
        "count": len(filtered_news),
        "source": "TrustNews API",
        "retrieved_at": int(time.time() * 1000),
    }


@TrustedTool("stock_service", trust_level=TrustLevel.HIGH)
async def get_stock_price(symbol: str) -> Dict[str, Any]:
    """Get stock price - cryptographically signed."""
    await asyncio.sleep(0.15)  # Simulate market API

    # Simulated stock data
    stock_data = {
        "AAPL": {"price": 192.45, "change": +2.1},
        "GOOGL": {"price": 2875.60, "change": -15.3},
        "MSFT": {"price": 425.20, "change": +5.7},
        "TSLA": {"price": 248.90, "change": -8.2},
    }

    data = stock_data.get(symbol.upper())
    if not data:
        return {"error": "Stock symbol not found", "symbol": symbol, "status": "error"}

    return {
        "symbol": symbol.upper(),
        "price": data["price"],
        "change": data["change"],
        "currency": "USD",
        "market": "NASDAQ",
        "timestamp": int(time.time() * 1000),
        "status": "success",
    }


# ==================== AI HALLUCINATION SIMULATOR ====================


class AIHallucinationSimulator:
    """Simulates AI that can hallucinate vs real tool responses."""

    def __init__(self):
        self.hallucination_mode = False

    def set_hallucination_mode(self, enabled: bool):
        """Enable/disable hallucination mode."""
        self.hallucination_mode = enabled

    async def get_account_info(self, account_id: str) -> Dict[str, Any]:
        """Simulate AI getting account info - may hallucinate!"""

        if self.hallucination_mode:
            # 🚨 AI HALLUCINATION - Make up fake data!
            print(f"🧠 AI HALLUCINATING: Making up fake account data for {account_id}")
            return {
                "account_id": account_id,
                "balance": 999999.99,  # Fake huge balance!
                "owner": "Super Rich Person",
                "status": "success",
                "timestamp": int(time.time() * 1000),
                "bank": "TrustBank",
                "WARNING": "This is HALLUCINATED data - not real!",
            }
        else:
            # ✅ Use real trusted tool
            print(f"✅ AI using TRUSTED tool for {account_id}")
            return await check_account_balance(account_id)

    async def get_news_info(self, category: str) -> Dict[str, Any]:
        """Simulate AI getting news - may hallucinate!"""

        if self.hallucination_mode:
            # 🚨 AI HALLUCINATION - Make up fake news!
            print(f"🧠 AI HALLUCINATING: Making up fake news for {category}")
            return {
                "category": category,
                "articles": [
                    {
                        "title": "BREAKING: AI Takes Over All Banks!",
                        "content": "In a shocking turn of events, AI systems have gained control...",
                        "author": "Fake News Corp",
                        "timestamp": "2025-01-24T12:00:00Z",
                    }
                ],
                "count": 1,
                "source": "FakeNews API",
                "retrieved_at": int(time.time() * 1000),
                "WARNING": "This is HALLUCINATED news - not real!",
            }
        else:
            # ✅ Use real trusted tool
            print(f"✅ AI using TRUSTED tool for news category: {category}")
            return await get_latest_news(category)

    async def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """Simulate AI getting stock data - may hallucinate!"""

        if self.hallucination_mode:
            # 🚨 AI HALLUCINATION - Make up fake stock prices!
            print(f"🧠 AI HALLUCINATING: Making up fake stock data for {symbol}")
            return {
                "symbol": symbol.upper(),
                "price": 50000.00,  # Impossible stock price!
                "change": +9999.99,  # Impossible change!
                "currency": "USD",
                "market": "FANTASY",
                "timestamp": int(time.time() * 1000),
                "status": "success",
                "WARNING": "This is HALLUCINATED stock data - not real!",
            }
        else:
            # ✅ Use real trusted tool
            print(f"✅ AI using TRUSTED tool for stock: {symbol}")
            return await get_stock_price(symbol)


# ==================== DEMO SCENARIOS ====================


class HallucinationDemo:
    """Main demo class showing hallucination detection."""

    def __init__(self):
        self.ai_agent = AIHallucinationSimulator()
        self.registry = None

    async def setup(self):
        """Setup demo environment."""
        print("🔧 Setting up TrustChain Hallucination Detection Demo...")
        self.registry = MemoryRegistry()
        await self.registry.start()
        print("✅ Demo environment ready!")

    async def cleanup(self):
        """Cleanup resources."""
        if self.registry:
            await self.registry.stop()

    def verify_response_authenticity(self, response: Any) -> Dict[str, Any]:
        """Verify if response is cryptographically authentic."""
        verification = {
            "is_trustchain_response": isinstance(response, SignedResponse),
            "has_signature": False,
            "is_verified": False,
            "trust_level": "UNKNOWN",
            "authenticity": "UNVERIFIED",
        }

        if isinstance(response, SignedResponse):
            verification.update(
                {
                    "has_signature": hasattr(response, "signature")
                    and response.signature is not None,
                    "is_verified": response.is_verified,
                    "trust_level": getattr(response, "trust_level", "UNKNOWN"),
                    "tool_id": response.tool_id,
                    "authenticity": "VERIFIED" if response.is_verified else "INVALID",
                }
            )
        else:
            # This is likely hallucinated data - no cryptographic proof!
            verification["authenticity"] = "HALLUCINATED - NO CRYPTO PROOF"

        return verification

    async def demo_banking_hallucination(self):
        """Demo banking data hallucination detection."""
        print("\n" + "=" * 60)
        print("🏦 BANKING DEMO: Detecting Financial Data Hallucinations")
        print("=" * 60)

        account_id = "acc_001"

        # Test 1: Real trusted response
        print("\n📊 Test 1: AI using TRUSTED banking tool")
        print("-" * 40)
        self.ai_agent.set_hallucination_mode(False)
        real_response = await self.ai_agent.get_account_info(account_id)
        real_verification = self.verify_response_authenticity(real_response)

        print(f"Response type: {type(real_response)}")
        print(f"Account balance: ${real_response.data.get('balance', 'N/A')}")
        print(f"🔐 Cryptographic verification: {real_verification}")

        # Test 2: Hallucinated response
        print("\n📊 Test 2: AI HALLUCINATING banking data")
        print("-" * 40)
        self.ai_agent.set_hallucination_mode(True)
        fake_response = await self.ai_agent.get_account_info(account_id)
        fake_verification = self.verify_response_authenticity(fake_response)

        print(f"Response type: {type(fake_response)}")
        print(f"Account balance: ${fake_response.get('balance', 'N/A')}")
        print(f"🚨 Cryptographic verification: {fake_verification}")

        # Security Analysis
        print("\n🛡️ SECURITY ANALYSIS:")
        print(f"✅ Real response verified: {real_verification['authenticity']}")
        print(f"❌ Fake response detected: {fake_verification['authenticity']}")

        if fake_verification["authenticity"] == "HALLUCINATED - NO CRYPTO PROOF":
            print("🔥 HALLUCINATION DETECTED! No cryptographic signature found.")
            print("💡 TrustChain prevented potential financial fraud!")

    async def demo_news_hallucination(self):
        """Demo news data hallucination detection."""
        print("\n" + "=" * 60)
        print("📰 NEWS DEMO: Detecting Fake News Hallucinations")
        print("=" * 60)

        category = "tech"

        # Test 1: Real trusted response
        print("\n📊 Test 1: AI using TRUSTED news service")
        print("-" * 40)
        self.ai_agent.set_hallucination_mode(False)
        real_response = await self.ai_agent.get_news_info(category)
        real_verification = self.verify_response_authenticity(real_response)

        print(f"Response type: {type(real_response)}")
        print(f"Articles found: {real_response.data.get('count', 'N/A')}")
        print(f"🔐 Cryptographic verification: {real_verification}")

        # Test 2: Hallucinated response
        print("\n📊 Test 2: AI HALLUCINATING news data")
        print("-" * 40)
        self.ai_agent.set_hallucination_mode(True)
        fake_response = await self.ai_agent.get_news_info(category)
        fake_verification = self.verify_response_authenticity(fake_response)

        print(f"Response type: {type(fake_response)}")
        print(f"Articles found: {fake_response.get('count', 'N/A')}")
        if fake_response.get("articles"):
            print(f"Sample headline: {fake_response['articles'][0]['title']}")
        print(f"🚨 Cryptographic verification: {fake_verification}")

        # Security Analysis
        print("\n🛡️ SECURITY ANALYSIS:")
        print(f"✅ Real news verified: {real_verification['authenticity']}")
        print(f"❌ Fake news detected: {fake_verification['authenticity']}")

        if fake_verification["authenticity"] == "HALLUCINATED - NO CRYPTO PROOF":
            print("🔥 FAKE NEWS DETECTED! No cryptographic signature found.")
            print("💡 TrustChain prevented misinformation spread!")

    async def demo_stock_hallucination(self):
        """Demo stock data hallucination detection."""
        print("\n" + "=" * 60)
        print("📈 STOCK DEMO: Detecting Market Data Hallucinations")
        print("=" * 60)

        symbol = "AAPL"

        # Test 1: Real trusted response
        print("\n📊 Test 1: AI using TRUSTED stock service")
        print("-" * 40)
        self.ai_agent.set_hallucination_mode(False)
        real_response = await self.ai_agent.get_stock_info(symbol)
        real_verification = self.verify_response_authenticity(real_response)

        print(f"Response type: {type(real_response)}")
        print(f"Stock price: ${real_response.data.get('price', 'N/A')}")
        print(f"Change: {real_response.data.get('change', 'N/A')}")
        print(f"🔐 Cryptographic verification: {real_verification}")

        # Test 2: Hallucinated response
        print("\n📊 Test 2: AI HALLUCINATING stock data")
        print("-" * 40)
        self.ai_agent.set_hallucination_mode(True)
        fake_response = await self.ai_agent.get_stock_info(symbol)
        fake_verification = self.verify_response_authenticity(fake_response)

        print(f"Response type: {type(fake_response)}")
        print(f"Stock price: ${fake_response.get('price', 'N/A')}")
        print(f"Change: {fake_response.get('change', 'N/A')}")
        print(f"🚨 Cryptographic verification: {fake_verification}")

        # Security Analysis
        print("\n🛡️ SECURITY ANALYSIS:")
        print(f"✅ Real data verified: {real_verification['authenticity']}")
        print(f"❌ Fake data detected: {fake_verification['authenticity']}")

        if fake_verification["authenticity"] == "HALLUCINATED - NO CRYPTO PROOF":
            print("🔥 MARKET MANIPULATION DETECTED! No cryptographic signature found.")
            print("💡 TrustChain prevented potential trading fraud!")

    async def demo_signature_tampering(self):
        """Demo signature tampering detection."""
        print("\n" + "=" * 60)
        print("🔒 TAMPERING DEMO: Detecting Response Modification")
        print("=" * 60)

        # Get a real signed response
        print("📊 Getting legitimate signed response...")
        real_response = await check_account_balance("acc_001")
        print(f"✅ Original balance: ${real_response.data['balance']}")
        print(f"✅ Signature valid: {real_response.is_verified}")

        # Try to tamper with the data (this will break the signature)
        print("\n🚨 Attempting to tamper with response data...")
        try:
            # This would be an attack attempt - modify the balance
            original_balance = real_response.data["balance"]
            real_response.data["balance"] = 999999.99  # Try to change balance

            # Re-verify signature after tampering
            verification = self.verify_response_authenticity(real_response)
            print(f"❌ Modified balance: ${real_response.data['balance']}")
            print(f"🛡️ Signature still valid: {verification['is_verified']}")

            # Restore original data for demonstration
            real_response.data["balance"] = original_balance

        except Exception as e:
            print(f"🔒 Tampering prevented by cryptographic protection: {e}")

        print("\n💡 TrustChain Insight:")
        print("Even if someone modifies the response data, the cryptographic")
        print("signature becomes invalid, immediately alerting to tampering!")

    async def run_full_demo(self):
        """Run the complete hallucination detection demo."""
        print("🧠 TrustChain AI Hallucination Detection Demo")
        print("=" * 60)
        print("🎯 Goal: Demonstrate how TrustChain prevents AI hallucinations")
        print("🔒 Method: Cryptographic signatures on tool responses")
        print("👨‍💻 Author: Ed Cherednik (@EdCher)")
        print()

        await self.setup()

        try:
            # Run all demo scenarios
            await self.demo_banking_hallucination()
            await self.demo_news_hallucination()
            await self.demo_stock_hallucination()
            await self.demo_signature_tampering()

            # Final summary
            print("\n" + "=" * 60)
            print("🏆 DEMO SUMMARY: TrustChain vs AI Hallucinations")
            print("=" * 60)
            print("✅ TRUSTED responses: Cryptographically signed & verified")
            print("❌ HALLUCINATED responses: No signature = immediately detected")
            print("🔒 TAMPERED responses: Invalid signature = immediately detected")
            print()
            print("🛡️ Key Benefits:")
            print("  • Prevents financial fraud from AI hallucinations")
            print("  • Stops fake news and misinformation")
            print("  • Detects market manipulation attempts")
            print("  • Provides cryptographic proof of authenticity")
            print("  • Works automatically - no user intervention needed")
            print()
            print("🎯 Result: AI responses are now TRUSTWORTHY and VERIFIABLE!")
            print("💡 TrustChain makes AI hallucinations impossible to hide!")

        finally:
            await self.cleanup()


# ==================== MAIN EXECUTION ====================


async def main():
    """Run the hallucination detection demo."""
    demo = HallucinationDemo()
    await demo.run_full_demo()


if __name__ == "__main__":
    print("🚀 Starting TrustChain Hallucination Detection Demo...")
    print("🔧 This demo shows how cryptographic signatures prevent AI hallucinations")
    print()

    asyncio.run(main())
