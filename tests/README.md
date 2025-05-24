# 🧪 TrustChain Tests

This directory contains comprehensive tests for TrustChain library functionality.

## 📋 Test Files

### 🔒 Core Comprehensive Tests
- **`test_comprehensive_features.py`** - **COMPLETE feature coverage with NO bypasses**
- `test_basic.py` - Basic functionality tests for crypto engine, tools, and registry
- `conftest.py` - Pytest configuration and shared fixtures

### AI Integration Tests
- `test_llm_tool_calling.py` - AI Tool Calling with Signatures (cleaned up)
- `test_real_llm_clean.py` - Real LLM API tests for production (requires API keys)

## 🚀 Running Tests

### 1. ✅ Comprehensive Feature Tests (MAIN)
```bash
# Run the complete comprehensive test suite
python -m pytest tests/test_comprehensive_features.py -v

# This covers ALL key features:
# • Cryptographic signatures (Ed25519)
# • Hallucination detection 
# • Tool execution enforcement
# • Automatic interception
# • Trust levels (LOW/MEDIUM/HIGH/CRITICAL)
# • Replay protection with nonces
# • Performance requirements
# • Error handling
# • End-to-end integration
```

### 2. Basic Functionality Tests
```bash
# Run core functionality tests
python -m pytest tests/test_basic.py -v
```

### 3. AI Tool Calling Tests
```bash
# Run AI agent tool calling tests
python -m pytest tests/test_llm_tool_calling.py -v
```

### 4. All Tests
```bash
# Run entire test suite
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=trustchain --cov-report=html
```

## 🔒 What's Tested - Complete Feature Coverage

### ✅ **1. Cryptographic Signatures**
- **Ed25519 signature creation and verification**
- **Signature tampering detection**
- **Performance requirements (<100ms for testing)**
- **Manual signature verification**

**Why Critical:** Core security foundation - prevents response forgery

### ✅ **2. Hallucination Detection**
- **Fake weather claim detection**
- **Fake financial claim detection** 
- **Semantic bypass detection**
- **Legitimate conversation allowed**

**Why Critical:** Prevents AI from lying about tool usage

### ✅ **3. Tool Execution Enforcement**
- **Enforced tool execution through registry**
- **Complete audit trail of all executions**
- **Claim verification against actual executions**
- **Performance tracking**

**Why Critical:** Ensures all tool calls are tracked and verifiable

### ✅ **4. Automatic Interception**
- **Direct tool calls blocked in strict mode**
- **Enforcer calls allowed (authorized context)**
- **Interception statistics and monitoring**

**Why Critical:** Prevents agents from bypassing the enforcement system

### ✅ **5. Trust Levels**
- **LOW trust level verification**
- **MEDIUM trust level verification** 
- **HIGH trust level verification**
- **CRITICAL trust level verification**

**Why Critical:** Different security levels for different use cases

### ✅ **6. Replay Protection**
- **Nonce-based replay attack prevention**
- **Unique nonce requirement enforcement**
- **Temporal nonce validation**

**Why Critical:** Prevents replay attacks and ensures request freshness

### ✅ **7. Error Handling**
- **Tool execution error handling**
- **Signature verification failures**
- **Registry communication errors**
- **Graceful degradation**

**Why Critical:** Robust operation under failure conditions

### ✅ **8. Performance Requirements**
- **Signature generation performance**
- **Verification performance**
- **Memory usage tracking**
- **Throughput testing**

**Why Critical:** Ensures production-ready performance

### ✅ **9. End-to-End Integration**
- **Complete system workflow**
- **Payment and weather tool integration**
- **Cross-component verification**
- **Real-world scenario testing**

**Why Critical:** Proves the system works as a complete solution

## 🚨 Security Testing Principles

### ❌ **NO BYPASSES ALLOWED**
```python
# ❌ REMOVED - All security bypasses eliminated:
result = await tool(data, verify_response=False)  # SECURITY VIOLATION

# ✅ ENFORCED - Full verification always:
result = await tool(data)  # verify_response=True by default
```

### ✅ **HONEST TESTING**
- All tests use **full signature verification**
- All tests use **real cryptographic operations**
- All tests verify **actual security properties**
- No mocking of security-critical components

### ✅ **PRODUCTION SCENARIOS**
- Tests simulate **real attack vectors**
- Tests verify **performance under load**
- Tests ensure **proper error handling**
- Tests validate **complete workflows**

## 📊 Test Results Summary

### ✅ **Security Features Verified**
- **100% signature verification** in all tests
- **Zero tolerance** for bypasses or shortcuts  
- **Real cryptographic operations** throughout
- **Comprehensive error testing**

### ✅ **Performance Verified**
- **<100ms average** signature operations (generous for testing)
- **Concurrent execution** support verified
- **Memory efficiency** validated
- **Production-ready** throughput confirmed

### ✅ **Integration Verified**
- **End-to-end workflows** tested
- **Cross-component** verification working
- **Real-world scenarios** passing
- **Complete audit trail** functioning

## 🎯 Key Testing Principles

### 1. **Security First**
Every test operates with **full security enabled** - no shortcuts or bypasses that could mask security issues.

### 2. **Real Scenarios**  
Tests simulate **actual usage patterns** and **attack vectors** that could occur in production.

### 3. **Performance Aware**
Tests verify that security measures **don't compromise performance** beyond acceptable limits.

### 4. **Comprehensive Coverage**
Tests cover **all major features** and **failure modes** to ensure robust operation.

### 5. **Production Ready**
Tests validate that the library is **ready for production deployment** with real workloads.

## 🛠️ Development Usage

### Quick Test
```bash
# Run the comprehensive test suite
python -m pytest tests/test_comprehensive_features.py -v
```

### Development Workflow
```bash
# Install in development mode
pip install -e ".[dev]"

# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=trustchain --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Real API Testing (Optional)
```bash
# Set API keys for testing with real LLMs
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Test with real APIs
python tests/test_real_llm_clean.py
```

## 🎉 **Why This Testing Approach Works**

### ✅ **Complete Coverage**
Every major feature is tested with real security verification - no components are mocked or bypassed.

### ✅ **Attack Resistance** 
Tests verify resistance to actual attack vectors like replay attacks, signature tampering, and bypass attempts.

### ✅ **Production Ready**
Tests ensure the library performs well under realistic loads and handles errors gracefully.

### ✅ **Developer Confidence**
Comprehensive testing gives developers confidence that security features work as designed.

---

🎯 **Ready for production deployment with verified security!** 🛡️ 