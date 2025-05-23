#!/bin/bash
# 🔧 Setup External Environment for TrustChain Testing
# 
# Автоматическая настройка окружения для тестирования TrustChain как внешней библиотеки.
#
# Author: Ed Cherednik (edcherednik@gmail.com)
# Telegram: @EdCher
#
# Usage: ./setup_external_env.sh

set -e  # Остановиться при первой ошибке

echo "🔧 TrustChain External Environment Setup"
echo "========================================="
echo "👨‍💻 Author: Ed Cherednik (@EdCher)"
echo ""

# Проверка что мы в правильной директории
if [[ ! -f "README_EXTERNAL_TEST.md" ]]; then
    echo "❌ Error: Run this script from the external_test directory"
    echo "💡 Usage: cd external_test && ./setup_external_env.sh"
    exit 1
fi

echo "📁 Current directory: $(pwd)"
echo "📋 Setting up external test environment..."

# Шаг 1: Проверка Python
echo ""
echo "1️⃣ Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ Found: $PYTHON_VERSION"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python --version)
    echo "✅ Found: $PYTHON_VERSION"
    PYTHON_CMD="python"
else
    echo "❌ Python not found! Please install Python 3.8+"
    exit 1
fi

# Проверка версии Python
PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
    echo "✅ Python version is compatible (3.$PYTHON_MINOR)"
else
    echo "❌ Python 3.8+ required, found $PYTHON_MAJOR.$PYTHON_MINOR"
    exit 1
fi

# Шаг 2: Проверка и установка TrustChain
echo ""
echo "2️⃣ Installing TrustChain library..."

# Переходим в корневую директорию проекта
cd ../

# Проверяем что мы в корне TrustChain проекта
if [[ ! -f "pyproject.toml" ]] || [[ ! -d "trustchain" ]]; then
    echo "❌ Error: TrustChain project not found"
    echo "💡 Make sure external_test is inside Tool_blockchain directory"
    exit 1
fi

echo "📦 Installing TrustChain in editable mode..."
if $PYTHON_CMD -m pip install -e . --quiet; then
    echo "✅ TrustChain installed successfully"
else
    echo "❌ Failed to install TrustChain"
    echo "🔧 Try manually: pip install -e ."
    exit 1
fi

# Шаг 3: Проверка установки
echo ""
echo "3️⃣ Verifying TrustChain installation..."

if $PYTHON_CMD -c "import trustchain; print(f'✅ TrustChain v{trustchain.__version__} imported successfully')" 2>/dev/null; then
    echo "✅ Import verification passed"
else
    echo "❌ TrustChain import failed"
    echo "🔧 Check installation manually"
    exit 1
fi

# Возвращаемся в external_test
cd external_test/

# Шаг 4: Установка зависимостей для тестов
echo ""
echo "4️⃣ Installing test dependencies..."

if [[ -f "requirements.txt" ]]; then
    echo "📋 Installing from requirements.txt..."
    if $PYTHON_CMD -m pip install -r requirements.txt --quiet; then
        echo "✅ Test dependencies installed"
    else
        echo "⚠️ Some test dependencies failed to install (continuing anyway)"
    fi
else
    echo "⚠️ requirements.txt not found, installing basic dependencies..."
    $PYTHON_CMD -m pip install pytest pytest-asyncio --quiet
fi

# Шаг 5: Проверка файлов проекта
echo ""
echo "5️⃣ Checking project files..."

required_files=("quick_test.py" "business_logic.py" "main.py" "test_integration.py")
missing_files=()

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file"
    else
        echo "❌ $file - MISSING"
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo ""
    echo "❌ Missing files detected: ${missing_files[*]}"
    echo "🔧 Please ensure all project files are present"
    exit 1
fi

# Шаг 6: Запуск быстрого теста
echo ""
echo "6️⃣ Running quick verification test..."

if $PYTHON_CMD quick_test.py; then
    echo "✅ Quick test passed!"
else
    echo "❌ Quick test failed"
    echo "🔧 Check the error messages above"
    exit 1
fi

# Финальная проверка
echo ""
echo "🎉 SETUP COMPLETE!"
echo "=================="
echo ""
echo "✅ All components installed and verified:"
echo "  📦 TrustChain library: READY"
echo "  🧪 Test environment: READY"
echo "  📁 Project files: READY"
echo "  ⚡ Quick test: PASSED"
echo ""
echo "🚀 Next steps:"
echo "  • Run full demo: $PYTHON_CMD main.py"
echo "  • Run pytest tests: $PYTHON_CMD test_integration.py"
echo "  • Run specific tests: $PYTHON_CMD -m pytest test_integration.py -v"
echo ""
echo "📚 Available commands:"
echo "  $PYTHON_CMD quick_test.py           # Quick verification"
echo "  $PYTHON_CMD main.py                 # Full demo"
echo "  $PYTHON_CMD business_logic.py       # Business workflow demo"
echo "  $PYTHON_CMD test_integration.py     # Integration tests"
echo ""
echo "🎯 External TrustChain integration is ready for testing!"
echo ""
echo "👨‍💻 Author: Ed Cherednik (@EdCher)"
echo "📧 Email: edcherednik@gmail.com" 