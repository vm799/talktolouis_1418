"""Shared pytest fixtures.

The seeded_db fixture provisions a fresh database per test (named with a
millisecond timestamp), seeds it with users/orders/knowledge documents,
and tears it down at the end. Tests that need MongoDB are skipped when
MONGODB_URI is not set.

To keep tests fast and to stay well under the Voyage AI free-tier rate
limit (3 RPM without a payment method), embed_text and embed_texts are
stubbed in this conftest with deterministic fake vectors derived from the
input text. Tests that specifically validate the Voyage client should
import voyageai directly. The MongoDB plumbing (vector index, $vectorSearch
pipeline, memory CRUD, scope filters) is identical regardless of whether
the vectors come from Voyage or a hash function.
"""

import hashlib
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

import pytest
from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

load_dotenv(".env.local")


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _unique_db_name() -> str:
    # Atlas caps database names at 38 bytes
    return f"lkmt_{int(datetime.now().timestamp() * 1000)}"


def _fake_vector(text: str, dimensions: int = 1024) -> list[float]:
    """Deterministic 1024-d unit vector seeded by the input text."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    raw = [(b - 128) / 128.0 for b in (digest * (dimensions // 32 + 1))[:dimensions]]
    norm = sum(x * x for x in raw) ** 0.5 or 1.0
    return [x / norm for x in raw]


@pytest.fixture(autouse=True)
def _stub_voyage(monkeypatch):
    """Replace embed_text/embed_texts with deterministic fake vectors.

    We patch in every module that does `from tools.embeddings import ...`
    because Python binds those names at import time.
    """
    async def fake_embed_text(text, *, input_type=None):
        return _fake_vector(text)

    async def fake_embed_texts(texts, *, input_type=None):
        return [_fake_vector(t) for t in texts]

    for module_path in ("tools.embeddings", "tools.memory", "agent"):
        monkeypatch.setattr(f"{module_path}.embed_text", fake_embed_text, raising=False)
        monkeypatch.setattr(f"{module_path}.embed_texts", fake_embed_texts, raising=False)


@pytest.fixture
async def test_db() -> AsyncGenerator[AsyncDatabase, None]:
    uri = os.getenv("MONGODB_URI")
    if not uri:
        pytest.skip("MONGODB_URI not set")
    client = AsyncMongoClient(uri)
    db_name = _unique_db_name()
    db = client[db_name]
    try:
        yield db
    finally:
        await client.drop_database(db_name)
        await client.close()


@pytest.fixture
async def seeded_db(test_db: AsyncDatabase) -> AsyncGenerator[AsyncDatabase, None]:
    await test_db.users.create_index("user_id", unique=True)
    await test_db.orders.create_index("order_id", unique=True)

    await test_db.users.insert_one(
        {
            "user_id": "user_1",
            "name": "Jordan",
            "email": "jordan@example.com",
            "preferences": {"language": "en"},
            "created_at": _now(),
        }
    )
    await test_db.orders.insert_one(
        {
            "user_id": "user_1",
            "order_id": "order_1001",
            "items": ["Widget A", "Widget B"],
            "total": 49.99,
            "status": "delivered",
            "created_at": _now(),
        }
    )

    knowledge_inputs = [
        {
            "title": "RAG pattern",
            "content": "Inject vector search results into chat context.",
        },
        {
            "title": "Memory pattern",
            "content": "Use tools to remember and recall details.",
        },
    ]
    await test_db.knowledge.insert_many(
        [
            {**k, "embedding": _fake_vector(k["content"]), "created_at": _now()}
            for k in knowledge_inputs
        ]
    )

    yield test_db
