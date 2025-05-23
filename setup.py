from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="trustchain",
    version="0.1.0",
    author="TrustChain Contributors",
    author_email="info@trustchain.dev",
    description="Cryptographically signed AI tool responses for preventing hallucinations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/trustchain/trustchain",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Security :: Cryptography",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Cryptography
        "PyNaCl>=1.5.0",
        "cryptography>=41.0.0",
        
        # Serialization
        "pydantic>=2.0.0",
        "msgpack>=1.0.0",
        
        # Async support
        "asyncio-mqtt>=0.16.0",
        "aioredis>=2.0.0",
        
        # Utilities
        "click>=8.0.0",
        "rich>=13.0.0",
        "typer>=0.9.0",
        
        # Configuration
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "kafka": [
            "kafka-python>=2.0.0",
            "aiokafka>=0.10.0",
            "confluent-kafka>=2.3.0",
        ],
        "redis": [
            "redis>=5.0.0",
            "aioredis>=2.0.0",
        ],
        "blockchain": [
            "web3>=6.0.0",
            "ipfshttpclient>=0.8.0",
        ],
        "monitoring": [
            "prometheus-client>=0.19.0",
            "grafana-api>=1.0.0",
            "fastapi>=0.104.0",
            "uvicorn>=0.24.0",
        ],
        "ai": [
            "langchain>=0.1.0",
            "openai>=1.0.0",
            "anthropic>=0.8.0",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.23.0",
            "black>=23.0.0",
            "isort>=5.0.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
            "coverage>=7.0.0",
        ],
        "all": [
            "kafka-python>=2.0.0", "aiokafka>=0.10.0", "confluent-kafka>=2.3.0",
            "redis>=5.0.0", "aioredis>=2.0.0",
            "web3>=6.0.0", "ipfshttpclient>=0.8.0",
            "prometheus-client>=0.19.0", "grafana-api>=1.0.0", "fastapi>=0.104.0", "uvicorn>=0.24.0",
            "langchain>=0.1.0", "openai>=1.0.0", "anthropic>=0.8.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "trustchain=trustchain.cli:main",
        ],
    },
) 