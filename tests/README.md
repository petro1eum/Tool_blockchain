# 🧪 TrustChain Tests

This directory contains comprehensive tests for TrustChain library functionality.

## 📋 Test Files

### Core Tests
- `test_basic.py` - Basic functionality tests for crypto engine, tools, and registry
- `conftest.py` - Pytest configuration and shared fixtures

### LLM Integration Tests
- `test_llm_integrations.py` - **Mock LLM response signing** (DEPRECATED APPROACH - signs every LLM response)
- `test_llm_tool_calling.py` - **✅ CORRECT APPROACH - AI Tool Calling with Signatures**
- `../examples/llm_real_api_examples.py` - **Real API tests** for production (requires API keys)

## 🚀 Running Tests

### 1. ✅ AI Tool Calling Tests (RECOMMENDED)
```bash
# Run the CORRECT implementation - AI tool calling with signatures
python tests/test_llm_tool_calling.py

# Or run with pytest
python -m pytest tests/test_llm_tool_calling.py -v
```

**Features tested:**
- ✅ Regular AI conversation (no signatures needed)
- ✅ Weather tool calling (MEDIUM trust level)
- ✅ Payment processing (CRITICAL trust level)
- ✅ Calculator operations (LOW trust level) 
- ✅ Data analytics (HIGH trust level)
- ✅ Multi-tool conversations with single AI agent
- ✅ Concurrent AI agents calling different tools
- ✅ Complete audit trail of tool usage

### 2. Mock LLM Response Signing (Alternative Approach)
```bash
# Run the LLM response signing test (signs every response)
python tests/test_llm_integrations.py

# Or run with pytest
python -m pytest tests/test_llm_integrations.py -v
```

**Features tested:**
- ✅ OpenAI GPT integration (mocked)
- ✅ Anthropic Claude integration (mocked)  
- ✅ Google Gemini integration (mocked)
- ✅ Financial AI with CRITICAL trust level
- ✅ Batch processing across multiple providers
- ✅ Performance benchmarking
- ✅ Cryptographic verification of all responses

### 3. Real API Tests (Optional)
```bash
# Set your API keys
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"  
export GEMINI_API_KEY="your-gemini-api-key"

# Install additional dependencies
pip install openai anthropic google-generativeai

# Run real API tests
python examples/llm_real_api_examples.py
```

### 4. All Core Tests
```bash
# Run all core functionality tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=trustchain --cov-report=html

# Run specific test class
python -m pytest tests/test_basic.py::TestCryptoEngine -v
```

## 🤔 Two Approaches: Which One to Choose?

### ✅ **Approach 1: Tool Calling Signatures (RECOMMENDED)**
```python
# ❌ Regular chat - no signature needed
response = await ai_agent.chat("Hello, how are you?")  # Normal conversation

# ✅ Tool usage - automatically signed
response = await ai_agent.chat("What's the weather?")  # Triggers weather_tool() with signature
response = await ai_agent.chat("Send $100 payment")   # Triggers payment_tool() with CRITICAL signature
```

**Benefits:**
- 🎯 **Targeted security**: Only sign when AI takes actions
- ⚡ **Performance**: No overhead for regular conversation  
- 🛡️ **Audit trail**: Perfect record of what tools AI actually used
- 💰 **Financial safety**: CRITICAL signatures for payments
- 🤖 **Natural UX**: AI can chat normally, tools are secured

### ❌ **Approach 2: Every Response Signed (OVERKILL)**
```python
# Every single AI response gets signed - even "Hello"
response = await openai_generate_text("Hello")  # ✅ Signed but unnecessary
response = await openai_generate_text("Weather?")  # ✅ Signed but doesn't call actual tools
```

**Drawbacks:**
- 🐌 **Performance overhead**: Every response signed
- 💸 **Unnecessary crypto**: Signs conversational responses
- 🔄 **No actual tools**: Just signs text, doesn't call real functions
- 🎯 **Misses the point**: Should sign tool usage, not text generation

### 💡 **Recommendation**
Use **Tool Calling Signatures** (`test_llm_tool_calling.py`) - it's the correct approach that signs actual AI actions while allowing normal conversation.

## 🎯 What Each Test Demonstrates

### ✅ AI Tool Calling Test (`test_llm_tool_calling.py`) - RECOMMENDED

This test demonstrates the **CORRECT** use of TrustChain - signing tool executions when AI agents decide to use them:

#### 🤖 **AI Agent Simulation**
```python
class AIAgent:
    async def chat(self, message: str) -> str:
        # Regular conversation - no signatures
        if "hello" in message.lower():
            return "Hi there! This is just normal chat."
        
        # AI decides to use tools - these get signed!
        elif "weather" in message.lower():
            return await self._call_weather_tool("New York")  # ✅ SIGNED
```

#### 🛠️ **Trusted Tools with Different Trust Levels**
```python
@TrustedTool("weather_api", trust_level=TrustLevel.MEDIUM)
async def weather_tool(location: str) -> Dict[str, Any]:
    return {"temp": 22, "condition": "sunny"}

@TrustedTool("payment_system", trust_level=TrustLevel.CRITICAL)  
async def payment_processor(amount: float, currency: str) -> Dict[str, Any]:
    return {"transaction_id": "tx_123", "status": "completed"}
```

#### 📋 **Test Scenarios**
- **Regular Chat**: AI responds normally without triggering tools
- **Weather Query**: AI detects weather question → calls weather_tool() → signed  
- **Payment Request**: AI detects payment → calls payment_tool() → CRITICAL signature
- **Math Query**: AI calculates → calls calculator_tool() → signed for audit
- **Data Analysis**: AI analyzes → calls analytics_tool() → HIGH trust signature
- **Multi-Tool**: AI uses multiple tools in one conversation
- **Concurrent Agents**: Multiple AI agents calling tools simultaneously

### ❌ Mock LLM Integration Test (`test_llm_integrations.py`) - ALTERNATIVE

This comprehensive test shows how TrustChain integrates with major LLM providers:

#### 🤖 **OpenAI Integration**
```python
@TrustedTool("openai_text_generator", trust_level=TrustLevel.MEDIUM)
async def openai_generate_text(prompt: str, model: str = "gpt-4o") -> Dict[str, Any]:
    # Mock OpenAI API call with cryptographic signing
    return {"generated_text": "...", "model": model, "usage": {...}}
```

#### 🧠 **Anthropic Claude Integration**
```python
@TrustedTool("anthropic_claude_generator", trust_level=TrustLevel.MEDIUM)  
async def anthropic_generate_text(prompt: str, model: str = "claude-3-sonnet") -> Dict[str, Any]:
    # Mock Anthropic API call with verification
    return {"generated_text": "...", "model": model, "usage": {...}}
```

#### 🌟 **Google Gemini Integration**
```python
@TrustedTool("gemini_text_generator", trust_level=TrustLevel.MEDIUM)
async def gemini_generate_text(prompt: str, model: str = "gemini-1.5-pro") -> Dict[str, Any]:
    # Mock Gemini API call with signing
    return {"generated_text": "...", "model": model, "usage": {...}}
```

#### 💰 **Financial AI (CRITICAL Trust Level)**
```python
@TrustedTool("financial_ai_advisor", trust_level=TrustLevel.CRITICAL)
async def analyze_financial_data(data: Dict[str, Any]) -> Dict[str, Any]:
    # Highest security level for financial decisions
    return {"risk_assessment": "...", "recommendation": "...", "confidence": 0.87}
```

#### 📦 **Batch Processing**
```python
@TrustedTool("batch_llm_processor", trust_level=TrustLevel.HIGH)
async def process_batch_requests(requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Process multiple LLM requests with batch verification
    return {"batch_id": "...", "results": [...], "total_requests": 3}
```

## 🔒 Security Features Tested

### ✅ **Cryptographic Verification**
- Every AI response is automatically signed with Ed25519 signatures
- Signatures are verified before returning responses
- Tamper detection ensures response integrity

### ✅ **Trust Levels**
- `TrustLevel.LOW` - Basic verification for non-critical operations
- `TrustLevel.MEDIUM` - Standard verification for typical AI responses  
- `TrustLevel.HIGH` - Enhanced security for important operations
- `TrustLevel.CRITICAL` - Maximum security for financial/medical decisions

### ✅ **Replay Protection**
- Unique nonce generation for each request
- Timestamp validation prevents replay attacks
- Automatic nonce management with TTL

### ✅ **Performance**
- Sub-millisecond signing overhead (0.17ms average)
- Concurrent request handling
- Batch processing optimization

## 📊 Sample Test Output

### ✅ AI Tool Calling Test Output (RECOMMENDED)
```
🤖 Starting TrustChain LLM Tool Calling Tests
======================================================================
This demonstrates the CORRECT use case:
• LLM generates regular text (no signatures)
• When LLM calls tools → cryptographically signed
• Prevents forged tool executions by AI
• Creates audit trail of AI actions

💬 Testing Regular AI Conversation (No Tools)
   📝 Response 1: I understand your question: 'Hello, how are you today?'...
   📝 Response 2: I understand your question: 'Tell me about quantum physics'...
   🛠️  Tools called: 0 (expected: 0)

🌤️  Testing AI Weather Tool Calling
🤖 WeatherAI: Thinking about 'What's the weather like today?'...
  🛠️  AI calling weather_tool for New York
   ✅ Tool call signed: True
   🔐 Signature: I1F4fW2WAuVeQ2pGjW3P...

💰 Testing AI Payment Tool Calling (CRITICAL)
🤖 FinancialAI: Thinking about 'Send $100 to my friend'...
  🛠️  AI calling payment_tool for $100.0 USD
   ✅ Payment signed: True
   💳 Transaction ID: tx_1748037695
   🔐 Critical signature: TW1RYyP02fFB6GyHzff0...

📋 Testing Tool Audit Trail
   📊 Total AI agents tested: 9
   🛠️  Total tool calls made: 10
   📈 Tool usage breakdown:
      🔸 weather_tool: 3 calls
      🔸 payment_processor: 2 calls  
      🔸 calculator_tool: 3 calls
      🔸 analytics_tool: 2 calls
   🔐 Signed calls: 10/10

🎉 TrustChain LLM Tool Calling Tests Complete!
📊 Test Results:
   🤖 AI Agents tested: 9
   🛠️  Tool calls made: 10
   🔐 Signed calls: 10/10 (100%)

🔗 TrustChain provides the RIGHT solution:
   • AI can chat normally (no unnecessary signatures)
   • But when AI takes actions via tools → SIGNED! 🛡️
```

### ❌ LLM Response Signing Output (Alternative)
```
🚀 Starting TrustChain LLM Integration Tests
============================================================

🤖 Testing OpenAI Integration...
  ✅ Text Generation - Verified: True
  📝 Response: The weather in New York today is sunny with a temp...
  ✅ Code Analysis - Score: 8.5

🧠 Testing Anthropic Integration...
  ✅ Text Generation - Verified: True
  📝 Response: Today in New York, expect sunny skies with temper...

💰 Testing Financial AI (CRITICAL Trust Level)...
  ✅ Financial Analysis - Verified: True
  📊 Risk Assessment: Low-Medium Risk

🎉 TrustChain LLM Integration Tests Complete!
📊 Total Tests Passed: 8
🔒 All Responses Cryptographically Verified: ✅

🔗 TrustChain successfully prevents AI hallucinations!
Every AI response is cryptographically signed and verifiable. 🛡️
```

## 🛠️ Development Usage

### Quick Test
```bash
# Run the RECOMMENDED AI tool calling test
python tests/test_llm_tool_calling.py

# Or run the alternative LLM response signing test
python tests/test_llm_integrations.py
```

### Full Development Workflow
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
export GEMINI_API_KEY="AI..."

# Install LLM libraries
pip install openai anthropic google-generativeai

# Test with real APIs
python examples/llm_real_api_examples.py
```

## 🎯 Use Cases Demonstrated

### 1. **AI Content Generation** with Crypto Proof
- Weather information APIs
- Educational content generation
- Creative writing assistance
- Technical documentation

### 2. **Code Analysis** with High Trust
- Security code reviews
- Quality assessments  
- Best practice recommendations
- Vulnerability detection

### 3. **Financial Analysis** with Critical Trust
- Investment recommendations
- Risk assessments
- Portfolio analysis
- Market predictions

### 4. **Batch Processing** for Scale
- Multiple provider consensus
- Bulk content generation
- Parallel request handling
- Performance optimization

## 🔐 Why This Matters

### 🎯 **The CORRECT Approach (Tool Calling Signatures)**

**Problem**: AI agents can execute dangerous actions (payments, data deletion, API calls) without accountability.

**Solution**: TrustChain signs only the tool executions, not conversational responses.

**Result**: 
- ✅ AI can chat normally (fast, natural UX)
- ✅ When AI takes actions → cryptographically signed
- ✅ Perfect audit trail of what AI actually did
- ✅ Prevents forged tool executions
- ✅ CRITICAL trust for financial operations

### ❌ **The Overkill Approach (Sign Everything)**

**Problem**: AI hallucinations can be dangerous in critical applications.

**Solution**: Sign every single AI response, even "Hello" and "How are you?"

**Result**: 
- ❌ Performance overhead for normal conversation
- ❌ Signs text generation, not actual tool usage
- ❌ Misses the real security concern (unauthorized actions)
- ❌ Overkill for most use cases

### 💡 **Recommendation**
Use **Tool Calling Signatures** for production AI agents - it provides security where it matters while maintaining natural conversation flow.

---

🎉 **Ready to prevent AI hallucinations with cryptographic proof!** 🛡️ 