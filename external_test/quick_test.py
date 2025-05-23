#!/usr/bin/env python3
"""
🧪 Quick External Test - TrustChain

Быстрая проверка что TrustChain работает как внешняя библиотека.

Author: Ed Cherednik (edcherednik@gmail.com)
Telegram: @EdCher

Run: python quick_test.py
"""

import asyncio
import sys
from typing import Dict, Any

def test_import():
    """Тест импорта основных компонентов."""
    print("🧪 Quick TrustChain External Test")
    print("=" * 32)
    
    try:
        # Тест базового импорта
        from trustchain import TrustedTool, TrustLevel, MemoryRegistry
        from trustchain.core.models import SignedResponse
        print("✅ TrustChain import: SUCCESS")
        return True
    except ImportError as e:
        print(f"❌ TrustChain import: FAILED - {e}")
        print("💡 Fix: run 'pip install -e ../' from external_test directory")
        return False

def test_decorator():
    """Тест работы декоратора @TrustedTool."""
    try:
        from trustchain import TrustedTool, TrustLevel
        
        @TrustedTool("external_quick_test", trust_level=TrustLevel.HIGH)
        async def test_function(message: str) -> Dict[str, Any]:
            """Тестовая функция для проверки декоратора."""
            return {
                "message": message,
                "status": "processed", 
                "external_test": True,
                "function": "quick_test"
            }
        
        print("✅ @TrustedTool decorator: SUCCESS")
        return test_function
    except Exception as e:
        print(f"❌ @TrustedTool decorator: FAILED - {e}")
        return None

async def test_signature_creation(test_func):
    """Тест создания подписей."""
    try:
        # Вызываем функцию
        result = await test_func("Hello from external test!")
        
        # Проверяем что получили SignedResponse
        from trustchain.core.models import SignedResponse
        if isinstance(result, SignedResponse):
            print("✅ Signature creation: SUCCESS")
            return result
        else:
            print(f"❌ Signature creation: FAILED - got {type(result)}")
            return None
    except Exception as e:
        print(f"❌ Signature creation: FAILED - {e}")
        return None

def test_signature_verification(result):
    """Тест проверки подписей."""
    try:
        # Проверяем что подпись валидна
        if hasattr(result, 'is_verified') and result.is_verified:
            print("✅ Signature verification: SUCCESS")
            return True
        else:
            print("❌ Signature verification: FAILED - signature not verified")
            return False
    except Exception as e:
        print(f"❌ Signature verification: FAILED - {e}")
        return False

def display_results(result):
    """Показываем результаты теста."""
    if result:
        print(f"✅ Response type: {type(result)}")
        print(f"✅ Data: {result.data}")
        print(f"✅ Tool ID: {result.tool_id}")
        print(f"✅ Is verified: {result.is_verified}")
        if hasattr(result, 'signature'):
            print(f"✅ Signature: {result.signature.signature[:20]}...")
        
        return True
    return False

async def main():
    """Основная функция теста."""
    success_count = 0
    total_tests = 4
    
    # Тест 1: Импорт
    if test_import():
        success_count += 1
    else:
        print("\n❌ Critical error: Cannot import TrustChain")
        print("🔧 Make sure you've installed TrustChain:")
        print("   cd ../")
        print("   pip install -e .")
        print("   cd external_test")
        sys.exit(1)
    
    # Тест 2: Декоратор
    test_func = test_decorator()
    if test_func:
        success_count += 1
    else:
        print("\n❌ Critical error: Decorator not working")
        sys.exit(1)
    
    # Тест 3: Создание подписи
    result = await test_signature_creation(test_func)
    if result:
        success_count += 1
    else:
        print("\n❌ Critical error: Signature creation failed")
        sys.exit(1)
    
    # Тест 4: Проверка подписи
    if test_signature_verification(result):
        success_count += 1
    
    # Показываем детали результата
    if display_results(result):
        print("\n🎉 TrustChain external integration: PERFECT!")
    
    # Финальный итог
    print(f"\n📊 Test Results: {success_count}/{total_tests} passed")
    
    if success_count == total_tests:
        print("🏆 ALL TESTS PASSED!")
        print("✅ TrustChain is ready for external use!")
        return True
    else:
        print("❌ Some tests failed")
        print("🔧 Check installation and try again")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1) 