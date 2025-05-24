# Предложение по рефакторингу TrustChain

## Упрощенная архитектура

### Текущая архитектура (сложная)
```
SignatureEngine
├── Signer (ABC)
│   ├── KeyPairSigner
│   └── MultiSigner
├── Verifier (ABC)
│   ├── InMemoryVerifier
│   └── TrustRegistryVerifier
├── TrustRegistry (ABC)
│   ├── MemoryRegistry
│   ├── RedisRegistry
│   └── KafkaRegistry
├── CryptoEngine
│   └── KeyPair (ABC)
│       ├── Ed25519KeyPair
│       ├── RSAKeyPair
│       └── ECDSAKeyPair
└── NonceManager
```

### Предлагаемая архитектура (простая)
```
TrustChain
├── Signer (конкретный класс)
├── Storage (простой интерфейс)
│   ├── MemoryStorage
│   └── RedisStorage (опционально)
└── Config
```

## Новый API

### 1. Основной класс
```python
from dataclasses import dataclass
from typing import Any, Dict, Optional
import time
import hashlib
import base64

@dataclass
class TrustChainConfig:
    """Конфигурация TrustChain"""
    algorithm: str = "ed25519"
    cache_ttl: int = 3600
    max_cached_responses: int = 100
    enable_nonce: bool = True
    
class TrustChain:
    """Простой API для подписи ответов инструментов"""
    
    def __init__(self, config: Optional[TrustChainConfig] = None):
        self.config = config or TrustChainConfig()
        self._signer = Signer(self.config.algorithm)
        self._storage = MemoryStorage(self.config.max_cached_responses)
        self._tools = {}
    
    def tool(self, tool_id: str, **options):
        """Декоратор для создания подписанного инструмента"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Выполнить функцию
                result = func(*args, **kwargs)
                
                # Подписать результат
                signed = self._sign_response(tool_id, result)
                
                # Сохранить для верификации
                self._storage.store(signed.signature_id, signed)
                
                return signed
            
            # Сохранить инструмент
            self._tools[tool_id] = {
                'func': wrapper,
                'options': options
            }
            
            return wrapper
        return decorator
    
    def verify(self, signed_response: SignedResponse) -> bool:
        """Проверить подпись ответа"""
        return self._signer.verify(signed_response)
```

### 2. Простой Signer
```python
class Signer:
    """Простой класс для подписи и верификации"""
    
    def __init__(self, algorithm: str = "ed25519"):
        self.algorithm = algorithm
        self._key = self._generate_key()
    
    def sign(self, data: Dict[str, Any]) -> str:
        """Подписать данные"""
        # Сериализовать данные
        json_data = json.dumps(data, sort_keys=True)
        
        # Создать хеш
        hash_obj = hashlib.sha256(json_data.encode()).digest()
        
        # Подписать (упрощенная версия для примера)
        signature = self._key.sign(hash_obj)
        
        return base64.b64encode(signature).decode()
    
    def verify(self, data: Dict[str, Any], signature: str) -> bool:
        """Проверить подпись"""
        # Воссоздать хеш
        json_data = json.dumps(data, sort_keys=True)
        hash_obj = hashlib.sha256(json_data.encode()).digest()
        
        # Проверить подпись
        signature_bytes = base64.b64decode(signature)
        return self._key.verify(hash_obj, signature_bytes)
```

### 3. Простое хранилище
```python
from collections import OrderedDict

class MemoryStorage:
    """Простое хранилище в памяти с LRU"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._data = OrderedDict()
    
    def store(self, key: str, value: Any) -> None:
        """Сохранить значение"""
        # LRU: удалить старое если превышен лимит
        if len(self._data) >= self.max_size:
            self._data.popitem(last=False)
        
        self._data[key] = value
        self._data.move_to_end(key)
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение"""
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None
```

### 4. Простой SignedResponse
```python
@dataclass
class SignedResponse:
    """Подписанный ответ инструмента"""
    tool_id: str
    data: Any
    signature: str
    signature_id: str
    timestamp: float = field(default_factory=time.time)
    
    @property
    def is_verified(self) -> bool:
        """Проверен ли ответ (кешируется)"""
        if not hasattr(self, '_verified'):
            # Получить TrustChain instance и проверить
            # (в реальной реализации через контекст)
            self._verified = True  # упрощение
        return self._verified
```

## Пример использования

### Старый способ (сложный)
```python
from trustchain import (
    TrustedTool, SignatureEngine, MemoryRegistry,
    get_signature_engine, TrustLevel, SignatureAlgorithm
)

# Настройка
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
```

### Новый способ (простой)
```python
from trustchain import TrustChain

tc = TrustChain()

@tc.tool("weather_api")
def get_weather(city: str):
    return {"temp": 20, "city": city}

# Использование
result = get_weather("Moscow")
assert result.is_verified  # автоматически
```

## Преимущества нового подхода

1. **Простота**: 3 класса вместо 15+
2. **Ясность**: Понятно что делает каждый компонент
3. **Тестируемость**: Нет глобального состояния
4. **Производительность**: Меньше слоев абстракции
5. **Гибкость**: Легко расширять через конфигурацию

## План миграции

### Фаза 1: Создать новое ядро
- Реализовать TrustChain, Signer, Storage
- Покрыть тестами основные сценарии
- Документация с примерами

### Фаза 2: Адаптеры для совместимости
- Wrapper для старого API поверх нового
- Миграционный гайд
- Deprecation warnings

### Фаза 3: Дополнительные фичи
- Hallucination detection как отдельный модуль
- Redis/Kafka storage как плагины
- Интеграции (LangChain, OpenAI) как отдельные пакеты

## Метрики успеха

- Размер кодовой базы: -70%
- Время выполнения тестов: -50%
- Покрытие тестами: 95%+
- Производительность: +30%
- Простота использования: 5 минут до первого результата 