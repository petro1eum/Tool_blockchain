# 🔗 TrustChain

**Cryptographically signed AI tool responses for preventing hallucinations**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

TrustChain is a production-ready Python library that provides cryptographic signatures for AI tool responses, preventing agent hallucinations and ensuring verifiable execution of tools.

## 🚀 Quick Start

```python
from trustchain import TrustedTool

@TrustedTool("weather_api")
async def get_weather(city: str) -> dict:
    """Get weather data with cryptographic verification."""
    return {
        "city": city,
        "temperature": 22.5,
        "conditions": "Sunny"
    }

# Automatically signed and verified
response = await get_weather("Paris")
print(f"Verified: {response.is_verified}")
print(f"Data: {response.data}")
```

## 🛡️ Key Features

### **Anti-Hallucination Protection**
- **Cryptographic Signatures**: Every tool response is cryptographically signed
- **Automatic Verification**: Responses are verified on creation and access
- **Hallucination Detection**: Advanced semantic analysis detects fake claims
- **Zero Bypass Tolerance**: All tool calls must go through verification

### **Security Features**
- **Tool Execution Enforcement**: Automatic interception of all tool calls
- **Replay Protection**: Built-in nonce system prevents replay attacks
- **Trust Levels**: Different security levels for different use cases
- **Real-time Monitoring**: Complete audit trail of all executions

### **Production Ready**
- **High Performance**: <5ms overhead for signature operations
- **Thread Safe**: Safe for concurrent usage
- **Multiple Backends**: Memory, Redis, Kafka support
- **Comprehensive Testing**: 95%+ test coverage

## 📦 Installation

```bash
pip install trustchain
```

## 🔧 Core Components

### **1. Trusted Tools**

Create verified tools with decorators:

```python
from trustchain import TrustedTool, TrustLevel

@TrustedTool("financial_api", trust_level=TrustLevel.HIGH)
async def process_payment(amount: float, recipient: str) -> dict:
    return {
        "transaction_id": "tx_123",
        "amount": amount,
        "status": "completed"
    }
```

### **2. Hallucination Detection**

Automatically detect fake claims:

```python
from trustchain import create_hallucination_detector, get_signature_engine

detector = create_hallucination_detector(get_signature_engine())
validation = detector.validate_response("I checked the weather: 25°C in London")

if not validation.valid:
    print(f"Detected {len(validation.hallucinations)} fake claims")
```

### **3. Enforcement System**

Prevent unauthorized tool access:

```python
from trustchain import create_tool_enforcer, enable_automatic_enforcement

# Create enforcer
enforcer = create_tool_enforcer(signature_engine, [weather_tool, payment_tool])

# Enable automatic interception
enable_automatic_enforcement(enforcer, strict_mode=True)

# All tool calls now go through verification
```

## 🎯 Use Cases

### **AI Agent Security**
Prevent agents from claiming tool results without actually executing them:

```python
# ❌ Agent cannot fake this
# "I checked the weather API: Temperature in Moscow is 25°C"

# ✅ Only real tool executions allowed
response = await get_weather("Moscow")  # Cryptographically signed
```

### **Financial Applications**
High-security tools for monetary operations:

```python
@TrustedTool("payment_processor", trust_level=TrustLevel.CRITICAL)
async def transfer_funds(amount: float, from_account: str, to_account: str):
    # Every transaction is cryptographically verified
    return execute_transfer(amount, from_account, to_account)
```

### **Audit Compliance**
Complete verification trail for compliance:

```python
# Every tool execution creates an immutable audit record
execution = enforcer.execute_tool("compliance_check", data)
print(f"Audit trail: {execution.audit_record}")
```

## 🔒 Security Architecture

### **Multi-Layer Protection**

1. **Cryptographic Signing**: Ed25519 signatures for all responses
2. **Automatic Interception**: All tool calls go through verification
3. **Semantic Analysis**: Advanced AI claim detection
4. **Real-time Monitoring**: Immediate detection of bypass attempts

### **Trust Levels**

- `TrustLevel.LOW`: Basic verification, minimal overhead
- `TrustLevel.MEDIUM`: Standard verification with replay protection
- `TrustLevel.HIGH`: Enhanced security for sensitive operations
- `TrustLevel.CRITICAL`: Maximum security for high-risk operations

## 📊 Performance

- **Signature Generation**: ~2ms average
- **Verification**: ~3ms average
- **Memory Usage**: ~10MB base overhead
- **Throughput**: 1000+ operations/second

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Agent      │───▶│  TrustChain      │───▶│  Verified Tool  │
│                 │    │  Interceptor     │    │  Execution      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Signature       │
                       │  Verification    │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Audit Trail     │
                       │  & Monitoring    │
                       └──────────────────┘
```

## 📚 Examples

See the `examples/` directory for complete demonstrations:

- **`basic_usage.py`**: Core functionality and simple tools
- **`security_vulnerability_demo.py`**: Security features demonstration  
- **`full_enforcement_demo.py`**: Complete enforcement system
- **`llm_real_api_examples.py`**: Real-world LLM integrations

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🆘 Support

- **Documentation**: See [QUICKSTART.md](QUICKSTART.md)
- **Issues**: [GitHub Issues](https://github.com/yourusername/trustchain/issues)
- **Email**: edcherednik@gmail.com
- **Telegram**: @EdCher

---

**Built for Production** | **Security First** | **Zero Compromise** 