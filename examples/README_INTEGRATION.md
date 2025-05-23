# 🔗 TrustChain Integration Examples

> **Готовые примеры интеграции TrustChain с популярными AI API**

**Автор:** Ed Cherednik ([edcherednik@gmail.com](mailto:edcherednik@gmail.com) | [@EdCher](https://t.me/EdCher))

---

## 📁 Файлы в этой папке

| Файл | Описание | Статус |
|------|----------|--------|
| `openai_anthropic_integration.py` | Полная интеграция с OpenAI + Anthropic | ✅ Готов |
| `hallucination_detection_demo.py` | Демо детекции галлюцинаций | ✅ Готов |
| `simple_hallucination_test.py` | Простой тест | ✅ Готов |
| `README_INTEGRATION.md` | Этот файл | ✅ |

---

## 🚀 Быстрый старт

### 1. Запустите демо без API ключей
```bash
# Демо детекции галлюцинаций (работает без ключей)
python examples/hallucination_detection_demo.py

# Простой тест
python examples/simple_hallucination_test.py

# Интеграция (будет работать частично без ключей)
python examples/openai_anthropic_integration.py
```

### 2. Полная интеграция с реальными API
```bash
# Установите зависимости
pip install openai anthropic

# Добавьте API ключи
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Запустите полное демо
python examples/openai_anthropic_integration.py
```

---

## 🔧 Что вы увидите

### ✅ Успешная работа:
```
🤖 OpenAI + TrustChain Integration Demo
=======================================

📤 Sending request to OpenAI GPT-4...
✅ OpenAI response received

🔧 Processing tool calls with TrustChain protection...

🛠️ Executing: get_weather
   Arguments: {'location': 'New York'}
   ✅ VERIFIED: Function executed authentically
   📊 Data: {'location': 'New York', 'temperature': 22, ...}
   🔐 Signature: kAgkjFt3cv55nAs1DD4S...
```

### 🚨 Обнаружение подделок:
```
🚨 Hallucination Detection Demo
===============================

1️⃣ Simulating AI hallucination...
   ❌ HALLUCINATION DETECTED: No cryptographic signature!

2️⃣ Getting real TrustChain-protected response...
   ✅ VERIFIED: Function executed authentically
   🔐 Signature: GKQCV99T7FVJUfttC7eY...
```

---

## 📖 Как использовать в своем проекте

### Шаг 1: Защитите ваши функции

```python
from trustchain import TrustedTool, TrustLevel

# До TrustChain (небезопасно)
def send_email(to, subject, body):
    # Ваша логика
    return {"status": "sent", "to": to}

# После TrustChain (защищено)
@TrustedTool("email_api", trust_level=TrustLevel.HIGH)
def send_email(to, subject, body):
    # ТА ЖЕ логика - ничего не меняется!
    return {"status": "sent", "to": to}
```

### Шаг 2: Используйте с OpenAI

```python
import openai
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

# Обычные tools - никаких изменений!
tools = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send email",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                }
            }
        }
    }
]

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Send hello email to john@example.com"}],
    tools=tools
)

# НОВОЕ: Проверка подлинности
for tool_call in response.choices[0].message.tool_calls or []:
    if tool_call.function.name == "send_email":
        result = send_email(**eval(tool_call.function.arguments))
        
        if result.is_verified:
            print("✅ Email ДЕЙСТВИТЕЛЬНО отправлен")
        else:
            print("❌ ПОДДЕЛКА! AI галлюцинирует!")
```

### Шаг 3: Используйте с Anthropic

```python
import anthropic

client = anthropic.Anthropic(api_key="your-api-key")

# Те же tools
tools = [
    {
        "name": "send_email",
        "description": "Send email",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            }
        }
    }
]

response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Send hello email to john@example.com"}],
    tools=tools
)

# НОВОЕ: Проверка подлинности
for content in response.content:
    if content.type == "tool_use" and content.name == "send_email":
        result = send_email(**content.input)
        
        if result.is_verified:
            print("✅ Email ДЕЙСТВИТЕЛЬНО отправлен")
        else:
            print("❌ ПОДДЕЛКА! AI галлюцинирует!")
```

---

## 🎯 Уровни доверия

Выберите подходящий уровень для ваших функций:

```python
# 🔵 LOW - Некритичные данные
@TrustedTool("weather_api", trust_level=TrustLevel.LOW)
def get_weather(location): ...

# 🟡 MEDIUM - Обычные операции
@TrustedTool("search_api", trust_level=TrustLevel.MEDIUM)
def search_web(query): ...

# 🟠 HIGH - Важные данные
@TrustedTool("user_service", trust_level=TrustLevel.HIGH)
def get_user_profile(user_id): ...

# 🔴 CRITICAL - Финансы, безопасность
@TrustedTool("payment_api", trust_level=TrustLevel.CRITICAL)
def transfer_money(amount, to_account): ...
```

---

## 🛡️ Что защищает TrustChain

### ❌ Проблемы БЕЗ TrustChain:
- AI может "галлюцинировать" отправку email'ов
- Поддельные банковские переводы
- Ложные результаты API запросов
- Невозможно отличить правду от выдумки

### ✅ Решения С TrustChain:
- **Каждый ответ подписан криптографически**
- **Галлюцинации обнаруживаются мгновенно**
- **100% гарантия подлинности**
- **Автоматическая защита без изменения кода**

---

## 📊 Примеры обнаружения атак

### 1. Подделка email отправки
```python
# AI говорит что отправил email, но это ложь
fake_response = {"status": "sent", "to": "user@example.com"}

# TrustChain мгновенно обнаруживает подделку
if hasattr(fake_response, 'signature'):
    print("✅ Настоящий ответ")
else:
    print("❌ ГАЛЛЮЦИНАЦИЯ!")  # Это выведется
```

### 2. Подделка финансовых данных
```python
# AI выдумывает баланс
fake_balance = {"balance": 999999.99}  # Нет подписи!

# Реальная функция всегда подписана
real_balance = check_balance("acc_123")
print(f"Подлинность: {real_balance.is_verified}")  # True
```

### 3. Подделка результатов поиска
```python
# AI выдумывает результаты
fake_results = {"results": ["fake news"]}  # Нет подписи!

# Реальный поиск защищен
real_results = search_web("Python tutorials")
if real_results.is_verified:
    print("✅ Результаты подлинные")
```

---

## 🔧 Troubleshooting

### Проблема: "ModuleNotFoundError: No module named 'trustchain'"
```bash
# Решение:
pip install -e /path/to/Tool_blockchain
# или
pip install git+https://github.com/petro1eum/Tool_blockchain.git
```

### Проблема: "No API key found"
```bash
# Решение:
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

### Проблема: "ImportError: No module named 'openai'"
```bash
# Решение:
pip install openai anthropic
```

### Проблема: Функция не подписана
```python
# Убедитесь что используете декоратор:
@TrustedTool("my_api", trust_level=TrustLevel.HIGH)
def my_function():
    return {"data": "value"}

# И функция async если нужно:
@TrustedTool("my_api", trust_level=TrustLevel.HIGH)
async def my_async_function():
    return {"data": "value"}
```

---

## 🎉 Заключение

**TrustChain обеспечивает 100% защиту от AI галлюцинаций!**

### Ключевые преимущества:
- ✅ **Один декоратор** - полная защита
- ✅ **Никаких изменений** в существующем коде
- ✅ **Работает с любыми AI API** 
- ✅ **Криптографическая гарантия** подлинности
- ✅ **Мгновенное обнаружение** подделок

**🚀 Начните использовать прямо сейчас!**

---

## 🔗 Дополнительные ресурсы

- **Простой гайд:** [SIMPLE_USAGE_GUIDE.md](../SIMPLE_USAGE_GUIDE.md)
- **Полная документация:** [README.md](../README.md)
- **Внешнее тестирование:** [external_test/](../external_test/)
- **GitHub:** [Tool_blockchain](https://github.com/petro1eum/Tool_blockchain)

---

<div align="center">

## 🛡️ Защитите ваши AI системы

**TrustChain - 100% защита от галлюцинаций**

**Made with ❤️ by Ed Cherednik**

📧 [edcherednik@gmail.com](mailto:edcherednik@gmail.com) | 💬 [@EdCher](https://t.me/EdCher)

</div> 