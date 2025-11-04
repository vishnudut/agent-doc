"""
Context7 Client - Fetches up-to-date documentation for libraries
Using Context7 MCP JSON-RPC API
"""
import requests
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Context7Client:
    """Client for Context7 MCP API to fetch library documentation"""

    def __init__(self, api_key: str):
        self.base_url = "https://mcp.context7.com/mcp"
        self.headers = {
            "CONTEXT7_API_KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }

    def resolve_library(self, library_name: str) -> Optional[str]:
        """
        Resolve library name to Context7-compatible ID

        Args:
            library_name: Name of the library (e.g., "fastapi", "react", "langchain")

        Returns:
            Context7-compatible library ID (e.g., "/fastapi/fastapi") or None if not found
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "resolve-library-id",
                "arguments": {
                    "libraryName": library_name
                }
            },
            "id": 1
        }

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()

            # Extract library list from response
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                if isinstance(content, list) and len(content) > 0:
                    libraries_text = content[0].get("text", "")

                    # Parse the library list to find the best match
                    # Look for lines with "Context7-compatible library ID:"
                    import re
                    pattern = r"- Context7-compatible library ID: (\/[\w\-\/]+)"
                    matches = re.findall(pattern, libraries_text)

                    if matches:
                        # Return the first official library (usually has highest trust score)
                        # Prefer /org/repo format over /websites/ format
                        for lib_id in matches:
                            if not lib_id.startswith("/websites/"):
                                logger.info(f"Resolved '{library_name}' → '{lib_id}'")
                                return lib_id

                        # If only websites found, return first one
                        logger.info(f"Resolved '{library_name}' → '{matches[0]}'")
                        return matches[0]

            logger.warning(f"Could not resolve library: {library_name}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error resolving library '{library_name}': {e}")
            return None

    def get_docs(self, library_id: str, topic: Optional[str] = None, tokens: int = 3000) -> str:
        """
        Fetch documentation for a library using Context7-compatible library ID

        Args:
            library_id: Context7-compatible library ID (e.g., "/fastapi/fastapi")
            topic: Optional topic to focus the docs on (e.g., "streaming", "authentication")
            tokens: Max number of tokens to return (default 3000, min 1000)

        Returns:
            Documentation text as string
        """
        # Ensure minimum token count
        if tokens < 1000:
            tokens = 1000

        arguments = {
            "context7CompatibleLibraryID": library_id,
            "tokens": tokens
        }

        # Add topic if provided
        if topic:
            arguments["topic"] = topic

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "get-library-docs",
                "arguments": arguments
            },
            "id": 2
        }

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=self.headers,
                timeout=15
            )
            response.raise_for_status()

            result = response.json()

            # Extract documentation from response
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                if isinstance(content, list):
                    # Combine all text content
                    docs_text = "\n".join([
                        item.get("text", "")
                        for item in content
                        if item.get("text")
                    ])

                    if docs_text:
                        logger.info(f"Retrieved {len(docs_text)} chars of docs for '{library_id}'")
                        return docs_text

            logger.warning(f"No documentation found for library: {library_id}")
            return ""

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching docs for '{library_id}': {e}")
            return ""


# Quick test function
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("CONTEXT7_API_KEY")
    if not api_key:
        print("❌ CONTEXT7_API_KEY not found in environment")
        exit(1)

    print("Testing Context7 Client...")
    client = Context7Client(api_key)

    # Test 1: Resolve library
    print("\n1. Resolving 'fastapi'...")
    library_id = client.resolve_library("fastapi")
    print(f"   Result: {library_id}")

    # Test 2: Get docs
    if library_id:
        print(f"\n2. Fetching docs for '{library_id}'...")
        docs = client.get_docs(library_id, topic="streaming", tokens=1000)
        print(f"   Retrieved {len(docs)} characters")
        print(f"   Preview: {docs[:200]}...")


    print("\n✅ Context7 client test complete!")
