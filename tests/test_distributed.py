import pytest
import hashlib
from app.utils.distributed import Cache, Consensus

class TestCache:
    def test_get_set(self):
        cache = Cache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.get("nonexistent") is None

    def test_semantic_search(self):
        cache = Cache()
        query = "What is the capital of France?"
        response = "Paris"

        # Expected hash key logic from the implementation
        key = hashlib.md5(query.encode()).hexdigest()

        cache.semantic_set(query, response)

        # Verify direct get
        assert cache.get(key) == response

        # Verify semantic get
        assert cache.semantic_get(query) == response

class TestConsensus:
    @pytest.mark.asyncio
    async def test_propose_state_update(self):
        consensus = Consensus()
        result = await consensus.propose_state_update("agent1", "some_hash")
        assert result is True
