# 🚀 TrustChain Quick Start Guide

Get up and running with TrustChain in 5 minutes! This guide will show you how to create cryptographically signed AI tool responses to prevent hallucinations.

## 📋 Prerequisites

- Python 3.8 or higher
- pip package manager

## 🔧 Installation

### Basic Installation
```bash
pip install trustchain
```

### With Optional Features
```bash
# With Kafka support
pip install trustchain[kafka]

# With Redis support  
pip install trustchain[redis]

# With AI framework integrations
pip install trustchain[ai]

# Full installation
pip install trustchain[all]
```

## 🎯 Your First Trusted Tool

Create a simple trusted tool in just a few lines:

```python
import asyncio
from trustchain import TrustedTool

@TrustedTool("weather_api_v1")
async def get_weather(location: str) -> dict:
    """Get weather information for a location."""
    return {
        "location": location,
        "temperature": 22.5,
        "humidity": 65,
        "conditions": "Partly cloudy"
    }

async def main():
    # Call the trusted tool
    response = await get_weather("New York")
    
    print(f"Tool ID: {response.tool_id}")
    print(f"Data: {response.data}")
    print(f"Verified: {response.is_verified}")
    print(f"Signature: {response.signature.signature[:20]}...")

if __name__ == "__main__":
    asyncio.run(main())
```

**Output:**
```
Tool ID: weather_api_v1
Data: {'location': 'New York', 'temperature': 22.5, 'humidity': 65, 'conditions': 'Partly cloudy'}
Verified: True
Signature: iJ8K9xQlM2nP7vB3z...
```

## 🔐 Security Levels

Choose the right security level for your use case:

### High-Security Financial Tool
```python
from trustchain import TrustedTool, TrustLevel, SignatureAlgorithm

@TrustedTool(
    "payment_processor_v1",
    trust_level=TrustLevel.HIGH,
    algorithm=SignatureAlgorithm.ED25519
)
async def process_payment(amount: float, recipient: str) -> dict:
    """Process a secure payment."""
    return {
        "transaction_id": f"tx_{int(time.time())}",
        "amount": amount,
        "recipient": recipient,
        "status": "completed"
    }
```

### Low-Latency Tool (No Nonce)
```python
@TrustedTool(
    "quick_lookup_v1",
    require_nonce=False,  # Skip nonce for speed
    trust_level=TrustLevel.LOW
)
def lookup_value(key: str) -> dict:
    """Quick cache lookup."""
    cache = {"user123": "John Doe", "user456": "Jane Smith"}
    return {"key": key, "value": cache.get(key, "Not found")}
```

### Multi-Signature Tool
```python
from trustchain import multi_signature_tool

@multi_signature_tool(
    "critical_operation_v1",
    required_signatures=["security", "compliance", "operations"],
    threshold=2  # Requires 2 out of 3 signatures
)
async def critical_operation(data: dict) -> dict:
    """Critical operation requiring multiple approvals."""
    return {"approved": True, "data": data}
```

## 🛠️ CLI Usage

TrustChain comes with a powerful CLI tool:

### Initialize Configuration
```bash
trustchain init --registry memory
```

### Generate Keys
```bash
trustchain keygen --tool-id my_tool --algorithm Ed25519
```

### Run Tests
```bash
trustchain test
```

### Monitor Operations
```bash
trustchain monitor --interval 5
```

## 📊 Error Handling and Validation

```python
from trustchain import TrustedTool, ToolExecutionError, NonceReplayError

@TrustedTool("validator_v1")
async def validate_data(value: int) -> dict:
    """Validate input data."""
    if value < 0:
        raise ValueError("Value must be positive")
    
    return {"value": value, "valid": True}

async def main():
    try:
        # Valid call
        response = await validate_data(42)
        print(f"Valid response: {response.data}")
        
        # Invalid call
        await validate_data(-5)
        
    except ToolExecutionError as e:
        print(f"Tool execution failed: {e}")
    except NonceReplayError as e:
        print(f"Replay attack detected: {e}")
```

## 📈 Monitoring and Statistics

Track your tool performance:

```python
@TrustedTool("analytics_v1")
async def analyze_data(numbers: list) -> dict:
    """Analyze a list of numbers."""
    return {
        "count": len(numbers),
        "sum": sum(numbers),
        "average": sum(numbers) / len(numbers) if numbers else 0
    }

async def main():
    # Execute multiple times
    for i in range(5):
        await analyze_data(list(range(i, i+10)))
    
    # Check statistics
    stats = await analyze_data.get_statistics()
    print(f"Total calls: {stats['stats']['total_calls']}")
    print(f"Success rate: {stats['success_rate']:.2%}")
    print(f"Avg execution time: {stats['avg_execution_time_ms']:.2f}ms")
```

## 🔗 Integration with AI Frameworks

### LangChain Integration
```python
from trustchain.integrations import make_langchain_tool

# Convert to LangChain tool
weather_langchain_tool = make_langchain_tool(get_weather)

# Use in LangChain agent
from langchain.agents import create_openai_functions_agent
agent = create_openai_functions_agent(llm, [weather_langchain_tool])
```

### OpenAI Function Calling
```python
from trustchain.integrations import OpenAITrustedFunction

@OpenAITrustedFunction({
    "name": "get_weather",
    "description": "Get weather for a location",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {"type": "string"}
        }
    }
})
async def get_weather_openai(location: str) -> dict:
    return {"temperature": 15, "location": location}
```

## 🏢 Production Configuration

For production deployments, use Redis or Kafka:

### Redis Configuration
```python
from trustchain import RedisRegistry, TrustedTool

# Create Redis registry
registry = RedisRegistry(
    host="localhost",
    port=6379,
    db=0
)

@TrustedTool("production_tool_v1", registry=registry)
async def production_tool(data: dict) -> dict:
    return {"processed": True, "data": data}
```

### Kafka Configuration
```python
from trustchain import KafkaRegistry

# Create Kafka registry
registry = KafkaRegistry(
    bootstrap_servers="localhost:9092",
    schema_registry_url="http://localhost:8081"
)

@TrustedTool("distributed_tool_v1", registry=registry)
async def distributed_tool(data: dict) -> dict:
    return {"processed": True, "distributed": True}
```

## 🔍 Debugging and Troubleshooting

### Enable Debug Mode
```python
from trustchain.utils.config import TrustChainConfig

config = TrustChainConfig()
config.debug = True
config.monitoring.log_level = "DEBUG"
```

### Verify Signatures Manually
```python
from trustchain.core.signatures import get_signature_engine

# Get response
response = await my_tool("test data")

# Manual verification
signature_engine = get_signature_engine()
verification_result = signature_engine.verify_response(response)

print(f"Valid: {verification_result.valid}")
print(f"Error: {verification_result.error_message}")
```

## 📚 Next Steps

Now that you have the basics, explore more advanced features:

1. **[Architecture Deep Dive](docs/architecture.md)** - Understanding the internals
2. **[Security Model](docs/security.md)** - Cryptographic guarantees  
3. **[API Reference](docs/api.md)** - Complete API documentation
4. **[Examples](examples/)** - Real-world use cases
5. **[Deployment Guide](docs/deployment.md)** - Production best practices

## 🤝 Getting Help

- 📖 **Documentation**: [trustchain.readthedocs.io](https://trustchain.readthedocs.io/)
- 🐛 **Issues**: [GitHub Issues](https://github.com/trustchain/trustchain/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/trustchain/trustchain/discussions)
- 📧 **Email**: info@trustchain.dev

## ✨ Key Benefits Recap

✅ **Prevent AI Hallucinations** - Cryptographic proof of authentic responses  
✅ **Replay Protection** - Nonce-based protection against replay attacks  
✅ **Zero Trust Architecture** - Verify everything, trust nothing  
✅ **Performance Monitoring** - Built-in statistics and metrics  
✅ **Easy Integration** - Works with existing AI frameworks  
✅ **Production Ready** - Scalable with Redis/Kafka backends  

Start building more trustworthy AI systems today with TrustChain! 🚀 