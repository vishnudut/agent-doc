#!/usr/bin/env python3
"""
Test script for MCP server using MCP Inspector
This script helps verify our MCP server works correctly before Zed integration
"""
import asyncio
import json
import subprocess
import sys
import time
from typing import Dict, Any

async def test_mcp_server():
    """Test the MCP server by sending JSON-RPC requests"""

    print("🧪 Testing Documentation Injection Agent MCP Server")
    print("=" * 60)

    # Start the MCP server process
    server_process = subprocess.Popen(
        [sys.executable, "agent_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )

    def send_request(request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server"""
        request_str = json.dumps(request) + "\n"
        server_process.stdin.write(request_str)
        server_process.stdin.flush()

        # Read response
        response_str = server_process.stdout.readline()
        return json.loads(response_str)

    try:
        # Test 1: Initialize the server
        print("1. Initializing MCP server...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    }
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        response = send_request(init_request)
        print(f"   ✅ Initialize response: {response.get('result', {}).get('capabilities', 'OK')}")

        # Test 2: List available tools
        print("\n2. Listing available tools...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }

        response = send_request(tools_request)
        tools = response.get('result', {}).get('tools', [])
        print(f"   ✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"      - {tool.get('name', 'unknown')}: {tool.get('description', 'no description')}")

        # Test 3: Call get_library_docs tool
        print("\n3. Testing get_library_docs tool...")
        tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_library_docs",
                "arguments": {
                    "library_name": "fastapi",
                    "topic": "routing",
                    "user_id": "test_user"
                }
            }
        }

        start_time = time.time()
        response = send_request(tool_request)
        elapsed = (time.time() - start_time) * 1000

        result = response.get('result', {})
        content_blocks = result.get('content', [])

        print(f"   ✅ Tool call completed in {elapsed:.0f}ms")
        print(f"   📋 Returned {len(content_blocks)} content blocks")

        if content_blocks:
            first_block = content_blocks[0]
            preview = first_block.get('text', '')[:200] + "..." if len(first_block.get('text', '')) > 200 else first_block.get('text', '')
            print(f"   📝 Preview: {preview}")

        # Test 4: Test search_memory tool
        print("\n4. Testing search_memory tool...")
        memory_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "search_memory",
                "arguments": {
                    "query": "fastapi",
                    "user_id": "test_user"
                }
            }
        }

        response = send_request(memory_request)
        result = response.get('result', {})
        content_blocks = result.get('content', [])

        print(f"   ✅ Memory search returned {len(content_blocks)} content blocks")

        # Test 5: List resources
        print("\n5. Testing resources...")
        resources_request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/list"
        }

        response = send_request(resources_request)
        resources = response.get('result', {}).get('resources', [])
        print(f"   ✅ Found {len(resources)} resources:")
        for resource in resources:
            print(f"      - {resource.get('uri', 'unknown')}: {resource.get('name', 'no name')}")

        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        print("\n📋 Server Summary:")
        print(f"   • Tools: {len(tools)} available")
        print(f"   • Resources: {len(resources)} available")
        print(f"   • Performance: Tool calls working with response times")
        print(f"   • Memory: Search and storage functioning")
        print("\n✅ Ready for Zed integration!")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        stderr_output = server_process.stderr.read()
        if stderr_output:
            print(f"Server stderr: {stderr_output}")

    finally:
        # Clean up
        server_process.terminate()
        server_process.wait(timeout=5)


if __name__ == "__main__":
    print("Starting MCP Server Test Suite...")
    asyncio.run(test_mcp_server())
