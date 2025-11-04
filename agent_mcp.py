#!/usr/bin/env python3
"""
Documentation Injection Agent - MCP Server
Orchestrates Context7, MemMachine, and Opik for intelligent documentation retrieval

This MCP server provides tools for Zed editor to fetch up-to-date documentation
with memory persistence and performance tracking.
"""
import asyncio
import logging
import os
import sys
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv

# MCP imports
from mcp.server.fastmcp import FastMCP
from mcp.server import NotificationOptions
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
import mcp.types as types

# Our client imports
from context_client import Context7Client
from memmachine_client import MemMachineClient
from opik_client import OpikClient

# Environment and logging setup
load_dotenv()  # Load .env file
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MCP server
mcp = FastMCP("Documentation Injection Agent")

# Initialize our clients
context7_client = None
memmachine_client = None
opik_client = None


def initialize_clients():
    """Initialize all client connections"""
    global context7_client, memmachine_client, opik_client

    try:
        # Initialize Context7 client
        context7_api_key = os.getenv("CONTEXT7_API_KEY")
        if not context7_api_key:
            logger.error("CONTEXT7_API_KEY not found in environment")
            return False

        context7_client = Context7Client(context7_api_key)
        logger.info("Context7 client initialized")

        # Initialize MemMachine client
        memmachine_client = MemMachineClient()
        if not memmachine_client.health_check():
            logger.error("MemMachine health check failed")
            return False
        logger.info("MemMachine client initialized")

        # Initialize Opik client
        opik_client = OpikClient()
        if not opik_client.is_configured():
            logger.warning("Opik client not configured - analytics will be disabled")
        else:
            logger.info("Opik client initialized")

        return True

    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        return False


@mcp.resource("doc-agent://status")
async def get_agent_status() -> str:
    """Get the status of all integrated services"""
    status = {
        "agent": "Documentation Injection Agent",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "context7": bool(context7_client),
            "memmachine": bool(memmachine_client and memmachine_client.health_check()),
            "opik": bool(opik_client and opik_client.is_configured())
        }
    }
    return f"Service Status:\n{status}"


@mcp.tool()
async def get_library_docs(
    library_name: str,
    topic: str = "",
    user_id: str = "zed_user"
) -> List[types.TextContent]:
    """
    Fetch up-to-date documentation for a library with intelligent memory and tracking.

    This tool:
    1. Searches MemMachine for similar past queries
    2. Fetches current docs from Context7
    3. Stores the session in MemMachine for future reference
    4. Tracks everything with Opik for analytics

    Args:
        library_name: Name of the library/framework (e.g., "fastapi", "react", "django")
        topic: Optional specific topic to focus on (e.g., "authentication", "routing")
        user_id: User identifier for memory personalization

    Returns:
        List of TextContent with documentation and context
    """
    start_time = time.time()

    if not context7_client or not memmachine_client:
        return [types.TextContent(
            type="text",
            text="❌ Service not available. Please check Context7 API key and MemMachine connection."
        )]

    try:
        # Step 1: Search MemMachine for similar queries
        query_text = f"{library_name} {topic}".strip()
        memory_start = time.time()

        similar_queries = memmachine_client.search_similar_queries(
            query=query_text,
            user_id=user_id,
            limit=3
        )

        memory_time = (time.time() - memory_start) * 1000

        # Track MemMachine operation in Opik
        if opik_client:
            opik_client.trace_memmachine_operation(
                operation_type="search",
                query=query_text,
                success=similar_queries['has_context'],
                result_count=len(similar_queries['episodic_memory']),
                response_time_ms=memory_time
            )

        # Step 2: Resolve and fetch docs from Context7
        context7_start = time.time()

        # Resolve library name to Context7 ID
        library_id = context7_client.resolve_library(library_name)

        if not library_id:
            error_msg = f"❌ Library '{library_name}' not found in Context7 database."

            # Track failed Context7 call
            if opik_client:
                opik_client.trace_context7_call(
                    library_name=library_name,
                    library_id=None,
                    success=False,
                    docs_retrieved="",
                    error_message=f"Library not found: {library_name}"
                )

            return [types.TextContent(type="text", text=error_msg)]

        # Fetch documentation
        docs = context7_client.get_docs(
            library_id=library_id,
            topic=topic if topic else None,
            tokens=3000
        )

        context7_time = (time.time() - context7_start) * 1000
        context7_success = bool(docs)

        # Track Context7 operation in Opik
        if opik_client:
            opik_client.trace_context7_call(
                library_name=library_name,
                library_id=library_id,
                success=context7_success,
                docs_retrieved=docs,
                response_time_ms=context7_time
            )

        if not docs:
            error_msg = f"❌ No documentation found for '{library_name}' (ID: {library_id})"
            return [types.TextContent(type="text", text=error_msg)]

        # Step 3: Store this retrieval session in MemMachine
        store_start = time.time()

        store_success = memmachine_client.store_retrieval_session(
            user_query=query_text,
            library_name=library_name,
            library_id=library_id,
            retrieved_docs=docs,
            context7_success=context7_success,
            user_id=user_id,
            metadata={
                "topic": topic,
                "context7_response_time_ms": context7_time,
                "memory_search_time_ms": memory_time
            }
        )

        store_time = (time.time() - store_start) * 1000

        # Track MemMachine store operation
        if opik_client:
            opik_client.trace_memmachine_operation(
                operation_type="store",
                query=f"Store: {query_text}",
                success=store_success,
                response_time_ms=store_time
            )

        # Step 4: Create main trace in Opik for the full session
        if opik_client:
            opik_client.trace_doc_retrieval_session(
                user_query=query_text,
                library_name=library_name,
                library_id=library_id,
                context7_success=context7_success,
                retrieved_docs=docs,
                memmachine_context=str(similar_queries) if similar_queries['has_context'] else None,
                user_id=user_id,
                metadata={
                    "total_time_ms": (time.time() - start_time) * 1000,
                    "context7_time_ms": context7_time,
                    "memory_time_ms": memory_time,
                    "store_time_ms": store_time,
                    "topic": topic,
                    "has_memory_context": similar_queries['has_context']
                }
            )

        # Step 5: Build response with context
        response_parts = []

        # Add memory context if available
        if similar_queries['has_context']:
            context_prompt = memmachine_client.build_context_prompt(
                similar_queries['episodic_memory'],
                similar_queries['profile_memory'],
                query_text
            )

            response_parts.append(types.TextContent(
                type="text",
                text=f"🧠 **Memory Context Found** ({len(similar_queries['episodic_memory'])} similar queries)\n\n{context_prompt}\n\n---\n"
            ))

        # Add the main documentation
        response_parts.append(types.TextContent(
            type="text",
            text=f"📚 **Latest Documentation: {library_name}**\n"
                 f"Source: Context7 ID `{library_id}`\n"
                 f"Topic: {topic or 'General'}\n"
                 f"Retrieved: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                 f"{docs}\n\n"
                 f"---\n"
                 f"⚡ Performance: Context7: {context7_time:.0f}ms | Memory: {memory_time:.0f}ms | Total: {(time.time() - start_time) * 1000:.0f}ms"
        ))

        return response_parts

    except Exception as e:
        logger.error(f"Error in get_library_docs: {e}")

        # Track error in Opik
        if opik_client:
            opik_client.trace_doc_retrieval_session(
                user_query=f"{library_name} {topic}".strip(),
                library_name=library_name,
                library_id="error",
                context7_success=False,
                retrieved_docs="",
                user_id=user_id,
                metadata={
                    "error": str(e),
                    "total_time_ms": (time.time() - start_time) * 1000
                }
            )

        return [types.TextContent(
            type="text",
            text=f"❌ Error retrieving documentation for '{library_name}': {str(e)}"
        )]


@mcp.tool()
async def search_memory(
    query: str,
    user_id: str = "zed_user"
) -> List[types.TextContent]:
    """
    Search MemMachine for past documentation retrievals and context.

    Args:
        query: Search query
        user_id: User identifier

    Returns:
        List of TextContent with memory search results
    """
    if not memmachine_client:
        return [types.TextContent(
            type="text",
            text="❌ MemMachine not available"
        )]

    try:
        results = memmachine_client.search_similar_queries(query, user_id, limit=5)

        if not results['has_context']:
            return [types.TextContent(
                type="text",
                text=f"🔍 No memory context found for query: '{query}'"
            )]

        memory_text = memmachine_client.build_context_prompt(
            results['episodic_memory'],
            results['profile_memory'],
            query
        )

        return [types.TextContent(
            type="text",
            text=f"🧠 **Memory Search Results**\n"
                 f"Query: {query}\n"
                 f"Found: {len(results['episodic_memory'])} relevant memories\n\n"
                 f"{memory_text}"
        )]

    except Exception as e:
        logger.error(f"Error in search_memory: {e}")
        return [types.TextContent(
            type="text",
            text=f"❌ Error searching memory: {str(e)}"
        )]


@mcp.tool()
async def get_agent_analytics() -> List[types.TextContent]:
    """
    Get analytics and performance data from Opik.

    Returns:
        List of TextContent with analytics information
    """
    if not opik_client or not opik_client.is_configured():
        return [types.TextContent(
            type="text",
            text="❌ Opik analytics not available. Run 'opik configure' to enable tracking."
        )]

    try:
        stats = opik_client.get_project_stats()

        return [types.TextContent(
            type="text",
            text=f"📊 **Agent Analytics**\n"
                 f"Project: {stats.get('project_name', 'doc-injection-agent')}\n"
                 f"Status: {stats.get('status', 'unknown')}\n"
                 f"Opik Dashboard: https://www.comet.com/opik\n\n"
                 f"Note: Detailed analytics available in Opik dashboard"
        )]

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return [types.TextContent(
            type="text",
            text=f"❌ Error retrieving analytics: {str(e)}"
        )]


async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Documentation Injection Agent MCP Server...")

    # Initialize all clients
    if not initialize_clients():
        logger.error("Failed to initialize clients. Exiting.")
        sys.exit(1)

    logger.info("All clients initialized successfully")
    logger.info("MCP Server ready - waiting for connections from Zed...")

    # Run the FastMCP server with stdio transport
    await mcp.run_stdio_async()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
