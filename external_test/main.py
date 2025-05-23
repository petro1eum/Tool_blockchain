#!/usr/bin/env python3
"""
🚀 External Project Main Demo - TrustChain

Основное демо внешнего проекта, использующего TrustChain.

Author: Ed Cherednik (edcherednik@gmail.com)
Telegram: @EdCher

Run: python main.py
"""

import asyncio
import sys
from typing import List, Dict, Any

# Импорт нашей бизнес-логики
from business_logic import (
    process_payment,
    get_account_balance,
    get_user_profile,
    authenticate_user,
    fetch_stock_price,
    get_financial_news,
    create_audit_log,
    simulate_business_workflow,
    demonstrate_signature_verification
)

# Импорт TrustChain для проверок
try:
    from trustchain.core.models import SignedResponse
    from trustchain import __version__ as trustchain_version
except ImportError:
    print("❌ TrustChain not available!")
    print("🔧 Install it with: pip install -e ../")
    sys.exit(1)


class ExternalProjectDemo:
    """Класс для демонстрации внешнего проекта с TrustChain."""
    
    def __init__(self):
        self.results: List[SignedResponse] = []
        self.errors: List[str] = []
    
    def print_header(self):
        """Печать заголовка демо."""
        print("🚀 TrustChain External Project Demo")
        print("=" * 45)
        print(f"📦 TrustChain Version: {trustchain_version}")
        print(f"👨‍💻 Author: Ed Cherednik (@EdCher)")
        print(f"🎯 Goal: Demonstrate external library usage")
        print()
    
    async def test_critical_operations(self):
        """Тест критически важных операций."""
        print("🔒 Testing CRITICAL trust level operations...")
        print("-" * 40)
        
        try:
            # Аутентификация
            auth = await authenticate_user("admin_user", "hash_secure_admin_pass")
            self.results.append(auth)
            print(f"✅ Authentication: {auth.data['authenticated']}")
            
            # Финансовый платеж
            payment = await process_payment(1500.0, "corporate_acc", "vendor_acc")
            self.results.append(payment)
            print(f"✅ Payment: {payment.data['transaction_id']} - ${payment.data['final_amount']}")
            
            return True
        except Exception as e:
            error_msg = f"Critical operations failed: {e}"
            self.errors.append(error_msg)
            print(f"❌ {error_msg}")
            return False
    
    async def test_high_trust_operations(self):
        """Тест операций высокого доверия."""
        print("\n🔐 Testing HIGH trust level operations...")
        print("-" * 40)
        
        try:
            # Профиль пользователя
            profile = await get_user_profile("external_test_user")
            self.results.append(profile)
            print(f"✅ User Profile: {profile.data['full_name']}")
            
            # Баланс счета
            balance = await get_account_balance("test_account_001")
            self.results.append(balance)
            print(f"✅ Account Balance: ${balance.data['balance']}")
            
            # Аудит лог
            audit = await create_audit_log(
                "external_test", 
                "test_user", 
                "demo_resource",
                {"demo": True, "version": "1.0"}
            )
            self.results.append(audit)
            print(f"✅ Audit Log: {audit.data['audit_id']}")
            
            return True
        except Exception as e:
            error_msg = f"High trust operations failed: {e}"
            self.errors.append(error_msg)
            print(f"❌ {error_msg}")
            return False
    
    async def test_medium_trust_operations(self):
        """Тест операций среднего доверия."""
        print("\n📊 Testing MEDIUM trust level operations...")
        print("-" * 40)
        
        try:
            # Данные акций
            stock = await fetch_stock_price("GOOGL")
            self.results.append(stock)
            print(f"✅ Stock Data: {stock.data['symbol']} - ${stock.data['price']}")
            
            # Финансовые новости
            news = await get_financial_news("tech", 3)
            self.results.append(news)
            print(f"✅ Financial News: {news.data['total_count']} articles")
            
            return True
        except Exception as e:
            error_msg = f"Medium trust operations failed: {e}"
            self.errors.append(error_msg)
            print(f"❌ {error_msg}")
            return False
    
    def verify_all_signatures(self):
        """Проверка всех подписей."""
        print("\n🔍 Verifying all cryptographic signatures...")
        print("-" * 45)
        
        verified_count = 0
        for i, result in enumerate(self.results, 1):
            tool_id = result.tool_id
            is_verified = result.is_verified
            signature_preview = result.signature.signature[:12] if hasattr(result, 'signature') else "N/A"
            
            print(f"  {i}. {tool_id}: {'✅' if is_verified else '❌'} ({signature_preview}...)")
            
            if is_verified:
                verified_count += 1
        
        success_rate = (verified_count / len(self.results)) * 100 if self.results else 0
        print(f"\n📈 Verification Success Rate: {verified_count}/{len(self.results)} ({success_rate:.1f}%)")
        
        return success_rate == 100.0
    
    def display_security_summary(self):
        """Показать сводку безопасности."""
        print("\n🛡️ Security Summary")
        print("-" * 20)
        
        trust_levels = {}
        for result in self.results:
            # Определяем уровень доверия по tool_id
            if result.tool_id in ["auth_service", "payment_processor"]:
                level = "CRITICAL"
            elif result.tool_id in ["user_service", "account_service", "audit_service"]:
                level = "HIGH"
            else:
                level = "MEDIUM"
            
            trust_levels[level] = trust_levels.get(level, 0) + 1
        
        for level, count in trust_levels.items():
            print(f"  🔒 {level}: {count} operations")
        
        print(f"\n  📊 Total Operations: {len(self.results)}")
        print(f"  ✅ All Signed: {len(self.results)} signatures")
        print(f"  🔐 All Verified: {all(r.is_verified for r in self.results)}")
        
        if self.errors:
            print(f"  ❌ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"     • {error}")
    
    async def run_comprehensive_demo(self):
        """Запуск полного демо."""
        self.print_header()
        
        # Выполняем тесты
        critical_ok = await self.test_critical_operations()
        high_ok = await self.test_high_trust_operations() 
        medium_ok = await self.test_medium_trust_operations()
        
        # Проверяем подписи
        signatures_ok = self.verify_all_signatures()
        
        # Показываем сводку
        self.display_security_summary()
        
        # Финальная оценка
        all_tests_passed = critical_ok and high_ok and medium_ok and signatures_ok
        
        print("\n🏆 Final Assessment")
        print("-" * 18)
        print(f"✅ Critical Operations: {'PASS' if critical_ok else 'FAIL'}")
        print(f"✅ High Trust Operations: {'PASS' if high_ok else 'FAIL'}")
        print(f"✅ Medium Trust Operations: {'PASS' if medium_ok else 'FAIL'}")
        print(f"✅ Signature Verification: {'PASS' if signatures_ok else 'FAIL'}")
        
        if all_tests_passed:
            print("\n🎉 SUCCESS: TrustChain external integration is PERFECT!")
            print("✅ Ready for production use!")
            print("🔒 All business operations are cryptographically secured!")
        else:
            print("\n❌ FAILURE: Some tests failed")
            print("🔧 Check errors above and fix issues")
        
        return all_tests_passed


async def quick_integration_test():
    """Быстрый тест интеграции."""
    print("⚡ Quick Integration Test")
    print("-" * 25)
    
    try:
        # Простой тест одной функции
        result = await get_user_profile("quick_test_user")
        
        print(f"✅ Function call: SUCCESS")
        print(f"✅ Return type: {type(result)}")
        print(f"✅ Has signature: {hasattr(result, 'signature')}")
        print(f"✅ Is verified: {result.is_verified}")
        print(f"✅ Data access: {result.data['user_id']}")
        
        return True
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False


async def main():
    """Основная функция демо."""
    print("🔧 Starting TrustChain External Project Demo...")
    print()
    
    # Быстрый тест для проверки работоспособности
    quick_ok = await quick_integration_test()
    if not quick_ok:
        print("\n💥 Quick test failed - stopping demo")
        return False
    
    print("\n" + "="*50)
    
    # Полное демо
    demo = ExternalProjectDemo()
    success = await demo.run_comprehensive_demo()
    
    # Дополнительные демонстрации из business_logic
    print("\n" + "="*50)
    print("🏢 Additional Business Workflow Demo")
    print("="*50)
    
    try:
        await simulate_business_workflow()
        verification_result = await demonstrate_signature_verification()
        
        if verification_result:
            print("\n✅ Business workflow signatures: ALL VERIFIED")
        else:
            print("\n❌ Business workflow signatures: SOME FAILED")
    except Exception as e:
        print(f"\n❌ Business workflow demo failed: {e}")
        success = False
    
    # Финальное заключение
    print("\n" + "="*50)
    print("🎯 CONCLUSION")
    print("="*50)
    
    if success:
        print("🏆 TrustChain external integration: COMPLETE SUCCESS!")
        print()
        print("Key achievements:")
        print("  ✅ Library imports correctly")
        print("  ✅ Decorators work seamlessly") 
        print("  ✅ Signatures are created automatically")
        print("  ✅ Verification works perfectly")
        print("  ✅ All trust levels supported")
        print("  ✅ Real business logic protected")
        print()
        print("🚀 READY FOR PRODUCTION USE!")
    else:
        print("❌ Some issues detected in external integration")
        print("🔧 Please review errors and fix before production use")
    
    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error in demo: {e}")
        sys.exit(1) 