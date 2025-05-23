import asyncio
import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import nacl.encoding
import nacl.signing
import rocksdb
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import ConsumerRecord
from confluent_kafka import DeserializingConsumer, SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer, AvroSerializer
from confluent_kafka.serialization import StringDeserializer, StringSerializer
from kafka import KafkaAdminClient, KafkaConsumer, KafkaProducer
from kafka.admin import ConfigResource, ConfigResourceType, NewTopic
from kafka.errors import KafkaError

# === АРХИТЕКТУРА ТОПИКОВ ===


class KafkaTopics(Enum):
    # Основные топики
    TOOL_REQUESTS = "ai.tool.requests"  # Запросы к инструментам
    TOOL_RESPONSES = "ai.tool.responses"  # Подписанные ответы
    SIGNATURE_EVENTS = "ai.signatures.events"  # События подписей

    # Trust Registry топики (compacted)
    TRUST_REGISTRY = "ai.trust.registry"  # Публичные ключи
    KEY_ROTATIONS = "ai.trust.key-rotations"  # Ротация ключей

    # Аудит и мониторинг
    VERIFICATION_LOGS = "ai.verification.logs"  # Логи проверок
    CHAIN_OF_TRUST = "ai.chain-of-trust"  # Цепочки вызовов

    # Replay protection (compacted, TTL)
    NONCE_REGISTRY = "ai.nonce.registry"  # Использованные nonce


# === СХЕМЫ AVRO ===

TOOL_REQUEST_SCHEMA = {
    "type": "record",
    "name": "ToolRequest",
    "namespace": "ai.tools",
    "fields": [
        {"name": "request_id", "type": "string"},
        {"name": "tool_id", "type": "string"},
        {"name": "query", "type": "string"},
        {
            "name": "context",
            "type": {
                "type": "record",
                "name": "RequestContext",
                "fields": [
                    {"name": "nonce", "type": "string"},
                    {"name": "timestamp", "type": "long"},
                    {"name": "caller_id", "type": "string"},
                    {"name": "session_id", "type": ["null", "string"], "default": None},
                    {
                        "name": "parent_request_id",
                        "type": ["null", "string"],
                        "default": None,
                    },
                ],
            },
        },
        {
            "name": "metadata",
            "type": ["null", {"type": "map", "values": "string"}],
            "default": None,
        },
    ],
}

SIGNED_RESPONSE_SCHEMA = {
    "type": "record",
    "name": "SignedResponse",
    "namespace": "ai.tools",
    "fields": [
        {"name": "request_id", "type": "string"},
        {"name": "tool_id", "type": "string"},
        {"name": "timestamp", "type": "long"},
        {"name": "result", "type": "string"},  # JSON string
        {
            "name": "signature",
            "type": {
                "type": "record",
                "name": "Signature",
                "fields": [
                    {"name": "algorithm", "type": "string"},
                    {"name": "public_key_id", "type": "string"},
                    {"name": "signature", "type": "string"},
                    {"name": "signed_hash", "type": "string"},
                ],
            },
        },
        {"name": "chain_proof", "type": ["null", "string"], "default": None},
    ],
}

# === KAFKA HEADERS ДЛЯ МЕТАДАННЫХ ===


class SignatureHeaders:
    """Стандартные headers для подписей"""

    SIGNATURE = "X-Signature"
    PUBLIC_KEY_ID = "X-Public-Key-Id"
    ALGORITHM = "X-Signature-Algorithm"
    TIMESTAMP = "X-Signature-Timestamp"
    CHAIN_ID = "X-Chain-Id"
    PARENT_HASH = "X-Parent-Hash"


# === PRODUCER С АВТОМАТИЧЕСКОЙ ПОДПИСЬЮ ===


class CryptoKafkaProducer:
    def __init__(
        self,
        bootstrap_servers: str,
        tool_id: str,
        private_key: bytes,
        schema_registry_url: str,
    ):
        self.tool_id = tool_id
        self.signing_key = nacl.signing.SigningKey(private_key)
        self.public_key_id = f"{tool_id}-key-001"

        # Schema Registry для Avro
        schema_registry_client = SchemaRegistryClient({"url": schema_registry_url})

        # Avro сериализатор
        self.avro_serializer = AvroSerializer(
            schema_registry_client, SIGNED_RESPONSE_SCHEMA
        )

        # Kafka producer с транзакциями
        self.producer = SerializingProducer(
            {
                "bootstrap.servers": bootstrap_servers,
                "key.serializer": StringSerializer("utf_8"),
                "value.serializer": self.avro_serializer,
                "transactional.id": f"crypto-producer-{tool_id}",
                "enable.idempotence": True,
                "acks": "all",
                "retries": 3,
                "max.in.flight.requests.per.connection": 1,
            }
        )

        # Инициализируем транзакции
        self.producer.init_transactions()

    def sign_message(self, message: dict) -> dict:
        """Подписывает сообщение"""
        # Создаём канонический JSON
        canonical_json = json.dumps(message, sort_keys=True, separators=(",", ":"))
        message_hash = hashlib.sha256(canonical_json.encode()).hexdigest()

        # Подписываем
        signature = self.signing_key.sign(
            message_hash.encode(), encoder=nacl.encoding.Base64Encoder
        ).signature.decode()

        return {
            "algorithm": "Ed25519",
            "public_key_id": self.public_key_id,
            "signature": signature,
            "signed_hash": f"sha256:{message_hash}",
        }

    def produce_signed_response(
        self,
        request_id: str,
        result: Any,
        chain_id: Optional[str] = None,
        parent_hash: Optional[str] = None,
    ):
        """Отправляет подписанный ответ в Kafka"""
        try:
            self.producer.begin_transaction()

            # Подготавливаем данные
            response_data = {
                "request_id": request_id,
                "tool_id": self.tool_id,
                "timestamp": int(time.time() * 1000),
                "result": json.dumps(result),
            }

            # Подписываем
            signature_info = self.sign_message(response_data)
            response_data["signature"] = signature_info

            # Headers для быстрой фильтрации
            headers = [
                (SignatureHeaders.PUBLIC_KEY_ID, self.public_key_id.encode()),
                (SignatureHeaders.ALGORITHM, b"Ed25519"),
                (SignatureHeaders.TIMESTAMP, str(response_data["timestamp"]).encode()),
            ]

            if chain_id:
                headers.append((SignatureHeaders.CHAIN_ID, chain_id.encode()))
                response_data["chain_proof"] = chain_id

            if parent_hash:
                headers.append((SignatureHeaders.PARENT_HASH, parent_hash.encode()))

            # Отправляем в основной топик
            self.producer.produce(
                topic=KafkaTopics.TOOL_RESPONSES.value,
                key=request_id,
                value=response_data,
                headers=headers,
            )

            # Дублируем в топик аудита
            self.producer.produce(
                topic=KafkaTopics.SIGNATURE_EVENTS.value,
                key=self.public_key_id,
                value={
                    "event_type": "signature_created",
                    "request_id": request_id,
                    "tool_id": self.tool_id,
                    "timestamp": response_data["timestamp"],
                    "signature_hash": signature_info["signed_hash"],
                },
            )

            self.producer.commit_transaction()

        except Exception as e:
            self.producer.abort_transaction()
            raise e


# === KAFKA STREAMS ДЛЯ ВЕРИФИКАЦИИ ===


class SignatureVerificationStream:
    """Kafka Streams приложение для проверки подписей"""

    def __init__(self, bootstrap_servers: str, state_dir: str = "/tmp/kafka-streams"):
        self.bootstrap_servers = bootstrap_servers
        self.state_dir = state_dir

        # RocksDB для локального стейта
        self.trust_store = rocksdb.DB(
            f"{state_dir}/trust-registry.db", rocksdb.Options(create_if_missing=True)
        )

        # Кэш проверенных подписей
        self.signature_cache = rocksdb.DB(
            f"{state_dir}/signature-cache.db", rocksdb.Options(create_if_missing=True)
        )

    async def start(self):
        """Запускает stream processing"""
        # Consumers
        response_consumer = AIOKafkaConsumer(
            KafkaTopics.TOOL_RESPONSES.value,
            bootstrap_servers=self.bootstrap_servers,
            group_id="signature-verifier",
            enable_auto_commit=False,
        )

        trust_consumer = AIOKafkaConsumer(
            KafkaTopics.TRUST_REGISTRY.value,
            bootstrap_servers=self.bootstrap_servers,
            group_id="trust-registry-sync",
            enable_auto_commit=True,
            auto_offset_reset="earliest",  # Читаем с начала
        )

        # Producer для результатов
        verification_producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers
        )

        await response_consumer.start()
        await trust_consumer.start()
        await verification_producer.start()

        try:
            # Запускаем параллельные задачи
            await asyncio.gather(
                self._sync_trust_registry(trust_consumer),
                self._verify_signatures(response_consumer, verification_producer),
            )
        finally:
            await response_consumer.stop()
            await trust_consumer.stop()
            await verification_producer.stop()

    async def _sync_trust_registry(self, consumer):
        """Синхронизирует реестр доверенных ключей"""
        async for msg in consumer:
            try:
                key_data = json.loads(msg.value)
                key_id = key_data["key_id"]

                # Сохраняем в RocksDB
                self.trust_store.put(key_id.encode(), json.dumps(key_data).encode())

                print(f"✅ Синхронизирован ключ: {key_id}")

            except Exception as e:
                print(f"❌ Ошибка синхронизации ключа: {e}")

    async def _verify_signatures(self, consumer, producer):
        """Проверяет подписи в потоке"""
        async for msg in consumer:
            try:
                # Проверяем в кэше
                cache_key = f"{msg.key}:{msg.timestamp}"
                cached = self.signature_cache.get(cache_key.encode())

                if cached:
                    verification_result = json.loads(cached)
                else:
                    # Выполняем проверку
                    verification_result = await self._verify_single_message(msg)

                    # Кэшируем результат
                    self.signature_cache.put(
                        cache_key.encode(), json.dumps(verification_result).encode()
                    )

                # Отправляем результат
                await producer.send(
                    KafkaTopics.VERIFICATION_LOGS.value,
                    key=msg.key,
                    value=json.dumps(verification_result).encode(),
                    headers=[
                        (
                            "verified",
                            b"true" if verification_result["valid"] else b"false",
                        ),
                        ("tool_id", verification_result["tool_id"].encode()),
                    ],
                )

                # Коммитим оффсет после успешной обработки
                await consumer.commit()

            except Exception as e:
                print(f"❌ Ошибка верификации: {e}")

    async def _verify_single_message(self, msg: ConsumerRecord) -> dict:
        """Проверяет одно сообщение"""
        response = json.loads(msg.value)
        signature_info = response["signature"]

        # Получаем публичный ключ
        key_data = self.trust_store.get(signature_info["public_key_id"].encode())
        if not key_data:
            return {
                "valid": False,
                "error": "Unknown public key",
                "request_id": response["request_id"],
                "tool_id": response["tool_id"],
            }

        key_info = json.loads(key_data)

        try:
            # Проверяем подпись
            verify_key = nacl.signing.VerifyKey(
                key_info["public_key"], encoder=nacl.encoding.Base64Encoder
            )

            # Восстанавливаем подписанные данные
            data_to_verify = {
                k: v
                for k, v in response.items()
                if k not in ["signature", "chain_proof"]
            }
            canonical_json = json.dumps(
                data_to_verify, sort_keys=True, separators=(",", ":")
            )
            expected_hash = hashlib.sha256(canonical_json.encode()).hexdigest()

            # Проверяем хэш
            actual_hash = signature_info["signed_hash"].split(":")[1]
            if expected_hash != actual_hash:
                raise ValueError("Hash mismatch")

            # Проверяем подпись
            verify_key.verify(
                expected_hash.encode(),
                signature_info["signature"].encode(),
                encoder=nacl.encoding.Base64Encoder,
            )

            return {
                "valid": True,
                "request_id": response["request_id"],
                "tool_id": response["tool_id"],
                "verified_at": time.time(),
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "request_id": response["request_id"],
                "tool_id": response["tool_id"],
            }


# === CHAIN OF TRUST В KAFKA ===


class KafkaChainOfTrust:
    """Управление цепочками вызовов через Kafka"""

    def __init__(self, producer: CryptoKafkaProducer):
        self.producer = producer
        self.active_chains = {}

    def start_chain(self, initial_request_id: str) -> str:
        """Начинает новую цепочку"""
        chain_id = str(uuid.uuid4())

        self.active_chains[chain_id] = {
            "started_at": time.time(),
            "steps": [
                {
                    "request_id": initial_request_id,
                    "parent_hash": None,
                    "timestamp": time.time(),
                }
            ],
        }

        # Публикуем начало цепочки
        self.producer.producer.produce(
            topic=KafkaTopics.CHAIN_OF_TRUST.value,
            key=chain_id,
            value={
                "chain_id": chain_id,
                "event": "chain_started",
                "initial_request_id": initial_request_id,
                "timestamp": int(time.time() * 1000),
            },
        )

        return chain_id

    def add_to_chain(
        self, chain_id: str, request_id: str, previous_response_hash: str
    ) -> str:
        """Добавляет шаг в цепочку"""
        if chain_id not in self.active_chains:
            raise ValueError(f"Unknown chain: {chain_id}")

        # Создаём связь с предыдущим шагом
        link_hash = hashlib.sha256(
            f"{previous_response_hash}:{request_id}".encode()
        ).hexdigest()

        step = {
            "request_id": request_id,
            "parent_hash": previous_response_hash,
            "link_hash": link_hash,
            "timestamp": time.time(),
        }

        self.active_chains[chain_id]["steps"].append(step)

        # Публикуем событие
        self.producer.producer.produce(
            topic=KafkaTopics.CHAIN_OF_TRUST.value,
            key=chain_id,
            value={
                "chain_id": chain_id,
                "event": "step_added",
                "step_number": len(self.active_chains[chain_id]["steps"]) - 1,
                "request_id": request_id,
                "parent_hash": previous_response_hash,
                "link_hash": link_hash,
                "timestamp": int(time.time() * 1000),
            },
        )

        return link_hash


# === REPLAY PROTECTION ЧЕРЕЗ KAFKA ===


class KafkaNonceRegistry:
    """Распределённый реестр nonce через Kafka"""

    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers

        # Создаём compacted topic для nonce
        admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)

        topic = NewTopic(
            name=KafkaTopics.NONCE_REGISTRY.value,
            num_partitions=10,
            replication_factor=3,
            topic_configs={
                "cleanup.policy": "compact",
                "retention.ms": "3600000",  # 1 час
                "segment.ms": "60000",  # 1 минута
                "min.cleanable.dirty.ratio": "0.1",
            },
        )

        try:
            admin.create_topics([topic])
        except:
            pass  # Топик уже существует

    async def check_and_register_nonce(self, nonce: str, request_id: str) -> bool:
        """Проверяет и регистрирует nonce атомарно"""
        key = f"{nonce}:{request_id}"

        # Producer с exactly-once семантикой
        producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            transactional_id=f"nonce-registry-{uuid.uuid4()}",
            enable_idempotence=True,
        )

        await producer.start()

        try:
            # Начинаем транзакцию
            await producer.begin_transaction()

            # Проверяем существование через consumer
            consumer = AIOKafkaConsumer(
                KafkaTopics.NONCE_REGISTRY.value,
                bootstrap_servers=self.bootstrap_servers,
                group_id=None,  # Не используем consumer group
                auto_offset_reset="earliest",
                enable_auto_commit=False,
            )

            await consumer.start()

            # Ищем nonce
            found = False
            consumer.seek_to_beginning()

            async for msg in consumer:
                if msg.key and msg.key.decode() == key:
                    found = True
                    break

                # Проверяем только последние сообщения
                if msg.timestamp > (time.time() - 3600) * 1000:
                    continue
                else:
                    break

            await consumer.stop()

            if found:
                await producer.abort_transaction()
                return False

            # Регистрируем nonce
            await producer.send(
                KafkaTopics.NONCE_REGISTRY.value,
                key=key.encode(),
                value=json.dumps(
                    {"nonce": nonce, "request_id": request_id, "timestamp": time.time()}
                ).encode(),
            )

            await producer.commit_transaction()
            return True

        finally:
            await producer.stop()


# === TRUST REGISTRY В KAFKA ===


class KafkaTrustRegistry:
    """Распределённый реестр ключей через Kafka"""

    def __init__(self, bootstrap_servers: str):
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode(),
        )

        # Создаём compacted topic
        admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)

        topic = NewTopic(
            name=KafkaTopics.TRUST_REGISTRY.value,
            num_partitions=1,  # Один партишн для упорядоченности
            replication_factor=3,
            topic_configs={
                "cleanup.policy": "compact",
                "retention.ms": "-1",  # Бесконечное хранение
                "segment.ms": "3600000",  # 1 час
            },
        )

        try:
            admin.create_topics([topic])
        except:
            pass

    def publish_key(self, key_metadata: dict):
        """Публикует публичный ключ"""
        key_id = key_metadata["key_id"]

        # Основная запись
        self.producer.send(
            KafkaTopics.TRUST_REGISTRY.value, key=key_id, value=key_metadata
        )

        # Событие для аудита
        self.producer.send(
            KafkaTopics.KEY_ROTATIONS.value,
            key=key_metadata["tool_id"],
            value={
                "event": "key_published",
                "key_id": key_id,
                "tool_id": key_metadata["tool_id"],
                "valid_from": key_metadata["valid_from"],
                "valid_until": key_metadata["valid_until"],
                "timestamp": time.time(),
            },
        )

        self.producer.flush()

    def revoke_key(self, key_id: str, reason: str):
        """Отзывает ключ"""
        # Tombstone для удаления из compacted topic
        self.producer.send(
            KafkaTopics.TRUST_REGISTRY.value, key=key_id, value=None  # Tombstone
        )

        # Событие отзыва
        self.producer.send(
            KafkaTopics.KEY_ROTATIONS.value,
            key=key_id,
            value={
                "event": "key_revoked",
                "key_id": key_id,
                "reason": reason,
                "timestamp": time.time(),
            },
        )


# === ИНТЕГРАЦИЯ С AI АГЕНТОМ ===


class KafkaAIAgent:
    """AI агент с полной интеграцией Kafka"""

    def __init__(self, bootstrap_servers: str, agent_id: str):
        self.agent_id = agent_id
        self.bootstrap_servers = bootstrap_servers

        # Consumer для запросов
        self.request_consumer = KafkaConsumer(
            KafkaTopics.TOOL_REQUESTS.value,
            bootstrap_servers=bootstrap_servers,
            group_id=f"ai-agent-{agent_id}",
            value_deserializer=lambda m: json.loads(m.decode()),
        )

        # Инструменты
        self.tools = {}

    async def process_requests(self):
        """Обрабатывает входящие запросы"""
        for message in self.request_consumer:
            request = message.value

            # Создаём цепочку для сложных запросов
            if request.get("metadata", {}).get("multi_step"):
                chain = KafkaChainOfTrust(self.tools[request["tool_id"]])
                chain_id = chain.start_chain(request["request_id"])

                # Выполняем план
                await self._execute_chain(request, chain_id)
            else:
                # Простой запрос
                tool = self.tools[request["tool_id"]]
                tool.produce_signed_response(
                    request["request_id"], self._execute_tool(request)
                )


# === МОНИТОРИНГ И АЛЕРТЫ ===


class KafkaSignatureMonitor:
    """Мониторинг подписей и аномалий"""

    def __init__(self, bootstrap_servers: str):
        self.consumer = KafkaConsumer(
            KafkaTopics.VERIFICATION_LOGS.value,
            bootstrap_servers=bootstrap_servers,
            group_id="signature-monitor",
            value_deserializer=lambda m: json.loads(m.decode()),
        )

        self.metrics = {
            "total_verifications": 0,
            "failed_verifications": 0,
            "tools": {},
        }

    def monitor(self):
        """Мониторит поток верификаций"""
        for message in self.consumer:
            result = message.value

            self.metrics["total_verifications"] += 1

            if not result["valid"]:
                self.metrics["failed_verifications"] += 1

                # Алерт при превышении порога
                failure_rate = (
                    self.metrics["failed_verifications"]
                    / self.metrics["total_verifications"]
                )

                if failure_rate > 0.01:  # 1% порог
                    self._send_alert(f"High signature failure rate: {failure_rate:.2%}")

            # Метрики по инструментам
            tool_id = result["tool_id"]
            if tool_id not in self.metrics["tools"]:
                self.metrics["tools"][tool_id] = {"total": 0, "failed": 0}

            self.metrics["tools"][tool_id]["total"] += 1
            if not result["valid"]:
                self.metrics["tools"][tool_id]["failed"] += 1


# === ПРИМЕР ИСПОЛЬЗОВАНИЯ ===


async def example_kafka_setup():
    # Конфигурация
    BOOTSTRAP_SERVERS = "localhost:9092"
    SCHEMA_REGISTRY_URL = "http://localhost:8081"

    # 1. Создаём Trust Registry
    trust_registry = KafkaTrustRegistry(BOOTSTRAP_SERVERS)

    # Публикуем ключи инструментов
    trust_registry.publish_key(
        {
            "key_id": "weather-api-key-001",
            "tool_id": "weather_api_v1",
            "algorithm": "Ed25519",
            "public_key": "MCowBQYDK2VwAyEA...",
            "valid_from": "2025-01-01T00:00:00Z",
            "valid_until": "2026-01-01T00:00:00Z",
        }
    )

    # 2. Создаём защищённый producer
    weather_tool = CryptoKafkaProducer(
        BOOTSTRAP_SERVERS, "weather_api_v1", private_key_bytes, SCHEMA_REGISTRY_URL
    )

    # 3. Запускаем верификатор
    verifier = SignatureVerificationStream(BOOTSTRAP_SERVERS)
    asyncio.create_task(verifier.start())

    # 4. Создаём nonce registry
    nonce_registry = KafkaNonceRegistry(BOOTSTRAP_SERVERS)

    # 5. Обрабатываем запрос
    request_id = str(uuid.uuid4())
    nonce = str(uuid.uuid4())

    # Проверяем nonce
    if await nonce_registry.check_and_register_nonce(nonce, request_id):
        # Выполняем и подписываем
        weather_tool.produce_signed_response(
            request_id, {"temperature": 15, "humidity": 60}
        )

    # 6. Мониторинг
    monitor = KafkaSignatureMonitor(BOOTSTRAP_SERVERS)
    asyncio.create_task(monitor.monitor())

    print("✅ Kafka crypto-tools запущены!")


if __name__ == "__main__":
    asyncio.run(example_kafka_setup())
