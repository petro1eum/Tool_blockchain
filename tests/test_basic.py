"""
Basic tests for TrustChain functionality.

Author: Ed Cherednik (edcherednik@gmail.com)
Telegram: @EdCher
"""

import asyncio
import platform
import time
from typing import Any, Dict

# Windows compatibility fix
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import pytest

from trustchain import (
    MemoryRegistry,
    SignatureAlgorithm,
    TrustedTool,
    TrustLevel,
    get_crypto_engine,
    get_signature_engine,
)
from trustchain.core.crypto import Ed25519KeyPair
from trustchain.core.models import KeyMetadata, SignedResponse
from trustchain.tools.base import FunctionTrustedTool
from trustchain.utils.exceptions import NonceReplayError, ToolExecutionError


@pytest.fixture
async def registry():
    """Create a test registry."""
    registry = MemoryRegistry()
    await registry.start()
    yield registry
    await registry.stop()


@pytest.fixture
def crypto_engine():
    """Create a test crypto engine."""
    return get_crypto_engine()


class TestCryptoEngine:
    """Test cryptographic functionality."""

    def test_create_ed25519_key_pair(self, crypto_engine):
        """Test Ed25519 key pair creation."""
        key_pair = crypto_engine.create_key_pair(SignatureAlgorithm.ED25519)

        assert key_pair.algorithm == SignatureAlgorithm.ED25519
        assert key_pair.has_private_key
        assert key_pair.has_public_key
        assert key_pair.key_id is not None

    def test_key_export_import(self, crypto_engine):
        """Test key export and import."""
        # Create key pair
        key_pair = crypto_engine.create_key_pair(SignatureAlgorithm.ED25519)

        # Export keys
        private_key_pem = key_pair.export_private_key("pem")
        public_key_pem = key_pair.export_public_key("pem")

        assert b"-----BEGIN PRIVATE KEY-----" in private_key_pem
        assert b"-----BEGIN PUBLIC KEY-----" in public_key_pem

        # Import keys
        new_key_pair = Ed25519KeyPair()
        new_key_pair.import_private_key(private_key_pem)

        # Test signature compatibility
        test_data = b"test message"
        signature1 = key_pair.sign(test_data)
        signature2 = new_key_pair.sign(test_data)

        # Both should verify successfully
        assert key_pair.verify(test_data, signature1)
        assert new_key_pair.verify(test_data, signature2)

    def test_hash_data(self, crypto_engine):
        """Test data hashing."""
        test_data = "Hello, World!"
        hash_result = crypto_engine.hash_data(test_data)

        assert hash_result.startswith("sha256:")
        assert len(hash_result.split(":")[1]) == 64  # SHA256 hex length

        # Same data should produce same hash
        hash_result2 = crypto_engine.hash_data(test_data)
        assert hash_result == hash_result2

        # Different data should produce different hash
        hash_result3 = crypto_engine.hash_data("Different data")
        assert hash_result != hash_result3


class TestTrustRegistry:
    """Test trust registry functionality."""

    async def test_register_and_get_key(self, registry):
        """Test key registration and retrieval."""
        # Create test key metadata
        key_metadata = KeyMetadata(
            key_id="test_key_001",
            algorithm=SignatureAlgorithm.ED25519,
            public_key="test_public_key_base64",
            tool_id="test_tool",
            created_by="test",
        )

        # Register key
        await registry.register_key(key_metadata)

        # Retrieve key
        retrieved_key = await registry.get_key("test_key_001")
        assert retrieved_key is not None
        assert retrieved_key.key_id == "test_key_001"
        assert retrieved_key.tool_id == "test_tool"
        assert retrieved_key.is_valid

    async def test_list_keys(self, registry):
        """Test key listing functionality."""
        # Register multiple keys
        for i in range(3):
            key_metadata = KeyMetadata(
                key_id=f"test_key_{i:03d}",
                algorithm=SignatureAlgorithm.ED25519,
                public_key=f"test_public_key_{i}",
                tool_id=f"tool_{i}",
                created_by="test",
            )
            await registry.register_key(key_metadata)

        # List all keys
        all_keys = await registry.list_keys()
        assert len(all_keys) == 3

        # List keys by tool
        tool_0_keys = await registry.list_keys(tool_id="tool_0")
        assert len(tool_0_keys) == 1
        assert tool_0_keys[0].tool_id == "tool_0"

    async def test_revoke_key(self, registry):
        """Test key revocation."""
        # Register key
        key_metadata = KeyMetadata(
            key_id="revoke_test_key",
            algorithm=SignatureAlgorithm.ED25519,
            public_key="test_public_key",
            tool_id="test_tool",
            created_by="test",
        )
        await registry.register_key(key_metadata)

        # Verify key is valid
        key = await registry.get_key("revoke_test_key")
        assert key.is_valid

        # Revoke key
        await registry.revoke_key("revoke_test_key", "Test revocation")

        # Verify key is revoked
        key = await registry.get_key("revoke_test_key")
        assert not key.is_valid
        assert key.revoked
        assert key.revocation_reason == "Test revocation"


class TestTrustedTools:
    """Test trusted tool functionality."""

    async def test_simple_trusted_tool(self, registry):
        """Test basic trusted tool creation and execution."""

        @TrustedTool("test_simple_tool", registry=registry, auto_register=False, require_nonce=False)
        async def simple_tool(message: str) -> Dict[str, Any]:
            return {"echo": message, "timestamp": int(time.time() * 1000)}

        # Execute tool
        response = await simple_tool("Hello, World!")

        # Verify response
        assert isinstance(response, SignedResponse)
        assert response.tool_id == "test_simple_tool"
        assert response.data["echo"] == "Hello, World!"
        assert response.is_verified
        assert response.signature is not None

    async def test_tool_with_error(self, registry):
        """Test tool error handling."""

        @TrustedTool("test_error_tool", registry=registry, auto_register=False, require_nonce=False)
        async def error_tool(should_error: bool) -> Dict[str, Any]:
            if should_error:
                raise ValueError("Test error")
            return {"success": True}

        # Test successful execution
        response = await error_tool(False)
        assert response.data["success"] is True

        # Test error handling
        with pytest.raises(ToolExecutionError):
            await error_tool(True)

    async def test_tool_statistics(self, registry):
        """Test tool statistics tracking."""

        @TrustedTool("test_stats_tool", registry=registry, auto_register=False, require_nonce=False)
        async def stats_tool(value: int) -> Dict[str, Any]:
            return {"result": value * 2}

        # Execute tool multiple times
        for i in range(5):
            await stats_tool(i)

        # Check statistics
        stats = await stats_tool.get_statistics()
        assert stats["stats"]["total_calls"] == 5
        assert stats["stats"]["successful_calls"] == 5
        assert stats["success_rate"] == 1.0

    async def test_synchronous_tool(self, registry):
        """Test synchronous function wrapping."""

        @TrustedTool("test_sync_tool", registry=registry, auto_register=False, require_nonce=False)
        def sync_tool(a: int, b: int) -> Dict[str, Any]:
            return {"sum": a + b, "product": a * b}

        # Execute synchronous tool
        response = await sync_tool(3, 4)

        # Verify response
        assert response.data["sum"] == 7
        assert response.data["product"] == 12
        assert response.is_verified


class TestNonceManagement:
    """Test nonce management and replay protection."""

    async def test_nonce_generation(self):
        """Test nonce generation."""
        from trustchain.core.nonce import NonceGenerator

        # Generate different types of nonces
        random_nonce = NonceGenerator.generate()
        uuid_nonce = NonceGenerator.generate_uuid()
        timestamp_nonce = NonceGenerator.generate_timestamp_nonce()

        # Verify they're different
        assert random_nonce != uuid_nonce
        assert uuid_nonce != timestamp_nonce
        assert random_nonce != timestamp_nonce

        # Verify formats
        assert len(random_nonce) > 10
        assert "-" in uuid_nonce
        assert "-" in timestamp_nonce

    async def test_nonce_validation(self):
        """Test nonce validation."""
        from trustchain.core.nonce import NonceValidator

        # Valid nonces (must be at least 8 chars)
        assert NonceValidator.validate_format("abc12345")  # Exactly 8 chars
        assert NonceValidator.validate_format("uuid-like-string-123")
        assert NonceValidator.validate_format("long_nonce_string_12345")

        # Invalid nonces
        assert not NonceValidator.validate_format("")
        assert not NonceValidator.validate_format("a")  # Too short
        assert not NonceValidator.validate_format("abc123")  # Too short (6 chars)
        assert not NonceValidator.validate_format("invalid characters!")

    async def test_replay_protection(self, registry):
        """Test replay attack prevention."""

        @TrustedTool("test_replay_tool", registry=registry, auto_register=False)
        async def replay_tool(data: str) -> Dict[str, Any]:
            return {"processed": data}

        # Use same nonce twice - should fail second time
        nonce = "test_nonce_123"

        # First call should succeed
        response1 = await replay_tool("data1", nonce=nonce)
        assert response1.is_verified

        # Second call with same nonce should fail
        with pytest.raises(NonceReplayError):
            await replay_tool("data2", nonce=nonce)


class TestSignatureVerification:
    """Test signature verification functionality."""

    async def test_signature_creation_and_verification(self, registry):
        """Test end-to-end signature creation and verification."""
        from trustchain.core.signatures import SignatureEngine, set_signature_engine

        # Create signature engine
        signature_engine = SignatureEngine(registry)
        set_signature_engine(signature_engine)

        # Create signer
        signature_engine.create_signer("test_signer", SignatureAlgorithm.ED25519)

        # Sign a response
        signed_response = signature_engine.sign_response(
            signer_id="test_signer",
            request_id="test_request",
            tool_id="test_tool",
            data={"message": "test data"},
        )

        # Verify the response
        verification_result = signature_engine.verify_response(signed_response)

        # Check verification result
        assert verification_result.valid
        assert verification_result.algorithm_used == SignatureAlgorithm.ED25519
        assert verification_result.request_id == "test_request"


# Integration test
async def test_full_integration():
    """Test full integration scenario."""
    # Create registry
    registry = MemoryRegistry()
    await registry.start()

    try:
        # Create trusted tool
        @TrustedTool("integration_test_tool", registry=registry, require_nonce=False)
        async def integration_tool(
            operation: str, a: float, b: float
        ) -> Dict[str, Any]:
            if operation == "add":
                return {"result": a + b, "operation": operation}
            elif operation == "multiply":
                return {"result": a * b, "operation": operation}
            else:
                raise ValueError(f"Unsupported operation: {operation}")

        # Test successful operations
        add_response = await integration_tool("add", 5.0, 3.0)
        assert add_response.data["result"] == 8.0
        assert add_response.is_verified

        multiply_response = await integration_tool("multiply", 4.0, 7.0)
        assert multiply_response.data["result"] == 28.0
        assert multiply_response.is_verified

        # Test error handling
        with pytest.raises(ToolExecutionError):
            await integration_tool("divide", 10.0, 2.0)

        # Check tool statistics
        stats = await integration_tool.get_statistics()
        assert stats["stats"]["total_calls"] == 3  # 2 successful + 1 failed
        assert stats["stats"]["successful_calls"] == 2
        assert stats["stats"]["failed_calls"] == 1

        print("✅ Full integration test passed!")

    finally:
        await registry.stop()


if __name__ == "__main__":
    # Run integration test directly
    asyncio.run(test_full_integration())
