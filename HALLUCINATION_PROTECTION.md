# 🛡️ TrustChain Hallucination Protection

## Overview

TrustChain now provides **comprehensive protection against LLM hallucinations** by ensuring that all tool-related claims in agent responses are backed by cryptographic signatures. This prevents AI agents from "making up" tool results and ensures factual accuracy.

## 🎯 The Problem

Traditional AI agents can hallucinate tool results:

```python
# LLM might respond with:
"I checked the weather API: Temperature in Moscow is 25°C, humidity 60%"

# But the weather tool was NEVER actually called!
```

This creates **false confidence** in AI-generated information and can lead to critical errors in production systems.

## ✅ TrustChain Solution

### 1. **Cryptographic Verification**
Every tool execution produces a signed response that cannot be forged.

### 2. **Claim Extraction & Validation**
LLM responses are parsed for factual claims and cross-referenced with verified tool signatures.

### 3. **Automatic Interception**
Agent responses are automatically validated before being returned to users.

## 🚀 Quick Start

### Basic Detection

```python
from trustchain import (
    get_signature_engine, MemoryRegistry,
    create_hallucination_detector, LLMResponseInterceptor
)

# Setup
registry = MemoryRegistry()
signature_engine = get_signature_engine(registry)
detector = create_hallucination_detector(signature_engine)
interceptor = LLMResponseInterceptor(detector)

# Validate LLM response
llm_response = "I checked weather: London is 18°C"
validated_response, validation = interceptor.intercept(llm_response)

if not validation.valid:
    print(f"⚠️ Hallucination detected: {validation.message}")
    for hallucination in validation.hallucinations:
        print(f"  - {hallucination.claim_text}")
```

### Verified Tools

```python
from trustchain import TrustedTool

@TrustedTool("weather_api", require_nonce=False)
def get_weather(city: str) -> dict:
    return {
        "temperature": 22.5,
        "humidity": 65,
        "city": city
    }

# When this tool runs, it automatically registers 
# its results with the hallucination detector
result = get_weather("London")
```

### LangChain Integration

```python
from trustchain.integrations.langchain import (
    create_verified_agent_executor,
    make_langchain_tool
)

# Convert TrustChain tools to LangChain tools
weather_tool = make_langchain_tool(get_weather._trustchain_tool, signature_engine)

# Create protected agent
agent_executor = create_verified_agent_executor(
    agent=your_agent,
    trusted_tools=[get_weather._trustchain_tool],
    signature_engine=signature_engine,
    hallucination_detector=detector,
    strict_mode=True  # Reject ALL unverified claims
)

# Agent responses are automatically validated
response = agent_executor.run("What's the weather in Tokyo?")
```

## 🔧 Core Components

### 1. **HallucinationDetector**

The main engine that validates LLM responses:

```python
from trustchain.monitoring.hallucination_detector import HallucinationDetector

detector = HallucinationDetector(signature_engine)
detector.set_strict_mode(True)  # Require verification for ALL claims

validation = detector.validate_response(llm_response)
print(f"Valid: {validation.valid}")
print(f"Confidence: {validation.confidence_score}")
```

### 2. **ClaimExtractor**

Automatically identifies factual claims in text:

```python
from trustchain.monitoring.hallucination_detector import ClaimExtractor

extractor = ClaimExtractor()
claims = extractor.extract_claims("I checked the API: Price is $150")

for claim in claims:
    print(f"Tool: {claim.tool_name}")
    print(f"Claim: {claim.claim_text}")
    print(f"Result: {claim.claimed_result}")
```

### 3. **LLMResponseInterceptor**

Intercepts and validates responses before they reach users:

```python
from trustchain.monitoring.hallucination_detector import LLMResponseInterceptor

interceptor = LLMResponseInterceptor(detector)
interceptor.auto_reject = True  # Auto-generate safe responses

safe_response, validation = interceptor.intercept(risky_response)
```

### 4. **VerificationRegistry**

Tracks verified tool results:

```python
# Tool results are automatically registered
weather_result = get_weather("Paris")

# Check if claim has verification
has_verification = detector.verification_registry.has_verification_for_claim(claim)
```

## 🔒 Protection Modes

### 1. **Permissive Mode** (Default)
- Only validates obvious tool claims
- Allows general conversation
- Good for most applications

```python
detector.set_strict_mode(False)  # Default
```

### 2. **Strict Mode**
- Requires verification for ALL factual claims
- Blocks any unverified statements
- Best for critical applications

```python
detector.set_strict_mode(True)
interceptor.auto_reject = True
```

## 🔍 Detection Patterns

The system recognizes these hallucination patterns:

### Tool Call Claims
```
"I checked the weather API: ..."
"According to stock_api, AAPL is ..."
"The weather tool returned ..."
"From the database: user count is ..."
```

### Structured Data
```
"Temperature: 25°C"
"Price: $150.50" 
"Status: Active"
{"temperature": 25, "humidity": 60}
```

### API References
```
"weather_api returned {...}"
"stock_tool gave me {...}"
"database_query showed {...}"
```

## 📊 Validation Results

### ValidationResult Structure
```python
@dataclass
class ValidationResult:
    valid: bool                           # Overall validity
    hallucinations: List[HallucinatedClaim] # Detected hallucinations  
    verified_claims: List[str]            # Claims backed by signatures
    message: str                          # Human-readable summary
    confidence_score: float               # 0.0-1.0 confidence
```

### Example Output
```python
ValidationResult(
    valid=False,
    hallucinations=[
        HallucinatedClaim(
            claim_text="Temperature in London is 18°C",
            tool_name="weather",
            claimed_result="18°C",
            confidence=0.0
        )
    ],
    verified_claims=[],
    message="❌ Detected 1 unverified claim(s) that may be hallucinated",
    confidence_score=0.0
)
```

## 🔗 Framework Integrations

### LangChain
- `TrustedLangChainTool` - Verified tool wrapper
- `VerifiedAgentExecutor` - Protected agent execution
- `VerifiedAgentCallbackHandler` - Response validation callbacks

### AutoGen (Planned)
- Tool verification for multi-agent conversations
- Cross-agent claim validation

### CrewAI (Planned)
- Crew-wide verification policies
- Role-based verification requirements

## ⚡ Performance

### Benchmarks
- **Claim extraction**: ~1ms per response
- **Signature verification**: ~0.5ms per claim
- **Overall overhead**: <5ms for typical responses

### Optimizations
- Regex pattern matching for speed
- Caching of verification results
- Batch validation for multiple claims

## 🛠️ Advanced Usage

### Custom Claim Patterns

```python
from trustchain.monitoring.hallucination_detector import ClaimExtractor

extractor = ClaimExtractor()
extractor.TOOL_RESULT_PATTERNS.append(
    r"Database shows:\s*(.+)"  # Custom pattern
)
```

### Integration with Monitoring

```python
# Log all hallucination attempts
def on_hallucination(validation: ValidationResult):
    for h in validation.hallucinations:
        logger.warning(f"Hallucination detected: {h.claim_text}")

interceptor.on_hallucination = on_hallucination
```

### Multi-Modal Support

```python
# Validate claims across text, code, and structured data
validator = MultiModalValidator(detector)
validation = validator.validate_mixed_content(response)
```

## 🚨 Error Handling

### HallucinationError
Raised when hallucinations are detected in strict mode:

```python
try:
    response = agent.run(query)
except HallucinationError as e:
    print(f"Blocked {len(e.hallucinations)} hallucinated claims")
    for h in e.hallucinations:
        print(f"  - {h.claim_text}")
```

### Graceful Degradation
```python
# Fallback to safe responses
interceptor = LLMResponseInterceptor(detector)
interceptor.auto_reject = True

safe_response, validation = interceptor.intercept(risky_response)
# Returns: "⚠️ I cannot verify some information. Please try again."
```

## 📈 Best Practices

### 1. **Register All Tool Executions**
```python
# Ensure all tools are @TrustedTool decorated
@TrustedTool("my_api")
def my_function():
    return data
```

### 2. **Use Appropriate Modes**
```python
# Development: Permissive mode
detector.set_strict_mode(False)

# Production: Strict mode  
detector.set_strict_mode(True)
```

### 3. **Monitor Validation Results**
```python
# Track hallucination attempts
validation_logger = ValidationLogger()
interceptor.add_callback(validation_logger.log)
```

### 4. **Educate Your LLM**
Include in system prompts:
```
"Only state facts that come from verified tool executions. 
Never guess or hallucinate tool results."
```

## 🔮 Roadmap

### Short Term
- ✅ Basic hallucination detection
- ✅ LangChain integration
- 🚧 AutoGen integration
- 🚧 CrewAI integration

### Medium Term
- 🔮 NLP-based claim matching
- 🔮 Confidence scoring improvements
- 🔮 Multi-modal validation
- 🔮 Real-time monitoring dashboard

### Long Term
- 🔮 LLM fine-tuning for verification
- 🔮 Federated verification networks
- 🔮 Zero-knowledge claim proofs

## 📝 Examples

See `examples/hallucination_detection_demo.py` for comprehensive examples covering:

- Basic detection patterns
- LangChain integration  
- Strict mode operation
- Agent protection scenarios
- Real-world use cases

## 🤝 Contributing

We welcome contributions to improve hallucination detection:

1. **New Detection Patterns** - Help identify more hallucination patterns
2. **Framework Integrations** - Add support for more AI frameworks  
3. **Performance Optimizations** - Make detection faster and more accurate
4. **Documentation** - Improve examples and guides

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/trustchain)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/trustchain/discussions)
- **Email**: support@trustchain.ai

---

**TrustChain: Making AI Agents Trustworthy Through Cryptographic Verification** 🛡️ 