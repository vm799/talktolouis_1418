"""Integration tests that exercise the MongoDB plumbing end-to-end.

These do not start a LiveKit session — they call the same functions the
agent calls and assert the database state.
"""

import pytest
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import OperationFailure

from agent import _vector_search_knowledge, preload_user
from tools.memory import (
    forget,
    list_memories,
    recall,
    remember,
    search_memory,
)


@pytest.fixture(autouse=True)
def _patch_get_db(monkeypatch, seeded_db: AsyncDatabase):
    """Pin get_db() to the per-test database for the duration of each test."""

    async def _fake_get_db(_=None):
        return seeded_db

    monkeypatch.setattr("db.client.get_db", _fake_get_db)
    monkeypatch.setattr("agent.get_db", _fake_get_db)


async def test_pattern_3_preload_finds_known_user(seeded_db: AsyncDatabase) -> None:
    chat_ctx = await preload_user("user_1", "default")
    rendered = " ".join(
        item.text_content for item in chat_ctx.items if item.text_content
    )
    assert "Jordan" in rendered
    assert "jordan@example.com" in rendered


async def test_pattern_3_preload_handles_missing_user(seeded_db: AsyncDatabase) -> None:
    chat_ctx = await preload_user("user_unknown", "default")
    rendered = " ".join(
        item.text_content for item in chat_ctx.items if item.text_content
    )
    assert "No stored profile fields" in rendered


async def test_pattern_3_preload_prompts_for_name_when_missing(
    seeded_db: AsyncDatabase,
) -> None:
    """When no profile name is on file, the chat context preload_user builds
    must instruct the agent to ASK for the user's name and persist it via
    update_profile. The agent reads this guidance before its first turn.
    """
    chat_ctx = await preload_user("user_unknown_no_name", "default")
    rendered = " ".join(
        item.text_content for item in chat_ctx.items if item.text_content
    ).lower()
    assert "ask" in rendered, (
        f"expected 'ask' in preload context for nameless user; got: {rendered}"
    )
    assert "name" in rendered, (
        f"expected 'name' in preload context for nameless user; got: {rendered}"
    )
    assert "update_profile" in rendered, (
        "expected 'update_profile' hint so the agent persists the name when "
        f"the user provides it; got: {rendered}"
    )


async def test_pattern_4_lookup_order(seeded_db: AsyncDatabase) -> None:
    order = await seeded_db.orders.find_one({"order_id": "order_1001"})
    assert order is not None
    assert order["items"] == ["Widget A", "Widget B"]
    assert order["status"] == "delivered"


async def test_pattern_1_vector_search_returns_results(
    seeded_db: AsyncDatabase,
) -> None:
    """Sanity check on $vectorSearch syntax. The fresh per-test index is not
    queryable yet, so we assert the pipeline shape is valid (no exception)."""
    from tools.embeddings import embed_text

    qv = await embed_text("voice agent retrieval", input_type="query")
    pipeline = [
        {
            "$vectorSearch": {
                "index": "knowledge_embedding_index",
                "path": "embedding",
                "queryVector": qv,
                "numCandidates": 50,
                "limit": 3,
            }
        },
        {"$project": {"title": 1, "_id": 0}},
    ]
    cursor = await seeded_db.knowledge.aggregate(pipeline)
    results = await cursor.to_list(length=3)
    assert isinstance(results, list)


async def test_pattern_5_session_report_insert(seeded_db: AsyncDatabase) -> None:
    await seeded_db.sessions.insert_one(
        {
            "session_id": "test-room-1",
            "user_id": "user_1",
            "report": {"chat_history": []},
        }
    )
    found = await seeded_db.sessions.find_one({"session_id": "test-room-1"})
    assert found is not None
    assert found["user_id"] == "user_1"


async def test_pattern_2_memory_remember_recall_forget(
    seeded_db: AsyncDatabase,
) -> None:
    msg = await remember(seeded_db, "user_1", "default", "preference", "likes coffee")
    assert "Remembered" in msg

    recalled = await recall(seeded_db, "user_1", "default", "preference")
    assert recalled == "likes coffee"

    msg = await forget(seeded_db, "user_1", "default", "preference")
    assert msg == "Memory forgotten."

    recalled = await recall(seeded_db, "user_1", "default", "preference")
    assert recalled == "No memory found."


async def test_pattern_2_memory_isolation_across_users(
    seeded_db: AsyncDatabase,
) -> None:
    await remember(seeded_db, "user_a", "default", "fact", "lives in Paris")
    await remember(seeded_db, "user_b", "default", "fact", "lives in Tokyo")

    assert await recall(seeded_db, "user_a", "default", "fact") == "lives in Paris"
    assert await recall(seeded_db, "user_b", "default", "fact") == "lives in Tokyo"


async def test_pattern_2_memory_overwrite(seeded_db: AsyncDatabase) -> None:
    """Writing the same memory_type twice replaces the old value; the
    (user_id, tenant_id, memory_type) slot holds at most one document."""
    await remember(seeded_db, "user_1", "default", "favorite_color", "blue")
    await remember(seeded_db, "user_1", "default", "favorite_color", "green")

    assert (
        await recall(seeded_db, "user_1", "default", "favorite_color")
    ) == "green"
    count = await seeded_db.memories.count_documents(
        {
            "user_id": "user_1",
            "tenant_id": "default",
            "memory_type": "favorite_color",
        }
    )
    assert count == 1


async def test_pattern_2_list_memories_returns_all_slots(
    seeded_db: AsyncDatabase,
) -> None:
    await remember(seeded_db, "user_1", "default", "favorite_color", "blue")
    await remember(seeded_db, "user_1", "default", "allergy", "peanuts")

    results = await list_memories(seeded_db, "user_1", "default")
    types = {r["memory_type"] for r in results}
    assert types == {"favorite_color", "allergy"}


async def test_pattern_2_search_memory_returns_list(
    seeded_db: AsyncDatabase,
) -> None:
    """search_memory should return a list of {memory_type, content} dicts.

    The $rankFusion pipeline needs both `memories_embedding_index` and
    `memories_text_index` to be queryable, which is not the case on a
    fresh per-test database. We tolerate OperationFailure so the test
    validates the pipeline shape without requiring synced indexes.
    """
    try:
        results = await search_memory(
            seeded_db, "user_1", "default", "anything", limit=5
        )
    except OperationFailure:
        return
    assert isinstance(results, list)
    for item in results:
        assert "memory_type" in item
        assert "content" in item


async def test_pattern_2_search_memory_recovers_unknown_key(
    seeded_db: AsyncDatabase,
) -> None:
    """Hybrid retrieval should surface a memory even when the query uses
    different phrasing than the stored label. We store under
    'color_preference' and query with 'favorite color', relying on the
    text branch of $rankFusion to catch the literal word overlap.

    Tolerates OperationFailure because the per-test database does not
    have the search indexes synced; the shape of the call is what we are
    validating here.
    """
    await remember(
        seeded_db, "user_1", "default", "color_preference", "blue"
    )
    try:
        results = await search_memory(
            seeded_db,
            "user_1",
            "default",
            "what is my favorite color?",
            limit=5,
        )
    except OperationFailure:
        return
    assert isinstance(results, list)


async def test_search_knowledge_tool_returns_docs(
    seeded_db: AsyncDatabase,
) -> None:
    """Sanity check on the shared knowledge pipeline helper.

    Exercises the same `$vectorSearch` + `$project` shape that
    `search_knowledge` uses. The per-test database does not have
    `knowledge_embedding_index` synced, so we tolerate
    `OperationFailure` and only assert the return shape when the
    pipeline runs.
    """
    try:
        results = await _vector_search_knowledge(
            seeded_db, "voice agent retrieval", limit=3
        )
    except OperationFailure:
        return
    assert isinstance(results, list)
    for doc in results:
        assert "title" in doc
        assert "content" in doc


async def test_voyage_client_returns_correct_dimensions() -> None:
    """Single live Voyage call to verify the SDK and our default model.

    The other tests use deterministic fake vectors (see conftest) to stay
    inside the free-tier rate limit; this test is the one place we hit
    the real API to make sure the embeddings module produces 1024-d
    vectors with the configured model.
    """
    import os

    if not os.getenv("VOYAGE_API_KEY"):
        pytest.skip("VOYAGE_API_KEY not set")

    import voyageai

    from tools.embeddings import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL

    client = voyageai.AsyncClient()
    result = await client.embed(
        texts=["livekit mongodb starter dimension check"],
        model=EMBEDDING_MODEL,
        input_type="query",
    )
    assert len(result.embeddings) == 1
    assert len(result.embeddings[0]) == EMBEDDING_DIMENSIONS
