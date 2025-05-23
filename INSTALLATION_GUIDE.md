# 📦 Installation Guide - TrustChain

> **Руководство по установке и использованию TrustChain в ваших проектах**

**Автор:** Ed Cherednik ([edcherednik@gmail.com](mailto:edcherednik@gmail.com) | [@EdCher](https://t.me/EdCher))

---

## 🎯 Цель

Эта инструкция покажет, как **установить TrustChain** и использовать в **отдельном проекте** для проверки работоспособности.

---

## 🚀 Способы установки

### Метод 1: Editable Install (Рекомендуется для разработки)

```bash
# Из корневой папки Tool_blockchain
pip install -e .

# Проверка установки
python -c "import trustchain; print(f'TrustChain v{trustchain.__version__} installed!')"
```

**Преимущества:**
- ✅ Изменения в коде сразу доступны
- ✅ Удобно для разработки
- ✅ Можно править библиотеку и тестировать

### Метод 2: Обычная установка

```bash
# Из корневой папки Tool_blockchain
pip install .

# Проверка установки
python -c "import trustchain; print('TrustChain installed successfully!')"
```

**Преимущества:**
- ✅ Стандартная установка пакета
- ✅ Библиотека установлена в site-packages
- ✅ Не зависит от исходного кода

### Метод 3: Прямая установка из GitHub

```bash
# Прямая установка из репозитория
pip install git+https://github.com/petro1eum/Tool_blockchain.git

# Проверка
python -c "import trustchain; print('Installed from GitHub!')"
```

---

## 🧪 Быстрая проверка работоспособности

### Тест 1: Базовый импорт

```bash
python -c "
from trustchain import TrustedTool, TrustLevel
print('✅ Basic import successful!')
"
```

### Тест 2: Создание доверенного инструмента

```bash
python -c "
import asyncio
from trustchain import TrustedTool

@TrustedTool('test_tool')
async def test_func():
    return {'status': 'working'}

async def main():
    result = await test_func()
    print(f'✅ Tool works: {result.is_verified}')

asyncio.run(main())
"
```

---

## 📁 Создание внешнего тестового проекта

### Шаг 1: Создайте отдельную папку

```bash
# Создайте папку ВНЕ директории Tool_blockchain
mkdir ~/my_trustchain_test
cd ~/my_trustchain_test
```

### Шаг 2: Создайте виртуальное окружение

```bash
# Создание нового окружения
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# Установка TrustChain
pip install -e ~/path/to/Tool_blockchain
```

### Шаг 3: Создайте тестовый файл

```python
# test_external.py
import asyncio
from trustchain import TrustedTool, TrustLevel

@TrustedTool("external_test", trust_level=TrustLevel.HIGH)
async def my_business_function(data: str) -> dict:
    """Моя бизнес-функция с криптографической защитой."""
    return {
        "processed_data": data.upper(),
        "length": len(data),
        "business_logic": "completed"
    }

async def main():
    print("🧪 Testing TrustChain in external project...")
    
    # Используем наш доверенный инструмент
    result = await my_business_function("hello world")
    
    print(f"✅ Response type: {type(result)}")
    print(f"✅ Data: {result.data}")
    print(f"✅ Has signature: {hasattr(result, 'signature')}")
    print(f"✅ Is verified: {result.is_verified}")
    print(f"✅ Tool ID: {result.tool_id}")
    
    print("\n🎉 TrustChain works perfectly in external project!")

if __name__ == "__main__":
    asyncio.run(main())
```

### Шаг 4: Запустите тест

```bash
python test_external.py
```

---

## 🔍 Расширенная проверка

### Создайте полноценный тестовый проект:

```
my_trustchain_test/
├── requirements.txt
├── main.py
├── business_logic.py
└── test_integration.py
```

**requirements.txt:**
```
# Если установили TrustChain локально, этот файл может быть пустым
# Или добавьте другие зависимости вашего проекта
requests>=2.28.0
pytest>=7.0.0
```

**business_logic.py:**
```python
from trustchain import TrustedTool, TrustLevel
from typing import Dict, Any

@TrustedTool("payment_processor", trust_level=TrustLevel.CRITICAL)
async def process_payment(amount: float, from_account: str, to_account: str) -> Dict[str, Any]:
    """Обработка платежа с криптографической подписью."""
    # Ваша бизнес-логика
    fee = amount * 0.01  # 1% комиссия
    
    return {
        "transaction_id": f"tx_{hash(f'{from_account}{to_account}{amount}') % 10000}",
        "amount": amount,
        "fee": fee,
        "from_account": from_account,
        "to_account": to_account,
        "status": "completed",
        "verified": True
    }

@TrustedTool("user_service", trust_level=TrustLevel.MEDIUM)
async def get_user_info(user_id: str) -> Dict[str, Any]:
    """Получение информации о пользователе."""
    return {
        "user_id": user_id,
        "name": f"User {user_id}",
        "balance": 1000.0,
        "status": "active"
    }
```

**main.py:**
```python
import asyncio
from business_logic import process_payment, get_user_info

async def main():
    print("🏦 TrustChain Business Logic Test")
    print("=" * 40)
    
    # Тест 1: Получение информации о пользователе
    print("\n📊 Getting user info...")
    user_info = await get_user_info("user_123")
    print(f"✅ User: {user_info.data['name']}")
    print(f"✅ Signed: {user_info.is_verified}")
    
    # Тест 2: Обработка платежа
    print("\n💳 Processing payment...")
    payment_result = await process_payment(100.0, "acc_001", "acc_002")
    print(f"✅ Transaction ID: {payment_result.data['transaction_id']}")
    print(f"✅ Amount: ${payment_result.data['amount']}")
    print(f"✅ Fee: ${payment_result.data['fee']}")
    print(f"✅ Signed: {payment_result.is_verified}")
    
    # Проверка подписей
    print(f"\n🔐 Cryptographic verification:")
    print(f"   User info signature: {user_info.signature.signature[:20]}...")
    print(f"   Payment signature: {payment_result.signature.signature[:20]}...")
    
    print("\n🎉 All business operations are cryptographically secured!")

if __name__ == "__main__":
    asyncio.run(main())
```

**test_integration.py:**
```python
import pytest
import asyncio
from business_logic import process_payment, get_user_info
from trustchain.core.models import SignedResponse

@pytest.mark.asyncio
async def test_user_service():
    """Тест сервиса пользователей."""
    result = await get_user_info("test_user")
    
    assert isinstance(result, SignedResponse)
    assert result.is_verified
    assert result.data["user_id"] == "test_user"
    assert result.tool_id == "user_service"

@pytest.mark.asyncio
async def test_payment_processing():
    """Тест обработки платежей."""
    result = await process_payment(250.0, "sender", "receiver")
    
    assert isinstance(result, SignedResponse)
    assert result.is_verified
    assert result.data["amount"] == 250.0
    assert result.data["fee"] == 2.5  # 1% от 250
    assert result.tool_id == "payment_processor"

def test_signature_authenticity():
    """Тест подлинности подписей."""
    async def run_test():
        payment = await process_payment(100.0, "a", "b")
        user = await get_user_info("u1")
        
        # Оба ответа должны быть подписаны
        assert hasattr(payment, 'signature')
        assert hasattr(user, 'signature')
        
        # Подписи должны быть разными
        assert payment.signature.signature != user.signature.signature
        
        return True
    
    result = asyncio.run(run_test())
    assert result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

---

## 🚀 Запуск внешнего проекта

```bash
# Переход в тестовую папку
cd ~/my_trustchain_test

# Активация окружения
source test_env/bin/activate

# Запуск основного теста
python main.py

# Запуск pytest тестов
python test_integration.py
```

**Ожидаемый результат:**
```
🏦 TrustChain Business Logic Test
========================================

📊 Getting user info...
✅ User: User user_123
✅ Signed: True

💳 Processing payment...
✅ Transaction ID: tx_1234
✅ Amount: $100.0
✅ Fee: $1.0
✅ Signed: True

🔐 Cryptographic verification:
   User info signature: A1B2C3D4E5F6G7H8I9J0...
   Payment signature: X9Y8Z7W6V5U4T3S2R1Q0...

🎉 All business operations are cryptographically secured!
```

---

## ✅ Критерии успешной установки

Ваша установка работает правильно, если:

1. ✅ **Импорт успешен**: `import trustchain` работает
2. ✅ **Декораторы работают**: `@TrustedTool` создает подписанные функции
3. ✅ **Подписи создаются**: `result.is_verified == True`
4. ✅ **Типы корректны**: `isinstance(result, SignedResponse)`
5. ✅ **Внешний проект работает**: Тесты из отдельной папки проходят

---

## 🔧 Решение проблем

### Проблема: "ModuleNotFoundError: No module named 'trustchain'"

**Решение:**
```bash
# Проверьте, что установили в правильное окружение
pip list | grep trustchain

# Переустановите если нужно
pip uninstall trustchain
pip install -e ~/path/to/Tool_blockchain
```

### Проблема: "ImportError: cannot import name 'TrustedTool'"

**Решение:**
```bash
# Проверьте версию Python (нужен 3.8+)
python --version

# Переустановите с зависимостями
pip install -e "~/path/to/Tool_blockchain[dev]"
```

### Проблема: Тесты не проходят

**Решение:**
```bash
# Запустите базовые тесты библиотеки
cd ~/path/to/Tool_blockchain
python -m pytest tests/ -v

# Если все ОК, проблема в вашем коде
```

---

## 🎯 Заключение

Теперь у вас есть **полноценный внешний тест** TrustChain:

1. 📦 **Установка как пакет** - библиотека работает независимо
2. 🔍 **Внешний проект** - реальное использование
3. 🧪 **Комплексные тесты** - проверка всех функций
4. ✅ **Готовность к продакшену** - можно использовать в реальных проектах

**🎉 Если все тесты проходят - TrustChain готова к использованию!**

---

<div align="center">

**Made with ❤️ by Ed Cherednik**

📧 [edcherednik@gmail.com](mailto:edcherednik@gmail.com) | 💬 [@EdCher](https://t.me/EdCher)

</div> 