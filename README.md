# Things 3 Enhanced MCP Server

A production-ready **Model Context Protocol (MCP) server** for [Things 3](https://culturedcode.com/things/), enabling AI assistants and automation platforms to interact with your task management system through natural language.

> **⚠️ Important:** Review the [Privacy Notice](PRIVACY.md) and [Terms of Use](TERMS_OF_USE.md) before installation.

## Overview

This MCP server provides seamless integration between Things 3 and AI assistants like Claude Desktop, allowing you to manage tasks, projects, and areas using natural language. Built with the modern **FastMCP** framework, it includes production-ready reliability features like intelligent caching, rate limiting, circuit breakers, and comprehensive error handling.

### Key Benefits

- **🗣️ Natural Language Interface**: Create and manage tasks conversationally through AI assistants
- **📊 Smart Insights**: Analyze productivity patterns and project status with AI-powered queries
- **⚡ Production-Ready**: Built-in caching, rate limiting, and automatic retry logic
- **🔒 Privacy-First**: All operations are local-only; your task data never leaves your Mac
- **🔄 Seamless Integration**: Works directly with your existing Things 3 database

## Prerequisites

- **macOS** (required - uses AppleScript and macOS `open` command)
- **Things 3** for macOS with scripting permissions enabled
- **Python 3.12+**
- **uv** package manager (recommended) or standard Python tooling

> **Note:** Docker is not supported due to macOS VM limitations preventing access to host-level AppleScript and URL scheme handlers.

## Features

### 📋 Things 3 Integration

- **List Access**: Inbox, Today, Upcoming, Anytime, Someday, Logbook, and Trash
- **Task Management**: Create, update, search, and organize todos with full metadata
- **Checklist Management**: View, add, update checklist items; find todos with checklists
- **Project & Area Management**: Organize tasks into projects and areas with nesting support
- **Heading Support**: Add organizational headings to projects; view hierarchical structure
- **Tag Operations**: Create, assign, and filter by tags (auto-creates missing tags)
- **Deadline Tracking**: Find overdue items, get upcoming deadlines, set/clear deadlines
- **Advanced Search**: Filter by type, status, deadline, tags, areas, and custom queries
- **Smart Counting**: Check item counts before fetching to manage context window

### 🚀 Reliability Features

- **Intelligent Caching**: Configurable TTL-based caching for read operations
- **Circuit Breaker**: Automatic failure detection and recovery
- **Rate Limiting**: Prevents API abuse and throttles operations safely
- **Dead Letter Queue**: Tracks failed operations for debugging (`things_dlq.json`)
- **Retry Logic**: Exponential backoff with jitter for transient failures
- **Structured Logging**: Privacy-aware logging with sensitive data redaction

### 🔌 MCP Integration

- **FastMCP Framework**: Modern, type-safe MCP implementation
- **Rich Metadata**: Assistants receive instructions, capabilities, and limitations
- **HTTP Transport**: RESTful interface on `http://127.0.0.1:8009` (configurable)
- **Tool Annotations**: Optimization hints for read-only, idempotent, and destructive operations

## Quick Start

### Installation

1. **Review Privacy & Terms**
   Confirm you've read the [Privacy Notice](PRIVACY.md) and [Terms of Use](TERMS_OF_USE.md).

2. **Install uv** (recommended)

   ```bash
   pipx install uv
   # or: pip install uv
   ```

3. **Clone and Install**

   ```bash
   git clone https://github.com/CaseyRo/things-fastmcp.git
   cd things-fastmcp
   uv venv
   uv pip install -e .
   ```

   *The helper script will bootstrap a virtual environment automatically if you skip this step.*

4. **Configure Authentication**

   ```bash
   uv run configure_token.py
   ```

   Follow the prompts to set up your Things 3 authentication token.

### Running the Server

**Option 1: Production Mode** (recommended)

```bash
uv run server
```

- Binds to `http://127.0.0.1:8009` by default (localhost-only)
- Uses [Rich](https://github.com/Textualize/rich) for colorful terminal output
- Auto-manages virtual environment and dependencies

**Option 2: Development Mode**

```bash
uv run dev
```

Same as production mode but with development-friendly settings.

**Option 3: Manual Development Mode** (with auto-reload)

```bash
mcp dev src/things_mcp/things_fast_server.py
```

Uses the [MCP development helper](https://github.com/anthropics/mcp-cli#development-helper) for automatic reloading on file changes.

### Configuration

**Environment Variables:**

```bash
# Bind to all interfaces (⚠️ exposes server to network - only for HTTP transport)
export THINGS_FASTMCP_HOST=0.0.0.0

# Use custom port (only for HTTP transport)
export THINGS_FASTMCP_PORT=9000

# Use HTTP transport instead of STDIO (for remote access)
export THINGS_MCP_TRANSPORT=http
```

**Transport Configuration:**

The server supports two transport modes:

- **STDIO (default)**: For local MCP clients like Claude Desktop, VS Code, Cursor, Windsurf
  - Communicates via standard input/output
  - Most secure (no network exposure)
  - Automatically selected when running via `uv run server`

- **HTTP**: For remote access or web-based integrations
  - Runs as a web service on `http://127.0.0.1:8009`
  - Enable with: `export THINGS_MCP_TRANSPORT=http`
  - Configure host/port with THINGS_FASTMCP_HOST and THINGS_FASTMCP_PORT

**Using .env File:**

Create a `.env` file in the project root for easy configuration:

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your preferred settings
THINGS_FASTMCP_HOST=127.0.0.1
THINGS_FASTMCP_PORT=8009
```

**Environment Variable Override:**

```bash
# Override configuration when running
THINGS_FASTMCP_HOST=0.0.0.0 THINGS_FASTMCP_PORT=9000 uv run server
```

## Available MCP Tools

The server exposes 31 tools organized into logical groups:

### 📥 List Views

- `get-inbox` - Retrieve items in Inbox
- `get-today` - Get tasks due today
- `get-upcoming` - View upcoming scheduled tasks
- `get-anytime` - List Anytime tasks
- `get-someday` - List Someday/Maybe items
- `get-logbook` - Access completed items (configurable period)
- `get-trash` - View deleted items

### 📝 Task Operations

- `get-todos` - List all todos (optionally filtered by project)
- `add-todo` - Create new tasks with full metadata
- `update-todo` - Modify existing tasks

### ✅ Checklist Operations

- `get-checklist-items` - Retrieve checklist items for a todo
- `add-checklist-item` - Add new checklist items to a todo
- `update-checklist-item` - Replace entire checklist for a todo
- `get-todos-with-checklists` - Find all todos containing checklists

### 📁 Project & Area Management

- `get-projects` - List all projects
- `get-areas` - List all areas
- `add-project` - Create new projects
- `update-project` - Modify existing projects
- `get-project-structure` - View hierarchical project structure with headings
- `add-heading` - Add organizational headings to projects
- `move-todo-under-heading` - Reorganize todos by moving them under headings
- `move-item-to-project` - Move todos to projects/areas (optionally under a heading)

### 🏷️ Tag Operations

- `get-tags` - List all tags
- `get-tagged-items` - Filter items by tag

### 🔍 Search & Discovery

- `search-todos` - Search by title or notes (supports type, status, deadline filters)
- `search-advanced` - Multi-criteria filtering
- `search-items` - Open search in Things app
- `show-item` - Display specific item or list in Things

### ⏰ Deadline Management

- `get-overdue-items` - Find items with past deadlines (shows days overdue)
- `get-items-due-soon` - Get items with deadlines in next N days (color-coded urgency)
- `set-deadline` - Set or update deadline (supports 'today', 'tomorrow', ISO dates, 'none')

### 📊 Diagnostics & Helpers

- `get-recent` - Recently created items
- `get-cache-stats` - Cache performance metrics
- `count-items` - Get counts for all main areas (lightweight)
- `count-search` - Count search results before fetching
- `count-tagged-items` - Count items with specific tag
- `count-project-items` - Count items in project
- `count-advanced` - Count advanced search results

Each tool includes detailed docstrings visible to AI assistants, with parameter descriptions and usage examples.

## Known Limitations

### Interactive Tools Require Elicitation Support

⚠️ **Important for Claude Desktop Users:** Some advanced tools use FastMCP's interactive elicitation feature for step-by-step workflows. **Claude Desktop does not currently support the `elicitation/create` MCP method**, which means these tools will fail with "Method not found" errors.

**Interactive Tools (Not Currently Supported in Claude Desktop):**

- `add-todo-interactive` - Interactive todo creation wizard
- `bulk-complete-todos` - Bulk completion with preview & confirmation
- `bulk-schedule-todos` - Bulk scheduling with preview & confirmation
- `bulk-tag-todos` - Bulk tag operations with preview & confirmation
- `bulk-move-todos` - Bulk move operations with preview & confirmation
- `schedule-assistant` - Smart scheduling with natural language
- `create-project-template` - Interactive template creation
- `apply-project-template` - Apply templates with variable substitution
- `update-project-template` - Interactive template editing
- `delete-project-template` - Template deletion with confirmation

**Working Alternatives:**

- ✅ **Use `add-todo`** instead of `add-todo-interactive` (provide all parameters directly)
- ✅ **Use `add-project`** to create reusable project structures (you can save these as reference projects)
- ✅ **Use `update-todo`** for individual todo modifications
- ✅ **Use `list-project-templates`** (this works! - no elicitation needed)

**Why This Happens:**

FastMCP's `Context.elicit()` method enables servers to request structured input from users during tool execution. This creates a richer, conversational experience with preview-and-confirm workflows. However, elicitation is an **optional MCP extension** that not all clients implement yet.

**Log Evidence:**
```
Server → Client: {"method":"elicitation/create", "params":{...}}
Client → Server: {"error":{"code":-32601,"message":"Method not found"}}
```

**Future Support:**

When Claude Desktop (or other MCP clients) add elicitation support, these interactive tools will work automatically without any code changes. The tools detect client capabilities at runtime and will gracefully handle both scenarios.

**For MCP Client Developers:**

To support these interactive tools, implement the `elicitation/create` JSON-RPC method in your MCP client. See the [FastMCP elicitation documentation](https://github.com/jlowin/fastmcp) for details on the protocol.

## Architecture

```text
src/things_mcp/
├── fast_server.py           # FastMCP server with tool definitions
├── handlers.py              # Tool handlers with reliability features
├── url_scheme.py            # Things URL scheme builders
├── applescript_bridge.py    # AppleScript execution layer
├── formatters.py            # Output formatting
├── cache.py                 # Caching decorator (@cached)
├── utils.py                 # Circuit breaker, rate limiter, DLQ
├── logging_config.py        # Structured logging with redaction
└── tag_handler.py           # Automatic tag creation
```

**Data Flow:**

1. MCP client → FastMCP server receives tool call
2. Tool handler validates params and checks circuit breaker
3. Read operations → things-py (SQLite) → cache → format response
4. Write operations → URL scheme builder → macOS `open` command → Things app
5. Errors → retry logic → circuit breaker → dead letter queue if needed

## Usage with AI Assistants

### Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "things": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "{{ABSOLUTE_PATH_TO_THINGS_FASTMCP}}",
        "server"
      ]
    }
  }
}
```

**Important:** Replace `{{ABSOLUTE_PATH_TO_THINGS_FASTMCP}}` with the actual absolute path to your cloned repository (e.g., `/Users/yourname/Repositories/things-fastmcp`).

**Quick Setup:**

```fish
# For fish shell
printf '%s\n' '{' '  "mcpServers": {' '    "things": {' '      "command": "uv",' '      "args": [' '        "run",' '        "--directory",' '        "/absolute/path/to/things-fastmcp",' '        "server"' '      ]' '    }' '  }' '}' > ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

```bash
# For bash/zsh
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json << 'EOF'
{
  "mcpServers": {
    "things": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/things-fastmcp",
        "server"
      ]
    }
  }
}
EOF
```

After updating the config:
1. Quit Claude Desktop completely (Cmd+Q)
2. Relaunch Claude Desktop
3. Look for the 🔌 MCP icon in a new conversation
4. The Things server should appear in the connected servers list

**Troubleshooting:**
- If you see "Server disconnected", check the logs: `tail -f ~/Library/Logs/Claude/mcp*.log`
- Make sure `uv` is installed and in your PATH: `which uv`
- Verify the repository path is absolute and correct

### VS Code with GitHub Copilot

Add to your VS Code settings (`.vscode/settings.json` in your workspace or global User settings):

```json
{
  "github.copilot.chat.mcp.servers": {
    "things": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "{{ABSOLUTE_PATH_TO_THINGS_FASTMCP}}",
        "server"
      ]
    }
  }
}
```

**Important:** Replace `{{ABSOLUTE_PATH_TO_THINGS_FASTMCP}}` with the actual absolute path to your cloned repository.

After updating:
1. Reload VS Code window (Cmd+Shift+P → "Developer: Reload Window")
2. Open GitHub Copilot Chat
3. The Things MCP tools will be available for use in conversations

### Cursor

Add to your Cursor config (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "things": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "{{ABSOLUTE_PATH_TO_THINGS_FASTMCP}}",
        "server"
      ]
    }
  }
}
```

**Important:** Replace `{{ABSOLUTE_PATH_TO_THINGS_FASTMCP}}` with the actual absolute path to your cloned repository.

After updating:
1. Restart Cursor
2. Open a new chat session
3. The Things MCP tools will be available

### Windsurf (Claude Code)

Add to your Windsurf config (`~/Library/Application Support/Windsurf/User/globalStorage/mcp.json`):

```json
{
  "mcpServers": {
    "things": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "{{ABSOLUTE_PATH_TO_THINGS_FASTMCP}}",
        "server"
      ]
    }
  }
}
```

**Important:** Replace `{{ABSOLUTE_PATH_TO_THINGS_FASTMCP}}` with the actual absolute path to your cloned repository.

After updating:
1. Restart Windsurf
2. Open a new Cascade or Chat session
3. The Things MCP tools will be available

### Testing Your Configuration

Once configured in any client, test the connection by asking:

```
Can you show me my inbox tasks?
```

The AI should use the `get-inbox` tool to retrieve your Things 3 inbox items.

### Troubleshooting Configuration

**MCP server not appearing:**
- Verify the path in your config points to the correct repository location
- Check that `uv` is installed and in your PATH: `which uv`
- Ensure Things 3 is running and accessible
- Review the MCP server logs (location varies by client)

**Permission errors:**
- Verify Things 3 has automation permissions (System Preferences → Security & Privacy)
- Check that the authentication token is configured: `uv run configure_token.py`

**Connection issues:**
- Make sure no other process is using port 8009
- Check environment variables if you've customized THINGS_FASTMCP_HOST or THINGS_FASTMCP_PORT

### MCP Client Metadata

AI assistants automatically receive:

- **Instructions**: Available tools, limitations, and privacy reminders
- **Website**: Link to this repository for documentation
- **Icon**: OpenMoji notepad icon for easy recognition

## Development

### Running in Development Mode

```bash
mcp dev things_fast_server.py
```

Enables auto-reload on file changes using the [MCP CLI development helper](https://github.com/anthropics/mcp-cli#development-helper).

### Code Quality

Before committing changes:

```bash
# Lint and format
ruff check .
ruff format .

# Run tests
pytest

# Check test coverage
pytest --cov=src/things_mcp
```

### Project Conventions

See [openspec/project.md](openspec/project.md) for:

- Code style guidelines
- Architecture patterns
- Type hints conventions
- Logging best practices
- Testing requirements

## Troubleshooting

### Common Issues

**Server won't start:**

- Verify Things 3 is installed and running
- Check Python version: `python --version` (requires 3.12+)
- Review logs for "Things app not available" messages

**Operations failing:**

- Check circuit breaker status in logs
- Review Dead Letter Queue: `cat things_dlq.json`
- Verify Things has automation permissions (System Preferences → Security & Privacy)

**Performance issues:**

- Check cache hit rate: Use `get-cache-stats` tool
- Review rate limiter logs for throttling
- Increase cache TTL in `cache.py` for slower-changing data

### Advanced Debugging

1. **Enable Debug Logging**
   Edit `src/things_mcp/logging_config.py` and set `console_level="DEBUG"`

2. **Monitor Dead Letter Queue**
   Failed operations are logged to `things_dlq.json` with full context

3. **Check Circuit Breaker State**
   Look for "Circuit breaker is open" messages in logs

4. **Cache Performance**
   Use the `get-cache-stats` MCP tool to analyze hit rates and optimization opportunities

5. **Inspect AppleScript Execution**
   Check logs for `osascript` subprocess errors

### Why No Docker Support?

Docker containers on macOS run in a lightweight VM that lacks access to host-level AppleScript and URL scheme handlers. The server requires direct macOS execution to interact with Things 3. Use `uv run server` directly on your Mac instead.

## Version 2.0 Changes

**Breaking Change:** Removed legacy MCP implementation.

If you're upgrading from 1.x:
- Update MCP client configs: `things_server.py` → `things_fast_server.py`
- All tool names and signatures remain unchanged
- You now get all reliability features automatically (caching, circuit breaker, retry logic)

See [CHANGELOG.md](CHANGELOG.md) for complete details.

## Contributing

Contributions are welcome! This project uses the [OpenSpec](openspec/AGENTS.md) workflow for spec-driven development.

**Before contributing:**

1. Read [openspec/project.md](openspec/project.md) for project conventions
2. Check existing [issues](https://github.com/CaseyRo/things-fastmcp/issues) and specs
3. Follow the change proposal workflow for new features
4. Run `ruff check .` and `pytest` before submitting PRs

## Migration from Bash Script

If you were previously using the bash script (`./run_things_fastmcp.sh`), here's how to migrate:

**Old way:**
```bash
./run_things_fastmcp.sh
./run_things_fastmcp.sh --host 0.0.0.0 --port 9000
```

**New way:**
```bash
uv run server
THINGS_FASTMCP_HOST=0.0.0.0 THINGS_FASTMCP_PORT=9000 uv run server
```

**Benefits of the new approach:**
- ✅ Simpler command syntax
- ✅ Better dependency management with UV
- ✅ Configuration via `.env` files
- ✅ No bash script maintenance overhead

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits & Acknowledgments

This project builds on the excellent work of:

- **[Harald Lindstrøm](https://github.com/hald)** - Original [things-mcp](https://github.com/hald/things-mcp) implementation
- **[Yaroslav Krempovych](https://github.com/excelsier)** - FastMCP modernization
- **[Cultured Code](https://culturedcode.com)** - Things 3 app and things-py library
- **[Anthropic](https://anthropic.com)** - Model Context Protocol specification and FastMCP framework

## Links

- **Documentation**: [README.md](README.md)
- **Issues & Support**: [GitHub Issues](https://github.com/CaseyRo/things-fastmcp/issues)
- **Privacy Policy**: [PRIVACY.md](PRIVACY.md)
- **Terms of Use**: [TERMS_OF_USE.md](TERMS_OF_USE.md)
- **MCP Specification**: [Model Context Protocol](https://github.com/anthropics/mcp)
- **Things 3 URL Scheme**: [Official Documentation](https://culturedcode.com/things/support/articles/2803573/)
