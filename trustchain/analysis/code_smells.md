# Code Smells в TrustChain

## 1. Хардкод и магические константы

### signatures.py (строки 166-184)
```python
# Look for the tool in the signature engine's registry to get its trust level
if hasattr(self._signature_engine, 'trust_registry') and self._signature_engine.trust_registry:
    try:
        # Try to get tool metadata from registry
        tool_metadata = getattr(self._signature_engine.trust_registry, 'get_tool', lambda x: None)(tool_id)
        if tool_metadata and hasattr(tool_metadata, 'trust_level'):
            tool_trust_level = tool_metadata.trust_level
    except:
        pass

# Fallback: check if tool trust level is in the data itself
if 'trust_level' in data:
    try:
        tool_trust_level = TrustLevel(data['trust_level'])
    except:
        pass
```
**Проблемы**: 
- Использование hasattr/getattr вместо нормального интерфейса
- Молчаливое проглатывание исключений
- Хардкод логики получения trust_level

### hallucination_detector.py (строки 55-65)
```python
tool_claim_patterns = [
    r'I\s+(?:called|used|executed|ran|invoked)',
    r'I\s+(?:got|obtained|received|fetched)',
    r'API\s+(?:returned|responded|gave)',
    r'tool\s+(?:returned|gave|showed)',
    r'transaction\s+(?:id|number)',
    r'result\s+(?:is|was|shows)',
]
```
**Проблема**: Хардкод паттернов, должно быть в конфигурации

## 2. Глобальное состояние

### signatures.py (строки 693-707)
```python
_global_signature_engine: Optional[SignatureEngine] = None

def get_signature_engine() -> SignatureEngine:
    """Get the global signature engine instance."""
    global _global_signature_engine
    if _global_signature_engine is None:
        _global_signature_engine = SignatureEngine()
    return _global_signature_engine

def set_signature_engine(engine: SignatureEngine) -> None:
    """Set the global signature engine instance."""
    global _global_signature_engine
    _global_signature_engine = engine
```
**Проблема**: Глобальный синглтон затрудняет тестирование и создает скрытые зависимости

## 3. Нарушение DRY (Don't Repeat Yourself)

### models.py - повторяющиеся валидаторы
```python
@field_validator("signature", "signed_hash")
@classmethod
def validate_non_empty(cls, v: Any) -> str:
    """Ensure critical fields are non-empty."""
    if not v or not isinstance(v, str):
        raise ValueError("Field must be a non-empty string")
    return v

# Похожий код повторяется в других местах:
@field_validator("request_id", "nonce")
@classmethod
def validate_ids(cls, v: Any) -> str:
    """Ensure IDs are non-empty strings."""
    if not v or not isinstance(v, str):
        raise ValueError("ID must be a non-empty string")
    return v
```

## 4. Смешивание ответственностей

### decorators.py (строки 50-90)
```python
def decorator(func: Callable) -> Callable:
    # Создание инструмента
    if multi_sig:
        # 40+ строк кода для создания MultiSigFunctionTool
        ...
    else:
        tool = FunctionTrustedTool(...)

    # Регистрация
    if register_globally:
        register_tool(tool)

    # Создание wrapper
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Обработка параметров
        # Вызов инструмента
        # Возврат результата
        ...

    # Присоединение метаданных
    wrapper._trustchain_tool = tool
    wrapper.tool_id = tool_id
    wrapper.get_statistics = tool.get_statistics
    wrapper.reset_statistics = tool.reset_statistics

    return wrapper
```
**Проблема**: Декоратор делает слишком много - создание, регистрация, обертка, статистика

## 5. Избыточная сложность

### crypto.py - создание ключей
```python
def create_key_pair(self, algorithm: SignatureAlgorithm, **kwargs) -> KeyPair:
    """Create a new key pair for the specified algorithm."""
    if algorithm == SignatureAlgorithm.ED25519:
        return Ed25519KeyPair.generate(**kwargs)
    elif algorithm == SignatureAlgorithm.RSA_PSS:
        return RSAKeyPair.generate(**kwargs)
    elif algorithm == SignatureAlgorithm.ECDSA:
        return ECDSAKeyPair.generate(**kwargs)
    elif algorithm == SignatureAlgorithm.DILITHIUM:
        raise NotImplementedError("Post-quantum signatures not yet implemented")
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
```
**Проблема**: Можно заменить на словарь фабрик

## 6. Плохая обработка ошибок

### signatures.py (строки 240-250)
```python
except Exception as e:
    result = VerificationResult.failure(
        request_id=request_id,
        tool_id=tool_id,
        signature_id=signature.public_key_id,
        verifier_id=self.verifier_id,
        error_code="VERIFICATION_ERROR",
        error_message=f"Verification error: {str(e)}",
        algorithm=signature.algorithm,
    )
    self._cache_result(cache_key, result)
    return result
```
**Проблема**: Ловим все Exception, теряем stack trace

## 7. Неэффективное использование памяти

### hallucination_detector.py (строки 130-135)
```python
def register_signed_response(self, signed_response: SignedResponse) -> None:
    """Register a signed response from a direct tool call."""
    self.recent_signed_responses.insert(0, signed_response)
    # Keep only recent responses
    if len(self.recent_signed_responses) > self.max_recent_responses:
        self.recent_signed_responses = self.recent_signed_responses[:self.max_recent_responses]
```
**Проблема**: Создаем новый список при каждом усечении, лучше использовать collections.deque

## 8. Костыли для async/sync совместимости

### decorators.py (строки 96-101)
```python
async def execute(self, *args, **kwargs) -> Any:
    """Execute the wrapped function with multi-signature."""
    import asyncio

    if asyncio.iscoroutinefunction(self.func):
        return await self.func(*args, **kwargs)
    else:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.func(*args, **kwargs)
        )
```
**Проблема**: run_in_executor для синхронных функций - overhead и потенциальные проблемы с thread safety

## Рекомендации

1. **Вынести конфигурацию**: Все магические константы и паттерны в отдельный config класс
2. **Dependency Injection**: Вместо глобальных синглтонов
3. **Интерфейсы вместо hasattr**: Определить четкие контракты
4. **Специфичные исключения**: Вместо общих Exception
5. **Разделение ответственностей**: Один класс - одна задача
6. **Эффективные структуры данных**: deque, LRU cache
7. **Четкое разделение sync/async**: Отдельные API или clear adapters 