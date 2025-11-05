"""
MemMachine Client - Store and retrieve documentation retrieval context
Integrates with locally running MemMachine instance for memory persistence
"""
import requests
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemMachineClient:
    """Client for MemMachine API to store and retrieve documentation context"""

    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.headers = {
            "Content-Type": "application/json"
        }

    def _create_session_data(self, user_id: str) -> Dict[str, Any]:
        """Create standardized session data structure"""
        return {
            "group_id": f"doc_agent_{user_id}",
            "agent_id": ["doc_injection_agent"],
            "user_id": [user_id],
            "session_id": f"doc_session_{user_id}"
        }

    def search_similar_queries(self, query: str, user_id: str, limit: int = 3) -> Dict[str, Any]:
        """
        Search for similar documentation queries in memory

        Args:
            query: User's current query
            user_id: User identifier
            limit: Maximum number of results to return

        Returns:
            Dictionary with episodic_memory and profile_memory
        """
        session_data = self._create_session_data(user_id)
        search_payload = {
            "session": session_data,
            "query": query,
            "limit": limit,
            "filter": {}
        }

        try:
            response = requests.post(
                f"{self.base_url}/v1/memories/search",
                json=search_payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            content = result.get("content", {})

            episodic_memory = content.get("episodic_memory", [])
            profile_memory = content.get("profile_memory", [])

            logger.info(f"Found {len(episodic_memory)} similar queries for: {query}")

            return {
                "episodic_memory": episodic_memory,
                "profile_memory": profile_memory,
                "has_context": bool(episodic_memory or profile_memory)
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching similar queries: {e}")
            return {
                "episodic_memory": [],
                "profile_memory": [],
                "has_context": False
            }

    def store_retrieval_session(self,
                              user_query: str,
                              library_name: str,
                              library_id: str,
                              retrieved_docs: str,
                              context7_success: bool,
                              user_id: str,
                              metadata: Optional[Dict] = None) -> bool:
        """
        Store a documentation retrieval session in memory

        Args:
            user_query: Original user query
            library_name: Library name (e.g., "fastapi")
            library_id: Context7 library ID (e.g., "/fastapi/fastapi")
            retrieved_docs: The documentation text retrieved
            context7_success: Whether Context7 retrieval was successful
            user_id: User identifier
            metadata: Optional additional metadata

        Returns:
            True if stored successfully, False otherwise
        """
        session_data = self._create_session_data(user_id)

        # Create structured content for the memory
        episode_content = {
            "type": "doc_retrieval",
            "user_query": user_query,
            "library_name": library_name,
            "library_id": library_id,
            "docs_preview": retrieved_docs[:500] + "..." if len(retrieved_docs) > 500 else retrieved_docs,
            "docs_length": len(retrieved_docs),
            "success": context7_success,
            "timestamp": datetime.now().isoformat()
        }

        # Add optional metadata
        episode_metadata = {
            "library_name": library_name,
            "library_id": library_id,
            "success": context7_success,
            "docs_length": len(retrieved_docs),
            "timestamp": datetime.now().isoformat(),
            "type": "doc_retrieval"
        }

        if metadata:
            episode_metadata.update(metadata)

        memory_payload = {
            "session": session_data,
            "producer": user_id,
            "produced_for": "doc_injection_agent",
            "episode_content": str(episode_content),  # MemMachine expects string content
            "episode_type": "doc_retrieval",
            "metadata": episode_metadata
        }

        try:
            response = requests.post(
                f"{self.base_url}/v1/memories",
                json=memory_payload,
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()

            logger.info(f"Stored retrieval session for library '{library_name}' and query: {user_query[:100]}")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Error storing retrieval session: {e}")
            return False

    def get_library_context(self, library_name: str, user_id: str, limit: int = 5) -> List[Dict]:
        """
        Get past successful retrievals for a specific library

        Args:
            library_name: Name of the library
            user_id: User identifier
            limit: Maximum number of results

        Returns:
            List of past successful retrievals for this library
        """
        session_data = self._create_session_data(user_id)
        search_payload = {
            "session": session_data,
            "query": library_name,
            "limit": limit,
            "filter": {
                "library_name": library_name
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/v1/memories/search",
                json=search_payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            content = result.get("content", {})
            episodic_memory = content.get("episodic_memory", [])

            logger.info(f"Found {len(episodic_memory)} past interactions with {library_name}")
            return episodic_memory

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting library context for {library_name}: {e}")
            return []

    def build_context_prompt(self,
                           episodic_memory: List[Dict],
                           profile_memory: List[Dict],
                           current_query: str) -> str:
        """
        Build a context prompt from memory for the LLM

        Args:
            episodic_memory: Past similar queries and retrievals
            profile_memory: User profile/preferences
            current_query: Current user query

        Returns:
            Formatted context string for the LLM
        """
        context_parts = []

        if profile_memory:
            context_parts.append("=== USER PREFERENCES ===")
            for profile in profile_memory:
                context_parts.append(str(profile))

        if episodic_memory:
            context_parts.append("=== PAST SIMILAR QUERIES ===")
            for i, episode in enumerate(episodic_memory[:3]):  # Limit to top 3
                context_parts.append(f"Past Query {i+1}: {episode}")

        if context_parts:
            context_parts.append("=== CURRENT QUERY ===")
            context_parts.append(f"Current query: {current_query}")
            context_parts.append("\nBased on the above context, provide relevant documentation.")

            return "\n".join(context_parts)

        return f"Query: {current_query}"

    def health_check(self) -> bool:
        """
        Check if MemMachine service is healthy

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )

            if response.status_code == 200:
                health_data = response.json()
                logger.info(f"MemMachine health: {health_data}")
                return health_data.get("status") == "healthy"

            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"MemMachine health check failed: {e}")
            return False


# Quick test function
if __name__ == "__main__":
    print("Testing MemMachine Client...")

    client = MemMachineClient()

    # Test 1: Health check
    print("\n1. Health check...")
    if client.health_check():
        print("   ✅ MemMachine is healthy")
    else:
        print("   ❌ MemMachine health check failed")
        exit(1)

    # Test 2: Store a test retrieval
    print("\n2. Storing test retrieval...")
    success = client.store_retrieval_session(
        user_query="How to create FastAPI routes?",
        library_name="fastapi",
        library_id="/fastapi/fastapi",
        retrieved_docs="FastAPI allows you to create routes using @app.get() decorator...",
        context7_success=True,
        user_id="test_user"
    )
    print(f"   Store result: {'✅ Success' if success else '❌ Failed'}")

    # Test 3: Search for similar queries
    print("\n3. Searching for similar queries...")
    results = client.search_similar_queries("FastAPI routing", "test_user")
    print(f"   Found context: {'✅ Yes' if results['has_context'] else '❌ No'}")
    if results['has_context']:
        print(f"   Episodic memories: {len(results['episodic_memory'])}")

    # Test 4: Build context prompt
    print("\n4. Building context prompt...")
    context = client.build_context_prompt(
        results['episodic_memory'],
        results['profile_memory'],
        "How to handle FastAPI dependencies?"
    )
    print(f"   Context length: {len(context)} characters")
    print(f"   Preview: {context[:200]}...")

    print("\n✅ MemMachine client test complete!")
