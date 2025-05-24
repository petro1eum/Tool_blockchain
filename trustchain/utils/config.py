"""Configuration management for TrustChain."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from dotenv import load_dotenv

from trustchain.utils.exceptions import ConfigurationError


@dataclass
class CryptoConfig:
    """Cryptographic configuration."""

    algorithm: str = "Ed25519"
    key_size: int = 32
    signature_format: str = "base64"
    hash_algorithm: str = "sha256"


@dataclass
class RegistryConfig:
    """Trust registry configuration."""

    backend: str = "memory"  # memory, redis, kafka
    url: Optional[str] = None
    namespace: str = "trustchain"
    ttl: int = 3600  # nonce TTL in seconds

    # Redis specific
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    # Kafka specific
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "trustchain"
    kafka_auto_offset_reset: str = "earliest"


@dataclass
class SecurityConfig:
    """Security configuration."""

    nonce_window: int = 300  # seconds
    max_chain_length: int = 100
    signature_cache_ttl: int = 3600
    key_rotation_interval: int = 86400  # 24 hours
    require_https: bool = True
    allowed_origins: list = field(default_factory=lambda: ["*"])


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""

    enabled: bool = True
    metrics_port: int = 8090
    dashboard_port: int = 8080
    log_level: str = "INFO"
    export_prometheus: bool = False
    prometheus_endpoint: Optional[str] = None
    export_grafana: bool = False
    grafana_api_key: Optional[str] = None


@dataclass
class TrustChainConfig:
    """Main TrustChain configuration."""

    crypto: CryptoConfig = field(default_factory=CryptoConfig)
    registry: RegistryConfig = field(default_factory=RegistryConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    # Global settings
    debug: bool = False
    environment: str = "development"
    app_name: str = "trustchain"
    version: str = "0.1.0"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustChainConfig":
        """Create config from dictionary."""
        return cls(
            crypto=CryptoConfig(**data.get("crypto", {})),
            registry=RegistryConfig(**data.get("registry", {})),
            security=SecurityConfig(**data.get("security", {})),
            monitoring=MonitoringConfig(**data.get("monitoring", {})),
            debug=data.get("debug", False),
            environment=data.get("environment", "development"),
            app_name=data.get("app_name", "trustchain"),
            version=data.get("version", "0.1.0"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "crypto": {
                "algorithm": self.crypto.algorithm,
                "key_size": self.crypto.key_size,
                "signature_format": self.crypto.signature_format,
                "hash_algorithm": self.crypto.hash_algorithm,
            },
            "registry": {
                "backend": self.registry.backend,
                "url": self.registry.url,
                "namespace": self.registry.namespace,
                "ttl": self.registry.ttl,
                "redis_host": self.registry.redis_host,
                "redis_port": self.registry.redis_port,
                "redis_db": self.registry.redis_db,
                "redis_password": self.registry.redis_password,
                "kafka_bootstrap_servers": self.registry.kafka_bootstrap_servers,
                "kafka_group_id": self.registry.kafka_group_id,
                "kafka_auto_offset_reset": self.registry.kafka_auto_offset_reset,
            },
            "security": {
                "nonce_window": self.security.nonce_window,
                "max_chain_length": self.security.max_chain_length,
                "signature_cache_ttl": self.security.signature_cache_ttl,
                "key_rotation_interval": self.security.key_rotation_interval,
                "require_https": self.security.require_https,
                "allowed_origins": self.security.allowed_origins,
            },
            "monitoring": {
                "enabled": self.monitoring.enabled,
                "metrics_port": self.monitoring.metrics_port,
                "dashboard_port": self.monitoring.dashboard_port,
                "log_level": self.monitoring.log_level,
                "export_prometheus": self.monitoring.export_prometheus,
                "prometheus_endpoint": self.monitoring.prometheus_endpoint,
                "export_grafana": self.monitoring.export_grafana,
                "grafana_api_key": self.monitoring.grafana_api_key,
            },
            "debug": self.debug,
            "environment": self.environment,
            "app_name": self.app_name,
            "version": self.version,
        }

    def validate(self) -> None:
        """Validate configuration."""
        # Validate crypto config
        if self.crypto.algorithm not in ["Ed25519", "RSA", "ECDSA"]:
            raise ConfigurationError(
                f"Unsupported algorithm: {self.crypto.algorithm}",
                config_key="crypto.algorithm",
            )

        # Validate registry config
        if self.registry.backend not in ["memory", "redis", "kafka"]:
            raise ConfigurationError(
                f"Unsupported registry backend: {self.registry.backend}",
                config_key="registry.backend",
            )

        # Validate security config
        if self.security.nonce_window <= 0:
            raise ConfigurationError(
                "Nonce window must be positive", config_key="security.nonce_window"
            )

        if self.security.max_chain_length <= 0:
            raise ConfigurationError(
                "Max chain length must be positive",
                config_key="security.max_chain_length",
            )

        # Validate monitoring config
        if self.monitoring.metrics_port == self.monitoring.dashboard_port:
            raise ConfigurationError(
                "Metrics and dashboard ports must be different",
                config_key="monitoring.ports",
            )


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    env_file: Optional[Union[str, Path]] = None,
) -> TrustChainConfig:
    """
    Load configuration from file and environment variables.

    Args:
        config_path: Path to YAML config file
        env_file: Path to .env file

    Returns:
        TrustChainConfig instance
    """
    # Load environment variables
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()  # Load from .env in current directory

    config_data: Dict[str, Any] = {}

    # Load from YAML file if provided
    if config_path:
        config_path = Path(config_path)
        if not config_path.exists():
            raise ConfigurationError(f"Config file not found: {config_path}")

        try:
            with open(config_path) as f:
                file_config = yaml.safe_load(f) or {}
                config_data.update(file_config)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML config: {e}")

    # Override with environment variables
    env_config = _load_from_env()
    _deep_merge(config_data, env_config)

    # Create and validate config
    config = TrustChainConfig.from_dict(config_data)
    config.validate()

    return config


def _load_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    config: Dict[str, Any] = {}

    # Crypto config
    if os.getenv("TRUSTCHAIN_CRYPTO_ALGORITHM"):
        config.setdefault("crypto", {})["algorithm"] = os.getenv(
            "TRUSTCHAIN_CRYPTO_ALGORITHM"
        )

    # Registry config
    if os.getenv("TRUSTCHAIN_REGISTRY_BACKEND"):
        config.setdefault("registry", {})["backend"] = os.getenv(
            "TRUSTCHAIN_REGISTRY_BACKEND"
        )

    if os.getenv("TRUSTCHAIN_REGISTRY_URL"):
        config.setdefault("registry", {})["url"] = os.getenv("TRUSTCHAIN_REGISTRY_URL")

    if os.getenv("REDIS_URL"):
        config.setdefault("registry", {})["url"] = os.getenv("REDIS_URL")

    if os.getenv("REDIS_HOST"):
        config.setdefault("registry", {})["redis_host"] = os.getenv("REDIS_HOST")

    if os.getenv("REDIS_PORT"):
        redis_port = os.getenv("REDIS_PORT")
        if redis_port:
            config.setdefault("registry", {})["redis_port"] = int(redis_port)

    if os.getenv("REDIS_PASSWORD"):
        config.setdefault("registry", {})["redis_password"] = os.getenv(
            "REDIS_PASSWORD"
        )

    if os.getenv("KAFKA_BOOTSTRAP_SERVERS"):
        config.setdefault("registry", {})["kafka_bootstrap_servers"] = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS"
        )

    # Security config
    if os.getenv("TRUSTCHAIN_NONCE_WINDOW"):
        nonce_window = os.getenv("TRUSTCHAIN_NONCE_WINDOW")
        if nonce_window:
            config.setdefault("security", {})["nonce_window"] = int(nonce_window)

    if os.getenv("TRUSTCHAIN_MAX_CHAIN_LENGTH"):
        max_chain_length = os.getenv("TRUSTCHAIN_MAX_CHAIN_LENGTH")
        if max_chain_length:
            config.setdefault("security", {})["max_chain_length"] = int(max_chain_length)

    # Monitoring config
    if os.getenv("TRUSTCHAIN_MONITORING_ENABLED"):
        monitoring_enabled = os.getenv("TRUSTCHAIN_MONITORING_ENABLED")
        if monitoring_enabled:
            enabled = monitoring_enabled.lower() in ("true", "1", "yes")
            config.setdefault("monitoring", {})["enabled"] = enabled

    if os.getenv("TRUSTCHAIN_METRICS_PORT"):
        metrics_port = os.getenv("TRUSTCHAIN_METRICS_PORT")
        if metrics_port:
            config.setdefault("monitoring", {})["metrics_port"] = int(metrics_port)

    if os.getenv("TRUSTCHAIN_DASHBOARD_PORT"):
        dashboard_port = os.getenv("TRUSTCHAIN_DASHBOARD_PORT")
        if dashboard_port:
            config.setdefault("monitoring", {})["dashboard_port"] = int(dashboard_port)

    if os.getenv("PROMETHEUS_ENDPOINT"):
        config.setdefault("monitoring", {})["prometheus_endpoint"] = os.getenv(
            "PROMETHEUS_ENDPOINT"
        )

    if os.getenv("GRAFANA_API_KEY"):
        config.setdefault("monitoring", {})["grafana_api_key"] = os.getenv(
            "GRAFANA_API_KEY"
        )

    # Global config
    if os.getenv("TRUSTCHAIN_DEBUG"):
        debug_env = os.getenv("TRUSTCHAIN_DEBUG")
        if debug_env:
            debug = debug_env.lower() in ("true", "1", "yes")
            config["debug"] = debug

    if os.getenv("TRUSTCHAIN_ENVIRONMENT"):
        config["environment"] = os.getenv("TRUSTCHAIN_ENVIRONMENT")

    return config


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> None:
    """Deep merge override dict into base dict."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def save_config(config: TrustChainConfig, path: Union[str, Path]) -> None:
    """Save configuration to YAML file."""
    path = Path(path)

    # Create directory if it doesn't exist
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(path, "w") as f:
            yaml.dump(config.to_dict(), f, default_flow_style=False, indent=2)
    except Exception as e:
        raise ConfigurationError(f"Failed to save config: {e}")


def get_default_config() -> TrustChainConfig:
    """Get default configuration."""
    return TrustChainConfig()


def create_config_template(path: Union[str, Path]) -> None:
    """Create a template configuration file."""
    config = get_default_config()
    save_config(config, path)
