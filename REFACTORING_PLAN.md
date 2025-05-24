# План рефакторинга TrustChain

## Резюме проблем

Анализ репозитория выявил следующие ключевые проблемы:

1. **Избыточная сложность**: 15+ классов для решения простой задачи (подпись ответов)
2. **Хардкод и магические константы**: Паттерны, TTL, размеры кешей захардкожены
3. **Глобальное состояние**: Синглтон `get_signature_engine()` усложняет тестирование
4. **Смешивание ответственностей**: Классы делают слишком много разных вещей
5. **Проблемы с async/sync**: Костыли для совместимости
6. **Неэффективное использование памяти**: Нет автоочистки, используются списки вместо deque

## Конкретные шаги рефакторинга

### Шаг 1: Создать новое упрощенное ядро (trustchain/v2/)

```bash
trustchain/
├── v2/
│   ├── __init__.py       # Новый простой API
│   ├── core.py           # TrustChain класс
│   ├── signer.py         # Простая подпись/верификация
│   ├── storage.py        # Хранилище с LRU
│   └── config.py         # Конфигурация
```

**Действия:**
1. Реализовать `TrustChain` класс с методом `tool()` декоратором
2. Создать простой `Signer` без лишних абстракций
3. Реализовать `MemoryStorage` на базе `OrderedDict`
4. Вынести все константы в `TrustChainConfig`

### Шаг 2: Убрать неиспользуемый функционал

**Удалить:**
- `ChainLink`, `ChainMetadata` - не используются
- `MultiSignatureTool` - переусложнение
- ABC классы с единственной реализацией
- Поддержку алгоритмов кроме Ed25519 (можно добавить позже)

### Шаг 3: Исправить конкретные code smells

**signatures.py:166-184** - заменить на:
```python
def get_trust_level(self, tool_id: str) -> TrustLevel:
    """Get trust level for tool with proper interface"""
    if self.trust_registry and hasattr(self.trust_registry, 'get_tool_trust_level'):
        return self.trust_registry.get_tool_trust_level(tool_id)
    return TrustLevel.MEDIUM  # default
```

**hallucination_detector.py** - вынести паттерны:
```python
@dataclass
class HallucinationConfig:
    tool_claim_patterns: List[str] = field(default_factory=lambda: [
        r'I\s+(?:called|used|executed|ran|invoked)',
        # ...
    ])
```

**decorators.py:96-101** - разделить sync/async:
```python
def create_wrapper(func, tool):
    if asyncio.iscoroutinefunction(func):
        return create_async_wrapper(func, tool)
    else:
        return create_sync_wrapper(func, tool)
```

### Шаг 4: Улучшить производительность

1. Заменить списки на `collections.deque` для кешей
2. Использовать `functools.lru_cache` где возможно
3. Добавить TTL-based очистку кешей
4. Убрать лишние слои абстракции

### Шаг 5: Создать миграционный слой

```python
# trustchain/compat.py
def TrustedTool(tool_id: str, **kwargs):
    """Compatibility wrapper for old API"""
    warnings.warn(
        "TrustedTool is deprecated, use @trustchain.tool() instead",
        DeprecationWarning
    )
    # Map old API to new
    tc = get_default_trustchain()
    return tc.tool(tool_id, **kwargs)
```

### Шаг 6: Обновить тесты

1. Написать тесты для нового API
2. Убедиться что старые тесты работают через compatibility layer
3. Добавить performance benchmarks
4. Покрытие 95%+

### Шаг 7: Обновить документацию

1. Новый QUICKSTART.md с простыми примерами
2. Migration guide от старого API
3. Обновить README с новыми примерами

## Приоритеты

### Высокий приоритет (неделя 1)
- [ ] Создать v2/core.py с базовым функционалом
- [ ] Исправить глобальный синглтон
- [ ] Вынести хардкод в конфигурацию

### Средний приоритет (неделя 2)
- [ ] Улучшить производительность (deque, lru_cache)
- [ ] Разделить sync/async API
- [ ] Создать compatibility layer

### Низкий приоритет (неделя 3+)
- [ ] Удалить неиспользуемый код
- [ ] Рефакторинг тестов
- [ ] Обновить документацию

## Метрики успеха

- **Размер кода**: с ~3000 строк до ~1000 строк (-70%)
- **Количество классов**: с 15+ до 5-6
- **Время до первого результата**: с 30+ минут до 5 минут
- **Производительность**: +30% за счет меньшего overhead
- **Тестовое покрытие**: 95%+

## Риски

1. **Обратная совместимость**: Решение - compatibility layer
2. **Потеря функционала**: Решение - вынести редкие фичи в extras/
3. **Сопротивление изменениям**: Решение - показать преимущества на примерах

## Заключение

Текущая реализация действительно страдает от "камуфлирования тупости за сложностью". Предлагаемый рефакторинг сделает библиотеку:
- Проще в использовании
- Быстрее в работе
- Легче в поддержке
- Понятнее для новых разработчиков

Основная идея библиотеки хорошая, но реализация нуждается в серьезном упрощении. 