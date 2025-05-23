# 🤝 Contributing to TrustChain

Thank you for your interest in contributing to TrustChain! This document provides guidelines for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Release Process](#release-process)

## 📜 Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/trustchain.git
   cd trustchain
   ```
3. **Add the upstream repository**:
   ```bash
   git remote add upstream https://github.com/trustchain/trustchain.git
   ```

## 🛠️ Development Setup

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### Installation

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

### Project Structure

```
trustchain/
├── trustchain/          # Main library code
│   ├── core/           # Core cryptographic functionality
│   ├── tools/          # Tool framework and decorators
│   ├── registry/       # Trust registry implementations
│   └── utils/          # Utility functions
├── tests/              # Test suite
├── examples/           # Usage examples
├── docs/               # Documentation
└── scripts/            # Development scripts
```

## 🔄 Making Changes

### Branch Naming

- `feature/description` - for new features
- `bugfix/description` - for bug fixes
- `docs/description` - for documentation changes
- `refactor/description` - for code refactoring

### Coding Standards

- **Follow PEP 8** style guidelines
- **Use type hints** for all functions
- **Write docstrings** for all public functions and classes
- **Keep functions small** and focused
- **Use meaningful variable names**

### Example:

```python
async def create_trusted_tool(
    tool_id: str,
    algorithm: SignatureAlgorithm = SignatureAlgorithm.ED25519,
    trust_level: TrustLevel = TrustLevel.MEDIUM
) -> BaseTrustedTool:
    """
    Create a new trusted tool with cryptographic signatures.
    
    Args:
        tool_id: Unique identifier for the tool
        algorithm: Cryptographic algorithm to use
        trust_level: Security level for the tool
        
    Returns:
        Configured trusted tool instance
        
    Raises:
        ValueError: If tool_id is invalid
    """
    # Implementation here
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_crypto.py

# Run with coverage
python -m pytest --cov=trustchain

# Run performance tests
python -m pytest tests/performance/
```

### Writing Tests

- **Write tests for all new features**
- **Include edge cases and error conditions**
- **Use descriptive test names**
- **Follow the arrange-act-assert pattern**

Example:

```python
async def test_trusted_tool_signature_verification():
    """Test that tool responses are properly signed and verified."""
    # Arrange
    @TrustedTool("test_tool")
    async def test_tool(data: str) -> dict:
        return {"result": data}
    
    # Act
    response = await test_tool("test_data")
    
    # Assert
    assert response.is_verified
    assert response.signature is not None
    assert response.data["result"] == "test_data"
```

### Test Categories

- **Unit tests**: Test individual components
- **Integration tests**: Test component interactions
- **Performance tests**: Test performance characteristics
- **Security tests**: Test cryptographic functionality

## 📤 Submitting Changes

### Before Submitting

1. **Update your branch**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests**:
   ```bash
   python -m pytest
   ```

3. **Run linters**:
   ```bash
   black trustchain/
   isort trustchain/
   mypy trustchain/
   ```

4. **Update documentation** if needed

### Pull Request Process

1. **Create a pull request** with a clear title and description
2. **Reference any related issues**
3. **Include screenshots** for UI changes
4. **Add tests** for new functionality
5. **Update documentation** as needed

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Updated documentation

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated
- [ ] Documentation updated
```

## 🏷️ Release Process

### Versioning

We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

### Release Steps

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md**
3. **Create release PR**
4. **Tag the release**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
5. **Publish to PyPI** (automated via GitHub Actions)

## 🤔 Questions?

- **Open an issue** for bugs or feature requests
- **Start a discussion** for questions or ideas
- **Join our Discord** for real-time chat
- **Check the documentation** for detailed guides

## 🙏 Recognition

Contributors will be recognized in:
- **CONTRIBUTORS.md** file
- **Release notes**
- **Documentation credits**

Thank you for contributing to TrustChain! 🔗 