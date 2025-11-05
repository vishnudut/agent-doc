# """
# Context7 Client - Fetches up-to-date documentation for libraries
# Using Context7 MCP JSON-RPC API
# """
# import requests
# from typing import Optional
# import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)


# class Context7Client:
#     """Client for Context7 MCP API to fetch library documentation"""

#     def __init__(self, api_key: str):
#         self.base_url = "https://mcp.context7.com/mcp"
#         self.headers = {
#             "CONTEXT7_API_KEY": api_key,
#             "Content-Type": "application/json",
#             "Accept": "application/json, text/event-stream"
#         }

#     def resolve_library(self, library_name: str) -> Optional[str]:
#         """
#         Resolve library name to Context7-compatible ID

#         Args:
#             library_name: Name of the library (e.g., "fastapi", "react", "langchain")

#         Returns:
#             Context7-compatible library ID (e.g., "/fastapi/fastapi") or None if not found
#         """
#         payload = {
#             "jsonrpc": "2.0",
#             "method": "tools/call",
#             "params": {
#                 "name": "resolve-library-id",
#                 "arguments": {
#                     "libraryName": library_name
#                 }
#             },
#             "id": 1
#         }

#         try:
#             response = requests.post(
#                 self.base_url,
#                 json=payload,
#                 headers=self.headers,
#                 timeout=10
#             )
#             response.raise_for_status()

#             result = response.json()

#             # Extract library list from response
#             if "result" in result and "content" in result["result"]:
#                 content = result["result"]["content"]
#                 if isinstance(content, list) and len(content) > 0:
#                     libraries_text = content[0].get("text", "")

#                     # Parse the library list to find the best match
#                     # Look for lines with "Context7-compatible library ID:"
#                     import re
#                     pattern = r"- Context7-compatible library ID: (\/[\w\-\/]+)"
#                     matches = re.findall(pattern, libraries_text)

#                     if matches:
#                         # Return the first official library (usually has highest trust score)
#                         # Prefer /org/repo format over /websites/ format
#                         for lib_id in matches:
#                             if not lib_id.startswith("/websites/"):
#                                 logger.info(f"Resolved '{library_name}' → '{lib_id}'")
#                                 return lib_id

#                         # If only websites found, return first one
#                         logger.info(f"Resolved '{library_name}' → '{matches[0]}'")
#                         return matches[0]

#             logger.warning(f"Could not resolve library: {library_name}")
#             return None

#         except requests.exceptions.RequestException as e:
#             logger.error(f"Error resolving library '{library_name}': {e}")
#             return None

#     def get_docs(self, library_id: str, topic: Optional[str] = None, tokens: int = 3000) -> str:
#         """
#         Fetch documentation for a library using Context7-compatible library ID

#         Args:
#             library_id: Context7-compatible library ID (e.g., "/fastapi/fastapi")
#             topic: Optional topic to focus the docs on (e.g., "streaming", "authentication")
#             tokens: Max number of tokens to return (default 3000, min 1000)

#         Returns:
#             Documentation text as string
#         """
#         # Ensure minimum token count
#         if tokens < 1000:
#             tokens = 1000

#         arguments = {
#             "context7CompatibleLibraryID": library_id,
#             "tokens": tokens
#         }

#         # Add topic if provided
#         if topic:
#             arguments["topic"] = topic

#         payload = {
#             "jsonrpc": "2.0",
#             "method": "tools/call",
#             "params": {
#                 "name": "get-library-docs",
#                 "arguments": arguments
#             },
#             "id": 2
#         }

#         try:
#             response = requests.post(
#                 self.base_url,
#                 json=payload,
#                 headers=self.headers,
#                 timeout=15
#             )
#             response.raise_for_status()

#             result = response.json()

#             # Extract documentation from response
#             if "result" in result and "content" in result["result"]:
#                 content = result["result"]["content"]
#                 if isinstance(content, list):
#                     # Combine all text content
#                     docs_text = "\n".join([
#                         item.get("text", "")
#                         for item in content
#                         if item.get("text")
#                     ])

#                     if docs_text:
#                         logger.info(f"Retrieved {len(docs_text)} chars of docs for '{library_id}'")
#                         return docs_text

#             logger.warning(f"No documentation found for library: {library_id}")
#             return ""

#         except requests.exceptions.RequestException as e:
#             logger.error(f"Error fetching docs for '{library_id}': {e}")
#             return ""


# # Quick test function
# if __name__ == "__main__":
#     import os
#     from dotenv import load_dotenv

#     load_dotenv()

#     api_key = os.getenv("CONTEXT7_API_KEY")
#     if not api_key:
#         print("❌ CONTEXT7_API_KEY not found in environment")
#         exit(1)

#     print("Testing Context7 Client...")
#     client = Context7Client(api_key)

#     # Test 1: Resolve library
#     print("\n1. Resolving 'fastapi'...")
#     library_id = client.resolve_library("fastapi")
#     print(f"   Result: {library_id}")

#     # Test 2: Get docs
#     if library_id:
#         print(f"\n2. Fetching docs for '{library_id}'...")
#         docs = client.get_docs(library_id, topic="streaming", tokens=1000)
#         print(f"   Retrieved {len(docs)} characters")
#         print(f"   Preview: {docs[:200]}...")


#     print("\n✅ Context7 client test complete!")


"""
Context7 Client - Fetches up-to-date documentation for libraries
Using Context7 MCP JSON-RPC API with LLM-powered intelligent library resolution
"""
import requests
from typing import Optional, List
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Context7Client:
    """Client for Context7 MCP API to fetch library documentation with intelligent LLM-based resolution"""

    def __init__(self, api_key: str, openai_api_key: Optional[str] = None):
        self.base_url = "https://mcp.context7.com/mcp"
        self.headers = {
            "CONTEXT7_API_KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

    def resolve_library_with_llm(self, library_name: str, matches: List[str]) -> Optional[str]:
        """Use GPT-4o-mini to intelligently pick the best library match"""
        if not self.openai_api_key:
            logger.warning("OpenAI API key not found, falling back to first match")
            return matches[0] if matches else None

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.openai_api_key)

            # Limit to top 15 matches to avoid overwhelming the LLM
            top_matches = matches[:15]
            matches_list = "\n".join(f"{i+1}. {match}" for i, match in enumerate(top_matches))

            prompt = f"""The user asked for documentation about: "{library_name}"

    Context7 API returned these {len(top_matches)} possible libraries:
    {matches_list}

    Your task: Select the library that BEST matches what the user asked for.


    Answer:"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise library matcher. You select the library ID that exactly matches what the user requested."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=10
            )

            answer = response.choices[0].message.content.strip()

            import re
            number_match = re.search(r'\d+', answer)
            if number_match:
                selected_index = int(number_match.group()) - 1

                if selected_index == -1:  # LLM returned 0 (no match)
                    logger.warning(f"LLM found no good match, searching all {len(matches)} for exact match...")
                    library_lower = library_name.lower().replace("-", "").replace("_", "")
                    for lib_id in matches:
                        repo_name = lib_id.split("/")[-1].lower().replace("-", "").replace("_", "")
                        if repo_name == library_lower:
                            logger.info(f"✅ Found exact match: '{library_name}' → '{lib_id}'")
                            return lib_id
                    return matches[0]

                if 0 <= selected_index < len(top_matches):
                    selected = top_matches[selected_index]

                    # Verify the LLM's choice makes sense
                    repo_name = selected.split("/")[-1].lower().replace("-", "").replace("_", "")
                    query_lower = library_name.lower().replace("-", "").replace("_", "")

                    if repo_name == query_lower:
                        logger.info(f"🤖 LLM selected (verified): '{library_name}' → '{selected}'")
                        return selected
                    else:
                        logger.warning(f"🤖 LLM selected '{selected}' but it doesn't match '{library_name}' exactly")
                        # Try to find exact match ourselves
                        for lib_id in matches:
                            repo_name = lib_id.split("/")[-1].lower().replace("-", "").replace("_", "")
                            if repo_name == query_lower:
                                logger.info(f"✅ Found better exact match: '{library_name}' → '{lib_id}'")
                                return lib_id
                        # If no exact match, trust the LLM
                        logger.info(f"No exact match found, trusting LLM choice: '{selected}'")
                        return selected

        except ImportError:
            logger.error("OpenAI package not installed. Run: pip install openai")
        except Exception as e:
            logger.error(f"LLM resolution failed: {e}")

        # Final fallback: exact string matching
        logger.info(f"⚠️  Fallback: searching for exact string match...")
        library_lower = library_name.lower().replace("-", "").replace("_", "")
        for lib_id in matches:
            repo_name = lib_id.split("/")[-1].lower().replace("-", "").replace("_", "")
            if repo_name == library_lower:
                logger.info(f"✅ Found exact match: '{library_name}' → '{lib_id}'")
                return lib_id

        logger.warning(f"No exact match found, returning first option: '{matches[0]}'")
        return matches[0] if matches else None

    def resolve_library(self, library_name: str, use_llm: bool = True) -> Optional[str]:
        """
        Resolve library name to Context7-compatible ID

        Args:
            library_name: Name of the library (e.g., "fastapi", "react", "MemMachine")
            use_llm: Whether to use LLM for intelligent selection (default: True)

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
            print(result)

            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                if isinstance(content, list) and len(content) > 0:
                    libraries_text = content[0].get("text", "")

                    import re
                    pattern = r"- Context7-compatible library ID: (\/[\w\-\/]+)"
                    matches = re.findall(pattern, libraries_text)

                    if matches:
                        non_website_matches = [
                            m for m in matches
                            if not m.startswith("/websites/")
                        ]

                        if not non_website_matches:
                            non_website_matches = matches

                        if len(non_website_matches) == 1:
                            logger.info(f"✅ Single match: '{library_name}' → '{non_website_matches[0]}'")
                            return non_website_matches[0]

                        elif len(non_website_matches) > 1:
                            logger.info(f"🔍 Found {len(non_website_matches)} matches for '{library_name}'")

                            if use_llm and self.openai_api_key:
                                return self.resolve_library_with_llm(library_name, non_website_matches)
                            else:
                                library_lower = library_name.lower().replace("-", "").replace("_", "")
                                for lib_id in non_website_matches:
                                    repo_name = lib_id.split("/")[-1].lower().replace("-", "").replace("_", "")
                                    if repo_name == library_lower:
                                        logger.info(f"✅ Exact name match: '{library_name}' → '{lib_id}'")
                                        return lib_id

                                logger.info(f"⚠️  Using first: '{non_website_matches[0]}'")
                                return non_website_matches[0]

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
        if tokens < 1000:
            tokens = 1000

        arguments = {
            "context7CompatibleLibraryID": library_id,
            "tokens": tokens
        }

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

            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                if isinstance(content, list):
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


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("CONTEXT7_API_KEY")
    if not api_key:
        print("❌ CONTEXT7_API_KEY not found in environment")
        exit(1)

    print("Testing Context7 Client...")
    client = Context7Client(api_key)

    print("\n1. Resolving 'fastapi'...")
    library_id = client.resolve_library("reducto ai")
    print(f"   Result: {library_id}")

    if library_id:
        print(f"\n2. Fetching docs for '{library_id}'...")
        docs = client.get_docs(library_id, topic="streaming", tokens=1000)
        print(f"   Retrieved {len(docs)} characters")
        print(f"   Preview: {docs[:200]}...")

    print("\n✅ Context7 client test complete!")
