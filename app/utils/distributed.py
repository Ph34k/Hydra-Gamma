from typing import Any, Optional, Dict
import hashlib
import json

class Cache:
    """
    A simple in-memory cache implementation to mock Redis Semantic Cache.
    Ref: Chapter 13.4 of the Technical Bible.
    """

    _store: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        return self._store.get(key)

    def set(self, key: str, value: Any, ttl: int = 3600):
        # TTL ignored for this mock implementation
        self._store[key] = value

    def semantic_get(self, query: str) -> Optional[str]:
        """Mock semantic search."""
        # Simple hash for now
        key = hashlib.md5(query.encode()).hexdigest()
        return self.get(key)

    def semantic_set(self, query: str, response: str):
        key = hashlib.md5(query.encode()).hexdigest()
        self.set(key, response)

class Consensus:
    """
    A mock consensus mechanism for distributed state.
    Ref: Chapter 14.6 of the Technical Bible.
    """

    async def propose_state_update(self, agent_id: str, new_state_hash: str) -> bool:
        """
        Simulate a consensus proposal.
        In a real distributed system, this would use Raft/Paxos.
        """
        # Always accept in single-node mode
        return True

# Global instances
cache = Cache()
consensus = Consensus()
