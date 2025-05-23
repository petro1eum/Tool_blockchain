#!/usr/bin/env python3
"""
🏢 Business Logic with TrustChain

Примеры реальной бизнес-логики, защищенной TrustChain.

Author: Ed Cherednik (edcherednik@gmail.com)
Telegram: @EdCher
"""

import asyncio
import time
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

# Импорт TrustChain как внешней библиотеки
from trustchain import TrustedTool, TrustLevel
from trustchain.core.models import SignedResponse


# ==================== ФИНАНСОВЫЕ СЕРВИСЫ ====================

@TrustedTool("payment_processor", trust_level=TrustLevel.CRITICAL)
async def process_payment(
    amount: float, 
    from_account: str, 
    to_account: str,
    currency: str = "USD"
) -> Dict[str, Any]:
    """
    Обработка финансового платежа с максимальной защитой.
    
    Эта функция обрабатывает критически важные финансовые транзакции.
    Каждый ответ автоматически подписывается криптографически.
    """
    # Симуляция проверки счетов
    await asyncio.sleep(0.1)
    
    # Вычисление комиссии (1% для простоты)
    fee = round(amount * 0.01, 2)
    final_amount = amount - fee
    
    # Генерация ID транзакции
    transaction_data = f"{from_account}-{to_account}-{amount}-{time.time()}"
    transaction_id = hashlib.sha256(transaction_data.encode()).hexdigest()[:16]
    
    return {
        "transaction_id": f"tx_{transaction_id}",
        "amount": amount,
        "fee": fee,
        "final_amount": final_amount,
        "from_account": from_account,
        "to_account": to_account,
        "currency": currency,
        "status": "completed",
        "timestamp": datetime.now().isoformat(),
        "verified": True,
        "processor": "TrustChain Payment System"
    }


@TrustedTool("account_service", trust_level=TrustLevel.HIGH)
async def get_account_balance(account_id: str) -> Dict[str, Any]:
    """Получение баланса счета с высоким уровнем доверия."""
    # Симуляция запроса к базе данных
    await asyncio.sleep(0.05)
    
    # Простая симуляция баланса на основе хеша ID
    balance_seed = hash(account_id) % 10000
    balance = abs(balance_seed) + 1000.0  # Минимум $1000
    
    return {
        "account_id": account_id,
        "balance": balance,
        "currency": "USD",
        "account_type": "checking",
        "status": "active",
        "last_updated": datetime.now().isoformat(),
        "bank": "TrustChain Bank"
    }


# ==================== ПОЛЬЗОВАТЕЛЬСКИЕ СЕРВИСЫ ====================

@TrustedTool("user_service", trust_level=TrustLevel.HIGH)
async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Получение профиля пользователя с защитой данных."""
    await asyncio.sleep(0.08)
    
    # Симуляция пользовательских данных
    user_seed = hash(user_id) % 1000
    
    return {
        "user_id": user_id,
        "username": f"user_{user_seed}",
        "email": f"user{user_seed}@trustchain.example",
        "full_name": f"User {user_seed} Smith",
        "registration_date": "2024-01-15",
        "verified": True,
        "subscription": "premium" if user_seed % 3 == 0 else "basic",
        "last_login": datetime.now().isoformat(),
        "profile_version": "2.1"
    }


@TrustedTool("auth_service", trust_level=TrustLevel.CRITICAL)
async def authenticate_user(username: str, password_hash: str) -> Dict[str, Any]:
    """Аутентификация пользователя с критическим уровнем безопасности."""
    await asyncio.sleep(0.12)  # Симуляция проверки пароля
    
    # Простая симуляция проверки
    is_valid = len(password_hash) > 10 and password_hash.startswith("hash_")
    
    if is_valid:
        session_token = hashlib.sha256(f"{username}-{time.time()}".encode()).hexdigest()
        return {
            "username": username,
            "authenticated": True,
            "session_token": session_token,
            "expires_at": datetime.now().isoformat(),
            "permissions": ["read", "write"] if username.startswith("admin") else ["read"],
            "auth_method": "password",
            "login_timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "username": username,
            "authenticated": False,
            "error": "Invalid credentials",
            "attempt_timestamp": datetime.now().isoformat(),
            "security_alert": True
        }


# ==================== ВНЕШНИЕ API ИНТЕГРАЦИИ ====================

@TrustedTool("market_data_api", trust_level=TrustLevel.MEDIUM)
async def fetch_stock_price(symbol: str) -> Dict[str, Any]:
    """Получение данных о ценах акций с внешнего API."""
    await asyncio.sleep(0.15)  # Симуляция HTTP запроса
    
    # Симуляция данных биржи
    stock_prices = {
        "AAPL": 192.45,
        "GOOGL": 2875.60,
        "MSFT": 425.20,
        "TSLA": 248.90,
        "AMZN": 3456.78,
        "META": 512.34
    }
    
    price = stock_prices.get(symbol.upper(), 100.0 + (hash(symbol) % 500))
    change = round((hash(symbol + "change") % 2000 - 1000) / 100, 2)
    
    return {
        "symbol": symbol.upper(),
        "price": price,
        "change": change,
        "change_percent": round((change / price) * 100, 2),
        "currency": "USD",
        "market": "NASDAQ",
        "volume": hash(symbol) % 1000000,
        "timestamp": datetime.now().isoformat(),
        "source": "TrustChain Market Data API"
    }


@TrustedTool("news_aggregator", trust_level=TrustLevel.MEDIUM)
async def get_financial_news(category: str = "general", limit: int = 5) -> Dict[str, Any]:
    """Агрегация финансовых новостей."""
    await asyncio.sleep(0.2)
    
    # Симуляция новостей
    news_templates = [
        "Market Report: {category} sector shows strong performance",
        "Breaking: Major announcement affects {category} trading",
        "Analysis: {category} trends for the upcoming quarter",
        "Update: Regulatory changes impact {category} market",
        "Spotlight: Innovation drives {category} growth"
    ]
    
    articles = []
    for i in range(min(limit, len(news_templates))):
        articles.append({
            "id": f"news_{hash(category + str(i)) % 10000}",
            "title": news_templates[i].format(category=category),
            "summary": f"Detailed analysis of {category} market conditions...",
            "source": f"TrustNews {i+1}",
            "published_at": datetime.now().isoformat(),
            "category": category,
            "relevance_score": round((hash(category + str(i)) % 100) / 100, 2)
        })
    
    return {
        "category": category,
        "articles": articles,
        "total_count": len(articles),
        "retrieved_at": datetime.now().isoformat(),
        "api_version": "v2.1",
        "source": "TrustChain News Aggregator"
    }


# ==================== АДМИНИСТРАТИВНЫЕ ФУНКЦИИ ====================

@TrustedTool("audit_service", trust_level=TrustLevel.HIGH)
async def create_audit_log(
    action: str, 
    user_id: str, 
    resource: str, 
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Создание записи аудита для соответствия требованиям."""
    
    audit_id = hashlib.sha256(f"{action}-{user_id}-{resource}-{time.time()}".encode()).hexdigest()[:12]
    
    return {
        "audit_id": f"audit_{audit_id}",
        "action": action,
        "user_id": user_id,
        "resource": resource,
        "details": details or {},
        "timestamp": datetime.now().isoformat(),
        "ip_address": "192.168.1.100",  # Симуляция
        "user_agent": "TrustChain Client v1.0",
        "audit_level": "standard",
        "compliance": "SOX, GDPR",
        "retention_period": "7_years"
    }


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def simulate_business_workflow():
    """Симуляция типичного бизнес-процесса с использованием TrustChain."""
    print("🏢 Симуляция бизнес-процесса с TrustChain")
    print("=" * 45)
    
    # 1. Аутентификация пользователя
    print("\n1️⃣ Аутентификация пользователя...")
    auth_result = await authenticate_user("john_doe", "hash_secure_password_123")
    print(f"   ✅ Пользователь аутентифицирован: {auth_result.data['authenticated']}")
    
    if auth_result.data['authenticated']:
        # 2. Получение профиля пользователя
        print("\n2️⃣ Загрузка профиля пользователя...")
        profile = await get_user_profile("john_doe")
        print(f"   ✅ Профиль загружен: {profile.data['full_name']}")
        
        # 3. Проверка баланса счета
        print("\n3️⃣ Проверка баланса счета...")
        balance = await get_account_balance("acc_123")
        print(f"   ✅ Баланс: ${balance.data['balance']}")
        
        # 4. Обработка платежа
        print("\n4️⃣ Обработка платежа...")
        payment = await process_payment(250.0, "acc_123", "acc_456")
        print(f"   ✅ Платеж: {payment.data['transaction_id']} - ${payment.data['final_amount']}")
        
        # 5. Создание записи аудита
        print("\n5️⃣ Создание записи аудита...")
        audit = await create_audit_log("payment", "john_doe", "acc_123", {
            "transaction_id": payment.data['transaction_id'],
            "amount": payment.data['amount']
        })
        print(f"   ✅ Аудит: {audit.data['audit_id']}")
        
        # 6. Получение рыночных данных
        print("\n6️⃣ Получение данных рынка...")
        market_data = await fetch_stock_price("AAPL")
        print(f"   ✅ AAPL: ${market_data.data['price']} ({market_data.data['change']:+.2f})")
    
    print("\n🎉 Бизнес-процесс завершен успешно!")
    print("🔐 Все операции криптографически подписаны TrustChain")
    
    return True


# ==================== ДЕМОНСТРАЦИОННЫЕ ФУНКЦИИ ====================

async def demonstrate_signature_verification():
    """Демонстрация проверки подписей в реальном бизнес-контексте."""
    print("\n🔍 Демонстрация проверки подписей")
    print("-" * 35)
    
    # Получаем несколько подписанных ответов
    responses = []
    
    payment = await process_payment(100.0, "acc_001", "acc_002")
    user = await get_user_profile("test_user")
    stock = await fetch_stock_price("TSLA")
    
    responses.extend([payment, user, stock])
    
    print("Проверка криптографических подписей:")
    for i, response in enumerate(responses, 1):
        print(f"  {i}. Tool: {response.tool_id}")
        print(f"     Type: {type(response)}")
        print(f"     Verified: {response.is_verified}")
        print(f"     Signature: {response.signature.signature[:15]}...")
        print()
    
    return all(r.is_verified for r in responses)


if __name__ == "__main__":
    print("🏢 TrustChain Business Logic Demo")
    print("Author: Ed Cherednik (@EdCher)")
    print()
    
    async def main():
        # Запуск демонстрации
        await simulate_business_workflow()
        verification_success = await demonstrate_signature_verification()
        
        if verification_success:
            print("✅ Все подписи прошли проверку!")
            print("🔒 Бизнес-логика полностью защищена TrustChain")
        else:
            print("❌ Обнаружены проблемы с подписями")
    
    asyncio.run(main()) 