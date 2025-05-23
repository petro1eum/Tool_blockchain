# 🧪 External Test Project - TrustChain

> **Независимый проект для тестирования TrustChain как внешней библиотеки**

**Автор:** Ed Cherednik ([edcherednik@gmail.com](mailto:edcherednik@gmail.com) | [@EdCher](https://t.me/EdCher))

---

## 🎯 Цель проекта

Этот проект демонстрирует использование **TrustChain как внешней библиотеки** в реальном проекте. Здесь мы импортируем TrustChain и используем её для защиты бизнес-логики.

---

## 📁 Структура проекта

```
external_test/
├── README_EXTERNAL_TEST.md     # Этот файл
├── requirements.txt            # Зависимости проекта
├── quick_test.py              # Быстрый тест импорта
├── business_logic.py          # Бизнес-функции с TrustChain
├── main.py                    # Основной демо-файл
├── test_integration.py        # Pytest тесты
└── setup_external_env.sh      # Скрипт настройки окружения
```

---

## 🚀 Быстрый старт

### Способ 1: Автоматическая настройка

```bash
# Из папки external_test
chmod +x setup_external_env.sh
./setup_external_env.sh
```

### Способ 2: Ручная настройка

```bash
# 1. Установите TrustChain (из корневой папки Tool_blockchain)
cd ../
pip install -e .

# 2. Вернитесь в external_test
cd external_test

# 3. Запустите быстрый тест
python quick_test.py

# 4. Запустите полный демо
python main.py

# 5. Запустите pytest тесты
python test_integration.py
```

---

## ✅ Критерии успешного теста

Если видите такой вывод - **TrustChain работает отлично**:

```
🧪 Quick TrustChain External Test
================================
✅ TrustChain import: SUCCESS
✅ @TrustedTool decorator: SUCCESS  
✅ Signature creation: SUCCESS
✅ Signature verification: SUCCESS
✅ Response type: <class 'trustchain.core.models.SignedResponse'>
✅ Tool ID: external_quick_test

🎉 TrustChain external integration: PERFECT!
```

---

## 📊 Что тестируется

1. **📦 Импорт библиотеки** - TrustChain доступна как внешний пакет
2. **🔧 Декораторы** - `@TrustedTool` работает в внешнем проекте  
3. **🔐 Подписи** - Автоматическое создание криптографических подписей
4. **✅ Верификация** - Проверка подлинности ответов
5. **🏗️ Бизнес-логика** - Реальные примеры использования
6. **🧪 Тестирование** - Pytest интеграция

---

## 💼 Примеры бизнес-применения

### Финансовые операции
```python
@TrustedTool("payment_system", trust_level=TrustLevel.CRITICAL)
async def transfer_money(amount: float, from_acc: str, to_acc: str):
    # Ваша логика перевода денег
    # Результат будет автоматически подписан!
```

### Пользовательские данные
```python
@TrustedTool("user_service", trust_level=TrustLevel.HIGH)
async def get_user_profile(user_id: str):
    # Получение данных пользователя
    # Гарантированная подлинность ответа!
```

### API интеграции
```python
@TrustedTool("external_api", trust_level=TrustLevel.MEDIUM)
async def fetch_market_data(symbol: str):
    # Запрос к внешнему API
    # Криптографическое подтверждение данных!
```

---

## 🎯 Заключение

Этот проект доказывает, что **TrustChain готова к production использованию**:

- ✅ Работает как независимая библиотека
- ✅ Легко интегрируется в существующие проекты  
- ✅ Не требует изменения архитектуры
- ✅ Автоматически защищает все функции
- ✅ Обеспечивает криптографическую безопасность

**🚀 Готово к использованию в реальных проектах!**

---

<div align="center">

**Made with ❤️ by Ed Cherednik**

📧 [edcherednik@gmail.com](mailto:edcherednik@gmail.com) | 💬 [@EdCher](https://t.me/EdCher)

</div> 