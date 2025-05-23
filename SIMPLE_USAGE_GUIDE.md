# 🔧 Простой гайд: Как использовать TrustChain

> **Защитите ваши AI tools от галлюцинаций за 5 минут**

**Автор:** Ed Cherednik ([edcherednik@gmail.com](mailto:edcherednik@gmail.com) | [@EdCher](https://t.me/EdCher))

---

## 🎯 Проблема

Ваши AI инструменты могут "галлюцинировать" - выдумывать данные:
- 💰 Поддельные банковские переводы
- 📧 Фейковые email отправки  
- 🔍 Ложные результаты поиска
- 🛒 Несуществующие заказы

**❌ БЕЗ TrustChain:** Невозможно отличить правду от галлюцинации

**✅ С TrustChain:** Каждый реальный ответ подписан криптографически

---

## 🚀 Решение: Добавьте один декоратор

### До (обычный код):
```python
def transfer_money(amount, from_account, to_account):
    # Ваша логика
    return {"status": "completed", "amount": amount}
```

### После (защищено TrustChain):
```python
from trustchain import TrustedTool, TrustLevel

@TrustedTool("payment_api", trust_level=TrustLevel.CRITICAL)
def transfer_money(amount, from_account, to_account):
    # ТА ЖЕ логика - ничего не меняется!
    return {"status": "completed", "amount": amount}
```

**Результат:** Ответ автоматически подписан и защищен!

---

## 📋 Установка

```bash
pip install -e /path/to/Tool_blockchain
# или
pip install git+https://github.com/petro1eum/Tool_blockchain.git
```

---

## 🤖 OpenAI + TrustChain

### 1. Обычный OpenAI код (БЕЗ защиты):

```python
import openai
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

# Небезопасная функция - может быть подделана
def get_weather(location: str) -> str:
    # Реальный API запрос
    return f"Weather in {location}: 22°C, sunny"

def send_email(to: str, subject: str, body: str) -> str:
    # Реальная отправка email
    return f"Email sent to {to}"

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather information",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }
    },
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
    messages=[{"role": "user", "content": "Send weather report to john@example.com"}],
    tools=tools
)
```

### 2. Защищенный код (С TrustChain):

```python
import openai
from openai import OpenAI
from trustchain import TrustedTool, TrustLevel

client = OpenAI(api_key="your-api-key")

# ✅ ЗАЩИЩЕННЫЕ функции
@TrustedTool("weather_service", trust_level=TrustLevel.MEDIUM)
def get_weather(location: str) -> str:
    # ТА ЖЕ логика!
    return f"Weather in {location}: 22°C, sunny"

@TrustedTool("email_service", trust_level=TrustLevel.HIGH) 
def send_email(to: str, subject: str, body: str) -> str:
    # ТА ЖЕ логика!
    return f"Email sent to {to}"

# Те же tools - никаких изменений!
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather information", 
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }
    },
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

# Тот же вызов API!
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Send weather report to john@example.com"}],
    tools=tools
)

# ✅ НОВОЕ: Проверка подлинности ответов
for tool_call in response.choices[0].message.tool_calls or []:
    if tool_call.function.name == "get_weather":
        result = get_weather(**eval(tool_call.function.arguments))
        if result.is_verified:
            print("✅ Weather data is AUTHENTIC")
        else:
            print("❌ FAKE weather data detected!")
    
    elif tool_call.function.name == "send_email":
        result = send_email(**eval(tool_call.function.arguments))
        if result.is_verified:
            print("✅ Email REALLY sent")
        else:
            print("❌ FAKE email send detected!")
```

---

## 🧠 Anthropic + TrustChain

### 1. Обычный Anthropic код (БЕЗ защиты):

```python
import anthropic

client = anthropic.Anthropic(api_key="your-api-key")

# Небезопасные функции
def check_balance(account_id: str) -> str:
    # Реальная проверка баланса
    return f"Account {account_id}: $5,000"

def make_payment(amount: float, to_account: str) -> str:
    # Реальный перевод денег
    return f"Paid ${amount} to {to_account}"

tools = [
    {
        "name": "check_balance",
        "description": "Check account balance",
        "input_schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"}
            }
        }
    },
    {
        "name": "make_payment", 
        "description": "Make payment",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "to_account": {"type": "string"}
            }
        }
    }
]

response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Check my balance and pay $100 to acc_456"}],
    tools=tools
)
```

### 2. Защищенный код (С TrustChain):

```python
import anthropic
from trustchain import TrustedTool, TrustLevel

client = anthropic.Anthropic(api_key="your-api-key")

# ✅ ЗАЩИЩЕННЫЕ функции
@TrustedTool("banking_api", trust_level=TrustLevel.HIGH)
def check_balance(account_id: str) -> str:
    # ТА ЖЕ логика!
    return f"Account {account_id}: $5,000"

@TrustedTool("payment_api", trust_level=TrustLevel.CRITICAL)
def make_payment(amount: float, to_account: str) -> str:
    # ТА ЖЕ логика!
    return f"Paid ${amount} to {to_account}"

# Те же tools!
tools = [
    {
        "name": "check_balance",
        "description": "Check account balance",
        "input_schema": {
            "type": "object", 
            "properties": {
                "account_id": {"type": "string"}
            }
        }
    },
    {
        "name": "make_payment",
        "description": "Make payment", 
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "to_account": {"type": "string"}
            }
        }
    }
]

# Тот же вызов API!
response = client.messages.create(
    model="claude-3-sonnet-20240229",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Check my balance and pay $100 to acc_456"}],
    tools=tools
)

# ✅ НОВОЕ: Проверка подлинности ответов
for content in response.content:
    if content.type == "tool_use":
        if content.name == "check_balance":
            result = check_balance(**content.input)
            if result.is_verified:
                print("✅ Balance data is AUTHENTIC") 
            else:
                print("❌ FAKE balance detected!")
        
        elif content.name == "make_payment":
            result = make_payment(**content.input)
            if result.is_verified:
                print("✅ Payment REALLY made")
            else:
                print("❌ FAKE payment detected!")
```

---

## 🔍 Что вы получаете

### ❌ БЕЗ TrustChain:
```python
# AI может соврать и вы не узнаете!
result = "Email sent to john@example.com"  # Правда или ложь? 🤷‍♂️
```

### ✅ С TrustChain:
```python
# Каждый ответ проверяемый!
result = send_email("john@example.com", "Hi", "Hello!")

if result.is_verified:
    print("✅ Email ДЕЙСТВИТЕЛЬНО отправлен")
    print(f"🔐 Подпись: {result.signature.signature[:20]}...")
else:
    print("❌ ПОДДЕЛКА! Email НЕ отправлен!")
```

---

## 🎯 Уровни доверия

Выберите нужный уровень безопасности:

```python
# Низкий - для некритичных операций
@TrustedTool("weather_api", trust_level=TrustLevel.LOW)
def get_weather(location): ...

# Средний - для обычных операций  
@TrustedTool("search_api", trust_level=TrustLevel.MEDIUM)
def search_web(query): ...

# Высокий - для важных данных
@TrustedTool("user_data", trust_level=TrustLevel.HIGH) 
def get_user_profile(user_id): ...

# Критический - для финансов, безопасности
@TrustedTool("payment_api", trust_level=TrustLevel.CRITICAL)
def transfer_money(amount, to_account): ...
```

---

## 📋 Простой чек-лист

### ✅ Что нужно сделать:

1. **Установить TrustChain**
   ```bash
   pip install git+https://github.com/petro1eum/Tool_blockchain.git
   ```

2. **Добавить импорт**
   ```python
   from trustchain import TrustedTool, TrustLevel
   ```

3. **Добавить декоратор к функциям**
   ```python
   @TrustedTool("my_api", trust_level=TrustLevel.HIGH)
   def my_function(param):
       # Ваш существующий код
       return result
   ```

4. **Проверять ответы**
   ```python
   result = my_function("test")
   if result.is_verified:
       print("✅ Подлинный ответ")
   else:
       print("❌ Подделка!")
   ```

### ❌ Что НЕ нужно менять:
- ✅ Логику функций
- ✅ OpenAI/Anthropic API вызовы
- ✅ Структуру tools
- ✅ Архитектуру приложения

---

## 🚨 Примеры обнаружения подделок

### Сценарий 1: AI галлюцинирует отправку email
```python
# AI говорит что отправил email, но это ложь
fake_response = {"status": "sent", "to": "user@example.com"}  # Нет подписи!

# TrustChain мгновенно обнаруживает подделку
if hasattr(fake_response, 'signature'):
    print("✅ Настоящий ответ")
else:
    print("❌ ГАЛЛЮЦИНАЦИЯ ОБНАРУЖЕНА!")  # Это выведется
```

### Сценарий 2: Подделка финансовых данных
```python
# AI выдумывает баланс
fake_balance = {"account": "acc_123", "balance": 999999.99}  # Нет подписи!

# Реальная функция всегда подписана
real_balance = check_balance("acc_123")
print(f"Подлинность: {real_balance.is_verified}")  # True
```

---

## 🎉 Заключение

### До TrustChain:
- ❌ Невозможно отличить правду от галлюцинации
- ❌ AI может обманывать незаметно
- ❌ Риск финансовых потерь
- ❌ Ненадежные системы

### После TrustChain:
- ✅ **Каждый ответ проверяемый**
- ✅ **Галлюцинации обнаруживаются мгновенно**
- ✅ **Финансовая безопасность**
- ✅ **Надежные AI системы**

**🚀 Добавьте один декоратор - получите полную защиту!**

---

## 🔗 Дополнительные ресурсы

- **Полная документация:** [README.md](README.md)
- **Примеры использования:** [examples/](examples/)
- **Тестирование:** [external_test/](external_test/)
- **Детекция галлюцинаций:** [examples/hallucination_detection_demo.py](examples/hallucination_detection_demo.py)

---

<div align="center">

## 🎯 Начните прямо сейчас!

**Защитите ваши AI tools за 5 минут**

**Made with ❤️ by Ed Cherednik**

📧 [edcherednik@gmail.com](mailto:edcherednik@gmail.com) | 💬 [@EdCher](https://t.me/EdCher)

</div> 