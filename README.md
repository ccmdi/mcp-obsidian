>[!NOTE] 
> This is a small modification of [this plugin](https://github.com/MarkusPfundstein/mcp-obsidian), which removes write access and adds a reading whitelist, so you can choose what to share as context.

# MCP server for Obsidian

MCP server to interact with Obsidian via the Local REST API community plugin.

<a href="https://glama.ai/mcp/servers/3wko1bhuek"><img width="380" height="200" src="https://glama.ai/mcp/servers/3wko1bhuek/badge" alt="server for Obsidian MCP server" /></a>

## Components

### Tools

The server implements multiple **read-only** tools to interact with Obsidian:

- list_files_in_vault: Lists all files and directories in the root directory of your Obsidian vault
- list_files_in_dir: Lists all files and directories in a specific Obsidian directory
- get_file_contents: Return the content of a single file in your vault.
- search: Search for documents matching a specified text query across all files in the vault
- complex_search: Complex search for documents using JsonLogic queries
- batch_get_file_contents: Return the contents of multiple files in your vault
- get_periodic_note: Get current periodic note for the specified period
- get_recent_periodic_notes: Get most recent periodic notes for the specified period type
- get_recent_changes: Get recently modified files in the vault
- get_all_tags: Get all unique tags used across all notes in the vault

**Note:** This server is read-only. All write, edit, and delete operations have been removed for security.

### Security Features

#### Whitelist System

The server includes a whitelist system that allows you to restrict access to only specific files and directories. This provides an additional layer of security by ensuring the server can only access files you explicitly allow.

**How it works:**
- If no whitelist is configured, the server can access all files (backward compatibility)
- If a whitelist is configured, the server can only access files/directories that match the whitelist patterns
- Whitelist patterns support exact matches, directory prefixes, and glob-style patterns

**Configuration:**
Add the `OBSIDIAN_WHITELIST` environment variable with a comma-separated list of allowed paths:

```
OBSIDIAN_WHITELIST=Work/,personal/journal.md,*.md,docs/**
```

**Pattern examples:**
- `Work/` - Allow access to all files in the Work directory
- `personal/journal.md` - Allow access to a specific file
- `*.md` - Allow access to all markdown files in the root directory
- `docs/**` - Allow access to all files in the docs directory and subdirectories

### Example prompts

Its good to first instruct Claude to use Obsidian. Then it will always call the tool.

The use prompts like this:
- Get the contents of the last architecture call note and summarize them
- Search for all files where Azure CosmosDb is mentioned and quickly explain to me the context in which it is mentioned
- Show me the recent changes in my vault
- Show me all the tags I'm using in my vault and organize them by category

## Configuration

### Obsidian REST API Key

There are two ways to configure the environment with the Obsidian REST API Key. 

1. Add to server config (preferred)

```json
{
  "mcp-obsidian": {
    "command": "uvx",
    "args": [
      "mcp-obsidian"
    ],
    "env": {
      "OBSIDIAN_API_KEY": "<your_api_key_here>",
      "OBSIDIAN_HOST": "<your_obsidian_host>",
      "OBSIDIAN_PORT": "<your_obsidian_port>",
      "OBSIDIAN_WHITELIST": "<comma_separated_paths>"
    }
  }
}
```
Sometimes Claude has issues detecting the location of uv / uvx. You can use `which uvx` to find and paste the full path in above config in such cases.

2. Create a `.env` file in the working directory with the following required variables:

```
OBSIDIAN_API_KEY=your_api_key_here
OBSIDIAN_HOST=your_obsidian_host
OBSIDIAN_PORT=your_obsidian_port
OBSIDIAN_WHITELIST=your_whitelist_paths
```

Note:
- You can find the API key in the Obsidian plugin config
- Default port is 27124 if not specified
- Default host is 127.0.0.1 if not specified
- OBSIDIAN_WHITELIST is optional - if not specified, all files are accessible

## Quickstart

### Install

#### Obsidian REST API

You need the Obsidian REST API community plugin running: https://github.com/coddingtonbear/obsidian-local-rest-api

Install and enable it in the settings and copy the api key.

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`

On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  
```json
{
  "mcpServers": {
    "mcp-obsidian": {
      "command": "uv",
      "args": [
        "--directory",
        "<dir_to>/mcp-obsidian",
        "run",
        "mcp-obsidian"
      ],
      "env": {
        "OBSIDIAN_API_KEY": "<your_api_key_here>",
        "OBSIDIAN_HOST": "<your_obsidian_host>",
        "OBSIDIAN_PORT": "<your_obsidian_port>",
        "OBSIDIAN_WHITELIST": "<comma_separated_paths>"
      }
    }
  }
}
```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  
```json
{
  "mcpServers": {
    "mcp-obsidian": {
      "command": "uvx",
      "args": [
        "mcp-obsidian"
      ],
      "env": {
        "OBSIDIAN_API_KEY": "<YOUR_OBSIDIAN_API_KEY>",
        "OBSIDIAN_HOST": "<your_obsidian_host>",
        "OBSIDIAN_PORT": "<your_obsidian_port>",
        "OBSIDIAN_WHITELIST": "<comma_separated_paths>"
      }
    }
  }
}
```
</details>

## Development

### Building

To prepare the package for distribution:

1. Sync dependencies and update lockfile:
```bash
uv sync
```

### Debugging

Since MCP servers run over stdio, debugging can be challenging. For the best debugging
experience, we strongly recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

You can launch the MCP Inspector via [`npm`](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm) with this command:

```bash
npx @modelcontextprotocol/inspector uv --directory /path/to/mcp-obsidian run mcp-obsidian
```

Upon launching, the Inspector will display a URL that you can access in your browser to begin debugging.

You can also watch the server logs with this command:

```bash
tail -n 20 -f ~/Library/Logs/Claude/mcp-server-mcp-obsidian.log
```
