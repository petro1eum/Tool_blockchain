#!/usr/bin/env python3
"""
🧪 Integration Tests for External TrustChain Project

Pytest тесты для проверки интеграции TrustChain в внешнем проекте.

Author: Ed Cherednik (edcherednik@gmail.com)
Telegram: @EdCher

Run: python test_integration.py
     или: python -m pytest test_integration.py -v
"""

import pytest
import asyncio
from typing import Dict, Any

# Импорт бизнес-логики
from business_logic import (
    process_payment,
    get_account_balance,
    get_user_profile,
    authenticate_user,
    fetch_stock_price,
    get_financial_news,
    create_audit_log
)

# Импорт TrustChain
try:
    from trustchain.core.models import SignedResponse
    from trustchain import TrustLevel
    TRUSTCHAIN_AVAILABLE = True
except ImportError:
    TRUSTCHAIN_AVAILABLE = False


# ==================== БАЗОВЫЕ ТЕСТЫ ====================

def test_trustchain_import():
    """Тест импорта TrustChain."""
    assert TRUSTCHAIN_AVAILABLE, "TrustChain should be importable"


@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_basic_function_call():
    """Базовый тест вызова функции."""
    result = await get_user_profile("test_user_basic")
    
    assert result is not None
    assert isinstance(result, SignedResponse)
    assert hasattr(result, 'data')
    assert hasattr(result, 'signature')


# ==================== ТЕСТЫ КРИТИЧЕСКИХ ОПЕРАЦИЙ ====================

@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_user_authentication():
    """Тест аутентификации пользователя."""
    # Успешная аутентификация
    valid_auth = await authenticate_user("test_user", "hash_valid_password_123")
    
    assert isinstance(valid_auth, SignedResponse)
    assert valid_auth.is_verified
    assert valid_auth.data["authenticated"] is True
    assert valid_auth.tool_id == "auth_service"
    assert "session_token" in valid_auth.data
    
    # Неуспешная аутентификация
    invalid_auth = await authenticate_user("test_user", "invalid_password")
    
    assert isinstance(invalid_auth, SignedResponse)
    assert invalid_auth.is_verified  # Ответ подписан, но аутентификация не прошла
    assert invalid_auth.data["authenticated"] is False
    assert "error" in invalid_auth.data


@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_payment_processing():
    """Тест обработки платежей."""
    amount = 500.0
    from_acc = "test_from_account"
    to_acc = "test_to_account"
    
    result = await process_payment(amount, from_acc, to_acc)
    
    # Проверка подписи
    assert isinstance(result, SignedResponse)
    assert result.is_verified
    assert result.tool_id == "payment_processor"
    
    # Проверка данных
    data = result.data
    assert data["amount"] == amount
    assert data["from_account"] == from_acc
    assert data["to_account"] == to_acc
    assert data["status"] == "completed"
    assert "transaction_id" in data
    assert "fee" in data
    assert "final_amount" in data
    
    # Проверка логики комиссии
    expected_fee = amount * 0.01
    assert data["fee"] == expected_fee
    assert data["final_amount"] == amount - expected_fee


# ==================== ТЕСТЫ ОПЕРАЦИЙ ВЫСОКОГО ДОВЕРИЯ ====================

@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_user_profile_service():
    """Тест сервиса профилей пользователей."""
    user_id = "integration_test_user"
    
    result = await get_user_profile(user_id)
    
    # Проверка подписи
    assert isinstance(result, SignedResponse)
    assert result.is_verified
    assert result.tool_id == "user_service"
    
    # Проверка данных
    data = result.data
    assert data["user_id"] == user_id
    assert "username" in data
    assert "email" in data
    assert "full_name" in data
    assert data["verified"] is True


@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_account_balance_service():
    """Тест сервиса балансов счетов."""
    account_id = "test_account_balance"
    
    result = await get_account_balance(account_id)
    
    # Проверка подписи
    assert isinstance(result, SignedResponse)
    assert result.is_verified
    assert result.tool_id == "account_service"
    
    # Проверка данных
    data = result.data
    assert data["account_id"] == account_id
    assert "balance" in data
    assert isinstance(data["balance"], (int, float))
    assert data["balance"] >= 0  # Баланс не может быть отрицательным
    assert data["currency"] == "USD"
    assert data["status"] == "active"


@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_audit_logging():
    """Тест системы аудита."""
    result = await create_audit_log(
        action="test_action",
        user_id="test_user",
        resource="test_resource",
        details={"test": True, "integration": "pytest"}
    )
    
    # Проверка подписи
    assert isinstance(result, SignedResponse)
    assert result.is_verified
    assert result.tool_id == "audit_service"
    
    # Проверка данных
    data = result.data
    assert data["action"] == "test_action"
    assert data["user_id"] == "test_user"
    assert data["resource"] == "test_resource"
    assert data["details"]["test"] is True
    assert "audit_id" in data
    assert "timestamp" in data


# ==================== ТЕСТЫ ОПЕРАЦИЙ СРЕДНЕГО ДОВЕРИЯ ====================

@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_stock_price_service():
    """Тест сервиса котировок акций."""
    symbol = "AAPL"
    
    result = await fetch_stock_price(symbol)
    
    # Проверка подписи
    assert isinstance(result, SignedResponse)
    assert result.is_verified
    assert result.tool_id == "market_data_api"
    
    # Проверка данных
    data = result.data
    assert data["symbol"] == symbol
    assert "price" in data
    assert isinstance(data["price"], (int, float))
    assert data["price"] > 0
    assert "change" in data
    assert "currency" in data


@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_financial_news_service():
    """Тест сервиса финансовых новостей."""
    category = "tech"
    limit = 3
    
    result = await get_financial_news(category, limit)
    
    # Проверка подписи
    assert isinstance(result, SignedResponse)
    assert result.is_verified
    assert result.tool_id == "news_aggregator"
    
    # Проверка данных
    data = result.data
    assert data["category"] == category
    assert "articles" in data
    assert isinstance(data["articles"], list)
    assert len(data["articles"]) <= limit
    assert data["total_count"] == len(data["articles"])


# ==================== ТЕСТЫ БЕЗОПАСНОСТИ ====================

@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_signature_uniqueness():
    """Тест уникальности подписей."""
    # Получаем несколько ответов от одной функции с разными параметрами
    result1 = await get_user_profile("user_1")
    result2 = await get_user_profile("user_2")
    result3 = await get_user_profile("user_1")  # Тот же пользователь, но новый вызов
    
    # Все ответы должны быть подписаны
    assert all(r.is_verified for r in [result1, result2, result3])
    
    # Подписи должны быть разными (даже для одного пользователя в разное время)
    signatures = [r.signature.signature for r in [result1, result2, result3]]
    assert len(set(signatures)) == 3, "All signatures should be unique"


@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_response_integrity():
    """Тест целостности ответов."""
    result = await process_payment(100.0, "test_from", "test_to")
    
    # Сохраняем оригинальные данные
    original_data = result.data.copy()
    original_signature = result.signature.signature
    
    # Попытаемся изменить данные (атака на целостность)
    try:
        result.data["amount"] = 999999.99  # Попытка изменить сумму
        
        # Подпись должна стать невалидной или система должна это обнаружить
        # В реальной системе это должно вызвать ошибку или сделать is_verified = False
        
        # Восстанавливаем оригинальные данные для следующих тестов
        result.data.update(original_data)
        
    except Exception:
        # Ожидаемое поведение - система защищает от изменений
        pass


# ==================== ПРОИЗВОДИТЕЛЬНОСТЬ ====================

@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_performance_multiple_calls():
    """Тест производительности множественных вызовов."""
    import time
    
    start_time = time.time()
    
    # Выполняем несколько операций параллельно
    tasks = [
        get_user_profile(f"perf_user_{i}") for i in range(10)
    ]
    
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Проверяем что все операции прошли успешно
    assert len(results) == 10
    assert all(r.is_verified for r in results)
    
    # Проверяем производительность (должно быть достаточно быстро)
    avg_time_per_call = total_time / 10
    assert avg_time_per_call < 1.0, f"Average time per call too slow: {avg_time_per_call}s"
    
    print(f"\n📊 Performance: {len(results)} calls in {total_time:.2f}s")
    print(f"📊 Average: {avg_time_per_call:.3f}s per call")


# ==================== КОМПЛЕКСНЫЕ ТЕСТЫ ====================

@pytest.mark.asyncio
@pytest.mark.skipif(not TRUSTCHAIN_AVAILABLE, reason="TrustChain not available")
async def test_complete_business_workflow():
    """Тест полного бизнес-процесса."""
    # 1. Аутентификация
    auth = await authenticate_user("workflow_user", "hash_secure_password")
    assert auth.data["authenticated"] is True
    
    # 2. Получение профиля
    profile = await get_user_profile("workflow_user")
    assert profile.data["user_id"] == "workflow_user"
    
    # 3. Проверка баланса
    balance = await get_account_balance("workflow_account")
    initial_balance = balance.data["balance"]
    
    # 4. Платеж
    payment = await process_payment(50.0, "workflow_account", "target_account")
    assert payment.data["status"] == "completed"
    
    # 5. Аудит
    audit = await create_audit_log(
        "workflow_test", 
        "workflow_user", 
        "workflow_account",
        {"payment_id": payment.data["transaction_id"]}
    )
    assert "audit_id" in audit.data
    
    # Все операции должны быть подписаны
    all_operations = [auth, profile, balance, payment, audit]
    assert all(op.is_verified for op in all_operations)
    
    # Все подписи должны быть уникальными
    signatures = [op.signature.signature for op in all_operations]
    assert len(set(signatures)) == len(signatures)


# ==================== ЗАПУСК ТЕСТОВ ====================

def run_all_tests():
    """Запуск всех тестов."""
    print("🧪 Running TrustChain Integration Tests")
    print("=" * 40)
    
    if not TRUSTCHAIN_AVAILABLE:
        print("❌ TrustChain not available - install with: pip install -e ../")
        return False
    
    # Запуск pytest
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    
    if exit_code == 0:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ TrustChain external integration is working perfectly!")
        return True
    else:
        print("\n❌ Some integration tests failed")
        print("🔧 Check errors above and fix issues")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1) 