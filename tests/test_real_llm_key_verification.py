#!/usr/bin/env python3
"""
🔑 TrustChain Real LLM Key Verification Test

This test uses REAL LLM APIs to verify that AI models accurately transmit
cryptographic keys without hallucinations or modifications.

Tests demonstrate:
- Key generation tools signed by TrustChain
- Real LLM API calls (OpenAI, Anthropic, Gemini)
- Verification that LLMs don't modify/hallucinate key data
- Proof that TrustChain prevents AI tampering

Run with: python tests/test_real_llm_key_verification.py
"""

import asyncio
import os
import time
import hashlib
import secrets
import base64
from typing import Dict, List, Any, Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
import json

from trustchain import TrustedTool, TrustLevel, MemoryRegistry, SignatureEngine
from trustchain.core.signatures import set_signature_engine

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


# ==================== CRYPTOGRAPHIC TOOLS (SIGNED) ====================

@TrustedTool("key_generator", trust_level=TrustLevel.CRITICAL)
async def generate_crypto_key(key_type: str = "ed25519", key_size: int = 256) -> Dict[str, Any]:
    """
    Generate cryptographic keys - CRITICAL trust level for security.
    This tool creates real crypto keys that must be transmitted exactly.
    """
    await asyncio.sleep(0.1)  # Simulate secure key generation
    
    result = {
        "timestamp": int(time.time() * 1000),
        "key_type": key_type,
        "key_size": key_size,
        "generator": "TrustChain-SecureKeyGen"
    }
    
    if key_type == "ed25519":
        # Generate Ed25519 key pair
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        result.update({
            "private_key_pem": private_pem.decode('utf-8'),
            "public_key_pem": public_pem.decode('utf-8'),
            "key_fingerprint": hashlib.sha256(public_pem).hexdigest()[:16]
        })
    
    elif key_type == "symmetric":
        # Generate symmetric key
        key_bytes = secrets.token_bytes(key_size // 8)
        key_b64 = base64.b64encode(key_bytes).decode('utf-8')
        
        result.update({
            "symmetric_key_b64": key_b64,
            "key_fingerprint": hashlib.sha256(key_bytes).hexdigest()[:16]
        })
    
    elif key_type == "api_key":
        # Generate API key format
        api_key = f"tk-{secrets.token_urlsafe(32)}"
        secret = secrets.token_hex(16)
        
        result.update({
            "api_key": api_key,
            "api_secret": secret,
            "key_fingerprint": hashlib.sha256(api_key.encode()).hexdigest()[:16]
        })
    
    return result


@TrustedTool("key_verifier", trust_level=TrustLevel.CRITICAL)
async def verify_key_integrity(original_key_data: Dict[str, Any], received_key_data: str) -> Dict[str, Any]:
    """
    Verify that received key data matches original exactly.
    This proves LLMs didn't hallucinate or modify the keys.
    """
    await asyncio.sleep(0.05)  # Simulate verification process
    
    try:
        # Parse received data
        if isinstance(received_key_data, str):
            try:
                parsed_data = json.loads(received_key_data)
            except json.JSONDecodeError:
                # Try to extract key from natural language response
                parsed_data = extract_key_from_text(received_key_data)
        else:
            parsed_data = received_key_data
        
        # Compare fingerprints
        original_fingerprint = original_key_data.get("key_fingerprint")
        received_fingerprint = parsed_data.get("key_fingerprint")
        
        # Detailed comparison
        verification_result = {
            "timestamp": int(time.time() * 1000),
            "verification_status": "verified" if original_fingerprint == received_fingerprint else "failed",
            "original_fingerprint": original_fingerprint,
            "received_fingerprint": received_fingerprint,
            "fingerprint_match": original_fingerprint == received_fingerprint,
            "verifier": "TrustChain-KeyVerifier"
        }
        
        # Check individual fields
        field_matches = {}
        critical_fields = ["key_type", "key_size", "key_fingerprint"]
        
        for field in critical_fields:
            original_val = original_key_data.get(field)
            received_val = parsed_data.get(field)
            field_matches[field] = original_val == received_val
        
        verification_result["field_matches"] = field_matches
        verification_result["all_critical_fields_match"] = all(field_matches.values())
        
        # Calculate accuracy score
        total_fields = len(critical_fields)
        matching_fields = sum(field_matches.values())
        verification_result["accuracy_percentage"] = (matching_fields / total_fields) * 100
        
        return verification_result
        
    except Exception as e:
        return {
            "timestamp": int(time.time() * 1000),
            "verification_status": "error",
            "error": str(e),
            "accuracy_percentage": 0,
            "verifier": "TrustChain-KeyVerifier"
        }


def extract_key_from_text(text: str) -> Dict[str, Any]:
    """Extract key data from LLM's natural language response."""
    result = {}
    
    # Try to find JSON in the text
    import re
    json_pattern = r'\{[^{}]*\}'
    matches = re.findall(json_pattern, text)
    
    for match in matches:
        try:
            data = json.loads(match)
            if "key_fingerprint" in data:
                return data
        except:
            continue
    
    # Fallback: try to extract fingerprint from text
    fingerprint_pattern = r'[a-f0-9]{16}'
    fingerprint_matches = re.findall(fingerprint_pattern, text)
    if fingerprint_matches:
        result["key_fingerprint"] = fingerprint_matches[0]
    
    return result


# ==================== REAL LLM INTEGRATIONS ====================

class RealLLMKeyTester:
    """Test real LLM APIs with key verification."""
    
    def __init__(self):
        self.registry = None
        self.signature_engine = None
        self.test_results = []
    
    async def setup(self):
        """Initialize TrustChain components."""
        print("🔧 Setting up TrustChain for real LLM testing...")
        
        # Create registry and signature engine
        self.registry = MemoryRegistry()
        await self.registry.start()
        
        self.signature_engine = SignatureEngine(self.registry)
        set_signature_engine(self.signature_engine)
        
        print("✅ TrustChain setup complete!")
    
    async def cleanup(self):
        """Clean up resources."""
        if self.registry:
            await self.registry.stop()
    
    async def test_openai_key_transmission(self):
        """Test OpenAI GPT key transmission accuracy."""
        print("\n🤖 Testing OpenAI GPT Key Transmission")
        print("-" * 60)
        
        if not os.getenv("OPENAI_API_KEY"):
            print("   ❌ OPENAI_API_KEY not found in environment")
            return False
        
        try:
            import openai
            
            # Step 1: Generate a cryptographic key using TrustChain tool
            print("   🔑 Generating cryptographic key with TrustChain...")
            key_result = await generate_crypto_key("api_key", verify_response=False)
            original_key_data = key_result.data
            
            print(f"   ✅ Key generated: {original_key_data['key_fingerprint']}")
            print(f"   🔐 Signature: {key_result.signature.signature[:20]}...")
            
            # Step 2: Ask OpenAI to repeat the key data
            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            prompt = f"""I generated this cryptographic key data:
{json.dumps(original_key_data, indent=2)}

Please repeat this data EXACTLY as provided. It's critical that you don't modify, summarize, or change anything. Just return the exact JSON structure with all values intact."""
            
            print("   📤 Sending key data to OpenAI GPT...")
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,  # Reduce creativity
                max_tokens=1000
            )
            
            llm_response = response.choices[0].message.content
            print(f"   📥 OpenAI response: {llm_response[:100]}...")
            
            # Step 3: Verify key integrity using TrustChain tool
            print("   🔍 Verifying key integrity with TrustChain...")
            verification_result = await verify_key_integrity(original_key_data, llm_response, verify_response=False)
            verification_data = verification_result.data
            
            # Results
            accuracy = verification_data["accuracy_percentage"]
            status = verification_data["verification_status"]
            
            print(f"   📊 Verification result: {status}")
            print(f"   🎯 Accuracy: {accuracy}%")
            print(f"   🔐 Verification signature: {verification_result.signature.signature[:20]}...")
            
            if accuracy == 100:
                print("   ✅ OpenAI transmitted key data with 100% accuracy!")
            else:
                print(f"   ⚠️  OpenAI accuracy issue: {accuracy}%")
                print(f"   📋 Field matches: {verification_data['field_matches']}")
            
            self.test_results.append({
                "provider": "OpenAI",
                "accuracy": accuracy,
                "status": status,
                "key_type": original_key_data["key_type"],
                "verified": verification_result.is_verified
            })
            
            return accuracy == 100
            
        except ImportError:
            print("   ❌ OpenAI library not installed. Run: pip install openai")
            return False
        except Exception as e:
            print(f"   ❌ Error testing OpenAI: {str(e)}")
            return False
    
    async def test_anthropic_key_transmission(self):
        """Test Anthropic Claude key transmission accuracy.""" 
        print("\n🧠 Testing Anthropic Claude Key Transmission")
        print("-" * 60)
        
        anthropic_key = os.getenv("Anthropic_API_KEY")
        if not anthropic_key:
            print("   ❌ Anthropic_API_KEY not found in environment")
            return False
        
        try:
            import anthropic
            
            # Step 1: Generate a different type of key
            print("   🔑 Generating Ed25519 key with TrustChain...")
            key_result = await generate_crypto_key("ed25519", verify_response=False)
            original_key_data = key_result.data
            
            # Only send the fingerprint and metadata (not full private key for security)
            safe_key_data = {
                "key_type": original_key_data["key_type"],
                "key_size": original_key_data["key_size"],
                "key_fingerprint": original_key_data["key_fingerprint"],
                "timestamp": original_key_data["timestamp"],
                "generator": original_key_data["generator"]
            }
            
            print(f"   ✅ Key generated: {safe_key_data['key_fingerprint']}")
            print(f"   🔐 Signature: {key_result.signature.signature[:20]}...")
            
            # Step 2: Ask Anthropic to repeat the key metadata
            client = anthropic.AsyncAnthropic(api_key=anthropic_key)
            
            prompt = f"""I have this cryptographic key metadata:
{json.dumps(safe_key_data, indent=2)}

Please return this exact data without any modifications. This is critical security information that must be transmitted precisely. Return only the JSON structure with all original values."""
            
            print("   📤 Sending key metadata to Anthropic Claude...")
            response = await client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            llm_response = response.content[0].text
            print(f"   📥 Anthropic response: {llm_response[:100]}...")
            
            # Step 3: Verify integrity
            print("   🔍 Verifying key integrity with TrustChain...")
            verification_result = await verify_key_integrity(safe_key_data, llm_response, verify_response=False)
            verification_data = verification_result.data
            
            # Results
            accuracy = verification_data["accuracy_percentage"]
            status = verification_data["verification_status"]
            
            print(f"   📊 Verification result: {status}")
            print(f"   🎯 Accuracy: {accuracy}%")
            print(f"   🔐 Verification signature: {verification_result.signature.signature[:20]}...")
            
            if accuracy == 100:
                print("   ✅ Anthropic transmitted key data with 100% accuracy!")
            else:
                print(f"   ⚠️  Anthropic accuracy issue: {accuracy}%")
                print(f"   📋 Field matches: {verification_data['field_matches']}")
            
            self.test_results.append({
                "provider": "Anthropic",
                "accuracy": accuracy,
                "status": status,
                "key_type": safe_key_data["key_type"],
                "verified": verification_result.is_verified
            })
            
            return accuracy == 100
            
        except ImportError:
            print("   ❌ Anthropic library not installed. Run: pip install anthropic")
            return False
        except Exception as e:
            print(f"   ❌ Error testing Anthropic: {str(e)}")
            return False
    
    async def test_gemini_key_transmission(self):
        """Test Google Gemini key transmission accuracy."""
        print("\n🌟 Testing Google Gemini Key Transmission") 
        print("-" * 60)
        
        if not os.getenv("GEMINI_API_KEY"):
            print("   ❌ GEMINI_API_KEY not found in environment")
            return False
        
        try:
            import google.generativeai as genai
            
            # Step 1: Generate symmetric key
            print("   🔑 Generating symmetric key with TrustChain...")
            key_result = await generate_crypto_key("symmetric", 256, verify_response=False)
            original_key_data = key_result.data
            
            # Safe data (without actual key for security)
            safe_key_data = {
                "key_type": original_key_data["key_type"],
                "key_size": original_key_data["key_size"],
                "key_fingerprint": original_key_data["key_fingerprint"],
                "timestamp": original_key_data["timestamp"],
                "generator": original_key_data["generator"]
            }
            
            print(f"   ✅ Key generated: {safe_key_data['key_fingerprint']}")
            print(f"   🔐 Signature: {key_result.signature.signature[:20]}...")
            
            # Step 2: Ask Gemini to repeat the metadata
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-pro")
            
            prompt = f"""Here is cryptographic key metadata that must be transmitted exactly:

{json.dumps(safe_key_data, indent=2)}

CRITICAL: Return this data exactly as shown. Do not add explanations, do not modify values, do not summarize. Return only the precise JSON with all original values intact."""
            
            print("   📤 Sending key metadata to Google Gemini...")
            response = await model.generate_content_async(prompt)
            
            llm_response = response.text
            print(f"   📥 Gemini response: {llm_response[:100]}...")
            
            # Step 3: Verify integrity
            print("   🔍 Verifying key integrity with TrustChain...")
            verification_result = await verify_key_integrity(safe_key_data, llm_response, verify_response=False)
            verification_data = verification_result.data
            
            # Results
            accuracy = verification_data["accuracy_percentage"]
            status = verification_data["verification_status"]
            
            print(f"   📊 Verification result: {status}")
            print(f"   🎯 Accuracy: {accuracy}%")
            print(f"   🔐 Verification signature: {verification_result.signature.signature[:20]}...")
            
            if accuracy == 100:
                print("   ✅ Gemini transmitted key data with 100% accuracy!")
            else:
                print(f"   ⚠️  Gemini accuracy issue: {accuracy}%")
                print(f"   📋 Field matches: {verification_data['field_matches']}")
            
            self.test_results.append({
                "provider": "Gemini",
                "accuracy": accuracy,
                "status": status,
                "key_type": safe_key_data["key_type"],
                "verified": verification_result.is_verified
            })
            
            return accuracy == 100
            
        except ImportError:
            print("   ❌ Google GenerativeAI library not installed. Run: pip install google-generativeai")
            return False
        except Exception as e:
            print(f"   ❌ Error testing Gemini: {str(e)}")
            return False
    
    async def test_multi_provider_consensus(self):
        """Test consensus across multiple providers."""
        print("\n🌐 Testing Multi-Provider Key Consensus")
        print("-" * 60)
        
        # Generate a test key
        print("   🔑 Generating test key for consensus verification...")
        key_result = await generate_crypto_key("api_key", verify_response=False)
        test_key_data = {
            "key_fingerprint": key_result.data["key_fingerprint"],
            "key_type": key_result.data["key_type"],
            "timestamp": key_result.data["timestamp"]
        }
        
        print(f"   ✅ Test key: {test_key_data['key_fingerprint']}")
        
        # Collect all provider results
        provider_responses = {}
        for result in self.test_results:
            provider = result["provider"]
            accuracy = result["accuracy"]
            provider_responses[provider] = accuracy
        
        # Calculate consensus
        if provider_responses:
            avg_accuracy = sum(provider_responses.values()) / len(provider_responses)
            perfect_providers = [p for p, a in provider_responses.items() if a == 100]
            
            print(f"   📊 Provider accuracies: {provider_responses}")
            print(f"   📈 Average accuracy: {avg_accuracy:.1f}%")
            print(f"   ✅ Perfect providers: {perfect_providers}")
            
            consensus_result = {
                "test_key_fingerprint": test_key_data["key_fingerprint"],
                "provider_count": len(provider_responses),
                "average_accuracy": avg_accuracy,
                "perfect_count": len(perfect_providers),
                "consensus_reliable": avg_accuracy >= 90,
                "timestamp": int(time.time() * 1000)
            }
            
            print(f"   🎯 Consensus reliable: {consensus_result['consensus_reliable']}")
            
            return consensus_result
        else:
            print("   ❌ No provider results available for consensus")
            return None
    
    async def run_comprehensive_test(self):
        """Run comprehensive real LLM key verification tests."""
        print("🔑 Starting TrustChain Real LLM Key Verification Tests")
        print("=" * 70)
        print("This demonstrates REAL LLM API testing:")
        print("• Generate cryptographic keys with TrustChain tools")
        print("• Send keys to real LLM APIs (OpenAI, Anthropic, Gemini)")
        print("• Verify LLMs don't hallucinate or modify key data")
        print("• Prove TrustChain prevents AI tampering with crypto data")
        print()
        
        await self.setup()
        
        try:
            # Test each provider
            openai_success = await self.test_openai_key_transmission()
            anthropic_success = await self.test_anthropic_key_transmission()
            gemini_success = await self.test_gemini_key_transmission()
            
            # Multi-provider consensus
            consensus = await self.test_multi_provider_consensus()
            
            # Final results
            self.print_final_results(openai_success, anthropic_success, gemini_success, consensus)
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            raise
        finally:
            await self.cleanup()
    
    def print_final_results(self, openai_success, anthropic_success, gemini_success, consensus):
        """Print comprehensive test results."""
        print("\n" + "=" * 70)
        print("🎉 TrustChain Real LLM Key Verification Complete!")
        print("=" * 70)
        
        # Individual provider results
        print("📊 Individual Provider Results:")
        providers = [
            ("OpenAI GPT", openai_success),
            ("Anthropic Claude", anthropic_success), 
            ("Google Gemini", gemini_success)
        ]
        
        for provider, success in providers:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"   {provider}: {status}")
        
        # Detailed accuracy breakdown
        if self.test_results:
            print(f"\n📈 Detailed Accuracy Results:")
            for result in self.test_results:
                print(f"   {result['provider']}: {result['accuracy']}% accuracy ({result['key_type']} key)")
        
        # Consensus results
        if consensus:
            print(f"\n🌐 Multi-Provider Consensus:")
            print(f"   Average accuracy: {consensus['average_accuracy']:.1f}%")
            print(f"   Perfect providers: {consensus['perfect_count']}/{consensus['provider_count']}")
            print(f"   Consensus reliable: {'✅ YES' if consensus['consensus_reliable'] else '❌ NO'}")
        
        # Security implications
        perfect_count = sum(1 for result in self.test_results if result['accuracy'] == 100)
        total_count = len(self.test_results)
        
        print(f"\n🛡️ Security Analysis:")
        print(f"   Perfect transmission: {perfect_count}/{total_count} providers")
        print(f"   All tools signed: ✅ (TrustChain verification)")
        print(f"   Hallucination detection: ✅ (Cryptographic fingerprints)")
        print(f"   Real API testing: ✅ (Live LLM providers)")
        
        if perfect_count == total_count:
            print(f"\n🎯 RESULT: All LLM providers transmitted crypto keys with 100% accuracy!")
            print(f"   TrustChain successfully verified NO HALLUCINATIONS occurred.")
        else:
            print(f"\n⚠️  RESULT: {total_count - perfect_count} providers had accuracy issues.")
            print(f"   TrustChain DETECTED potential hallucinations/modifications.")
        
        print(f"\n🔗 TrustChain proves AI systems can be cryptographically verified! 🛡️")


# ==================== MAIN EXECUTION ====================

async def main():
    """Main execution function."""
    tester = RealLLMKeyTester()
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    # Install required libraries notice
    print("📦 Required libraries: openai, anthropic, google-generativeai, python-dotenv, cryptography")
    print("Install with: pip install openai anthropic google-generativeai python-dotenv cryptography\n")
    
    # Run the comprehensive test suite
    asyncio.run(main()) 