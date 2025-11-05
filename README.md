# Agent Doc

A tool that provides real-time, most recent and up-to-date documentation retrieval directly in your code editor, eliminating the need to switch between editor and browser.

## Problem Solved

**Before**: Coding agent's not knowing the correct syntax or documentation for the tool's or tech the user is building with. Most of times it hallucinates and makes up functions or method's that don't even exist in certain libraries causing a serier of bugs and issues.

**After**: Get up-to-date documentation directly in Zed editor with intelligent memory and performance tracking. Your code editor will always ensure that the code it generates is accurate and uses reliable functions and methods as per latest documentation.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐
│   Zed Editor        │────▶│   MCP Server         │
│   (User Interface)  │     │   (Orchestrator)     │
└─────────────────────┘     └──────────┬───────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
        ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
        │   Context7      │ │   MemMachine    │ │     Opik        │
        │ (Fresh Docs)    │ │   (Memory)      │ │ (Analytics)     │
        │                 │ │                 │ │                 │
        │ • Library       │ │ • Query History │ │ • Performance   │
        │   Resolution    │ │ • User Profile  │ │ • Tracing       │
        │ • Doc Retrieval │ │ • Context Build │ │ • Insights      │
        └─────────────────┘ └─────────────────┘ └─────────────────┘
```

## Features

- **Real-time Documentation**: Fetch current docs from GitHub, not stale LLM training data
- **Intelligent Memory**: Learn from past queries and build user context over time
- **Performance Analytics**: Track what's working with detailed observability
- **Zero Context Switching**: Stay in your editor, never open browser tabs
- **Multi-Library Support**: Works with FastAPI, React, Django, and 100+ libraries

## Tech Stack

- **MCP Server**: Python with FastMCP for Model Context Protocol
- **Context7**: Real-time documentation retrieval from GitHub
- **MemMachine**: Intelligent memory and context building
- **Opik**: Performance tracking and observability
- **Zed Editor**: AI-native code editor with MCP integration

## Quick Start

### Prerequisites

- Python 3.11+
- Zed Editor
- Docker (for MemMachine)
- API keys for Context7 and Opik

### Setup

1. **Clone and setup environment**:
```bash
git clone <your-repo>
cd agent-doc
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment variables**:
```bash
# Create .env file
CONTEXT7_API_KEY=your_context7_key
OPENAI_API_KEY=your_openai_key
```

3. **Start MemMachine**:
```bash
# Download and start MemMachine with Docker
curl -sL https://api.github.com/repos/MemMachine/MemMachine/tarball/main | tar -xz
cd MemMachine-*
./memmachine-compose.sh
```

4. **Configure Opik**:
```bash
opik configure
```

5. **Configure Zed**:
Add to your Zed `settings.json`:
```json
{
  "context_servers": {
    "doc-injection-agent": {
      "source": "custom",
      "command": "/path/to/your/venv/bin/python",
      "args": ["/path/to/your/agent_mcp.py"],
      "env": {
        "PYTHONPATH": "/path/to/your/project"
      }
    }
  }
}
```

6. **Test the setup**:
```bash
python test_mcp.py
```

## Usage

1. Open Zed Editor
2. Start a new chat in the Agent Panel
3. Ask about any library: *"How do I create FastAPI routes with path parameters?"*
4. Get instant, up-to-date documentation with memory context

### Example Queries

- *"How to stream responses in FastAPI?"*
- *"React useEffect cleanup best practices"*
- *"Django async views implementation"*
- *"What have I asked about FastAPI before?"*

## Project Structure

```
agent-doc/
├── agent_mcp.py           # Main MCP server
├── context_client.py      # Context7 integration
├── memmachine_client.py   # MemMachine integration
├── opik_client.py         # Opik integration
├── test_mcp.py           # Test suite
├── requirements.txt       # Dependencies
├── .env                  # Environment variables
└── README.md             # This file
```

## How It Works

1. **User Query**: Ask about documentation in Zed
2. **Memory Search**: Check MemMachine for similar past queries
3. **Doc Retrieval**: Fetch current docs from Context7
4. **Context Building**: Combine fresh docs with user context
5. **Response**: Get intelligent answer with memory context
6. **Tracking**: All interactions logged in Opik for analytics

## Performance

- **Average Response Time**: 2-6 seconds
- **Documentation Freshness**: Real-time from GitHub
- **Memory Context**: 3+ similar queries with similarity scores
- **Library Coverage**: 100+ supported frameworks/libraries

## Monitoring

View detailed analytics in your Opik dashboard:
- Query patterns and frequency
- Response times and success rates
- User learning progression
- Library usage statistics

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with `python test_mcp.py`
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built for hackathon with sponsor technologies:
- **Upstash Context7** - Real-time documentation retrieval
- **MemMachine** - Intelligent memory and context
- **Comet Opik** - Performance tracking and observability

---
