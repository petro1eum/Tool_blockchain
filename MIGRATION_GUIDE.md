# Migration Guide: TrustChain v1 to v2

This guide helps you migrate from TrustChain v1 to the simplified v2 API.

## Key Changes

### 1. Simplified Architecture
- **v1**: 15+ classes (SignatureEngine, Signer, Verifier, Registry, etc.)
- **v2**: 3 main classes (TrustChain, SignedResponse, TrustChainConfig)

### 2. No Global State
- **v1**: Global singleton via `get_signature_engine()`
- **v2**: Explicit TrustChain instances

### 3. Configuration-Based
- **v1**: Hardcoded constants scattered throughout
- **v2**: All settings in TrustChainConfig

## Quick Migration

### Old Code (v1)
```python
from trustchain import TrustedTool, SignatureEngine, MemoryRegistry, get_signature_engine

# Setup
engine = SignatureEngine(MemoryRegistry())
set_signature_engine(engine)

@TrustedTool(
    "weather_api",
    trust_level=TrustLevel.MEDIUM,
    algorithm=SignatureAlgorithm.ED25519,
    require_nonce=True,
    auto_register=True
)
async def get_weather(city: str):
    return {"temp": 20, "city": city}

# Use
response = await get_weather("Paris")
```

### New Code (v2)
```python
from trustchain.v2 import TrustChain

# Setup
tc = TrustChain()

@tc.tool("weather_api")
def get_weather(city: str):
    return {"temp": 20, "city": city}

# Use
response = get_weather("Paris")
```

## Detailed Migration Steps

### Step 1: Replace Imports

```python
# Old
from trustchain import (
    TrustedTool, SignatureEngine, MemoryRegistry,
    get_signature_engine, TrustLevel, SignatureAlgorithm
)

# New
from trustchain.v2 import TrustChain, TrustChainConfig
```

### Step 2: Create TrustChain Instance

```python
# Old
engine = SignatureEngine(MemoryRegistry())
set_signature_engine(engine)

# New
tc = TrustChain()

# Or with custom config
tc = TrustChain(TrustChainConfig(
    enable_nonce=True,
    cache_ttl=600,
))
```

### Step 3: Update Tool Decorators

```python
# Old
@TrustedTool(
    "my_tool",
    trust_level=TrustLevel.HIGH,
    require_nonce=True
)
async def my_tool(data: str):
    return process(data)

# New
@tc.tool("my_tool")
def my_tool(data: str):
    return process(data)
```

### Step 4: Update Verification Code

```python
# Old
engine = get_signature_engine()
result = engine.verify_response(response)
if result.valid:
    print("Verified!")

# New
if tc.verify(response):
    print("Verified!")
```

## Using Compatibility Layer

For gradual migration, use the compatibility layer:

```python
# Add this import to use old API with deprecation warnings
from trustchain.compat import TrustedTool, get_signature_engine

# Your old code continues to work
@TrustedTool("old_tool")
def old_tool():
    return "still works"
```

## Feature Mapping

| v1 Feature | v2 Equivalent |
|------------|---------------|
| `TrustedTool` decorator | `@tc.tool()` |
| `SignatureEngine` | `TrustChain` |
| `MemoryRegistry` | Built-in storage |
| `get_signature_engine()` | Create `TrustChain()` |
| `TrustLevel` enum | Removed (simplified) |
| `SignatureAlgorithm` enum | String in config |
| `NonceManager` | Built into TrustChain |
| `ChainLink/ChainMetadata` | Removed (unused) |
| `MultiSignatureTool` | Removed (overcomplex) |

## Configuration Migration

### v1 (Hardcoded)
```python
# Scattered throughout code
cache_ttl = 3600  # in signatures.py
max_recent_responses = 50  # in hallucination_detector.py
```

### v2 (Centralized)
```python
config = TrustChainConfig(
    cache_ttl=3600,
    max_cached_responses=50,
    enable_nonce=True,
    tool_claim_patterns=[...]  # All patterns in config
)
tc = TrustChain(config)
```

## Async/Sync Handling

### v1 (Complex)
```python
# Had to use run_in_executor for sync functions
@TrustedTool("sync_tool")
def sync_tool():  # Complex wrapper needed
    return "data"
```

### v2 (Simple)
```python
# Automatic detection
@tc.tool("sync_tool")
def sync_tool():  # Just works
    return "data"

@tc.tool("async_tool")
async def async_tool():  # Also just works
    return "data"
```

## Common Pitfalls

1. **Global State**: v2 doesn't use global state. Create TrustChain instances explicitly.
2. **Trust Levels**: v2 simplifies this - all tools are equally trusted.
3. **Multi-Signature**: Not supported in v2 (rarely used, added complexity).
4. **Chain Features**: ChainLink/ChainMetadata removed - use your own if needed.

## Performance Improvements

v2 is faster due to:
- Fewer abstraction layers
- `collections.deque` instead of lists
- Built-in LRU cache
- Simplified verification path

## Testing

Update your tests:

```python
# Old
def test_old():
    engine = SignatureEngine()
    # ... complex setup ...

# New  
def test_new():
    tc = TrustChain()
    
    @tc.tool("test_tool")
    def my_tool(x):
        return x * 2
    
    response = my_tool(5)
    assert response.data == 10
    assert response.is_verified
```

## Need Help?

- Check `trustchain/v2/example.py` for usage examples
- Use compatibility layer for gradual migration
- File issues for missing features you need 