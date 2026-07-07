---
name: reactome-neo4j-ols-setup
description: Step-by-step setup guide for a local Reactome Neo4j database connected to Claude Desktop via MCP, plus the EBI OLS MCP server for ontology lookups. Covers initial install, Docker configuration, quarterly database updates, and troubleshooting.
---

# Reactome Neo4j + OLS: Claude Desktop MCP Setup

**Platform:** macOS (Apple Silicon) | **Created:** March 2026 | **Reactome release:** V94

---

## Overview

This skill guides you through:

1. **Part 1** — Running a local Reactome Neo4j database in Docker and connecting it to Claude Desktop via the `neo4j-mcp` server so you can query the database in plain English.
2. **Part 2** — Installing the OLS MCP server so Claude can look up ontology terms (GO, HP, ChEBI, EFO, and 300+ others) against the live EBI OLS API without hallucinating accession numbers.
3. **Quarterly Update SOP** — How to refresh the database after each Reactome release.

---

## Prerequisites

| Software | Version used | Notes |
|---|---|---|
| Claude Desktop | Latest | claude.ai/download — Pro plan required for MCP |
| Node.js | v24.14.0 | nodejs.org/en/download |
| Docker Desktop | 28.3.3 | Required to run the Neo4j container |
| neo4j-mcp binary | v1.4.6 | github.com/neo4j/mcp/releases |
| uv (Python package manager) | Latest | Required for OLS MCP — astral.sh/uv |
| Python | 3.10+ | Required by OLS MCP; installed via uv |

---

## Part 1 — Reactome Neo4j Setup

### Step 1 — Install Claude Desktop and subscribe to Pro

1. Download Claude Desktop from claude.ai/download and drag it to Applications.
2. Sign in with your Anthropic account.
3. Subscribe to Claude Pro ($17/month annual or $20/month monthly) — Pro is required for MCP tool support.

---

### Step 2 — Install the neo4j-mcp binary

```bash
# 1. Go to https://github.com/neo4j/mcp/releases/latest in your browser
# 2. Download: neo4j-mcp_Darwin_arm64.tar

# Extract the archive
tar -xf ~/Downloads/neo4j-mcp_Darwin_arm64.tar -C ~/Downloads/

# Make executable and move to system path
chmod +x ~/Downloads/neo4j-mcp
sudo mv ~/Downloads/neo4j-mcp /usr/local/bin/neo4j-mcp

# Verify installation
neo4j-mcp --version
# Expected output: neo4j-mcp version: v1.4.6
```

> **macOS security warning:** Go to System Settings > Privacy & Security and click "Allow Anyway", then run the verify command again.

---

### Step 3 — Download and load the Reactome database

Downloads the Reactome Neo4j dump (~500 MB) and loads it into a local Neo4j container.

```bash
# Create working directory
mkdir -p ~/reactome-neo4j

# Pull the Neo4j 4.4 Docker image
docker pull neo4j:4.4

# Download the latest Reactome database dump
curl -L https://reactome.org/download/current/reactome.graphdb.dump \
  -o ~/reactome-neo4j/reactome.graphdb.dump

# Load the dump into Neo4j
docker run --rm \
  -v ~/reactome-neo4j/reactome.graphdb.dump:/dump/reactome.graphdb.dump \
  -v ~/reactome-neo4j/data:/data \
  neo4j:4.4 \
  neo4j-admin load --from=/dump/reactome.graphdb.dump --database=graph.db --force
```

Expected final output: `Done: 73 files, 3.176GiB processed.`

---

### Step 4 — Start Neo4j with APOC plugin

```bash
docker run -d \
  --name reactome-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=none \
  -e NEO4J_dbms_default__database=graph.db \
  -e NEO4J_PLUGINS='["apoc"]' \
  -e NEO4J_dbms_security_procedures_unrestricted=apoc.* \
  -e NEO4J_dbms_security_procedures_allowlist=apoc.* \
  -v ~/reactome-neo4j/data:/data \
  neo4j:4.4
```

Verify by opening http://localhost:7474 and running:

```cypher
MATCH (n:Pathway) RETURN count(n)
// Expected result: ~23,290
```

---

### Step 5 — Configure Claude Desktop MCP for Reactome

```bash
open -e ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

If adding Reactome only (without OLS), replace the file contents with:

```json
{
  "mcpServers": {
    "neo4j-reactome": {
      "command": "/usr/local/bin/neo4j-mcp",
      "args": [
        "--neo4j-uri", "bolt://localhost:7687",
        "--neo4j-username", "neo4j",
        "--neo4j-password", "neo4j",
        "--neo4j-database", "graph.db",
        "--neo4j-read-only", "true"
      ]
    }
  }
}
```

> **Tip:** If you are also setting up OLS (Part 2), hold off on saving until you complete Part 2, Step 2 — both servers go in the same config file.

Save, then fully quit Claude Desktop (Claude menu > Quit Claude) and reopen it.

---

### Step 6 — Verify Reactome MCP connection

1. In Claude Desktop, go to **Settings > Developer**.
2. Confirm `neo4j-reactome` shows status: **running** (blue badge).
3. Open a new chat and type: `What Neo4j tools do you have available?`
4. Claude should describe the `get-schema` and `read-cypher` tools.

---

### Step 7 — Set the Reactome system prompt

At the start of each conversation where you want to query Reactome, paste:

```
You are a Reactome database expert. When I ask questions in plain English,
generate and run the appropriate read-only Cypher query against the database.
Always return displayName and stId in results.
Limit to 25 results unless I ask for more.
```

> **Tip:** Save this as a Claude Project (sidebar > Projects > New project > "Reactome") so you do not need to paste it every session.

---

## Part 2 — OLS MCP Server Setup

The OLS MCP server connects Claude Desktop to the EBI Ontology Lookup Service — over 300 biological and medical ontologies (GO, HP, EFO, ChEBI, and more). Because LLMs often hallucinate ontology accessions, this server provides a reliable live lookup path instead of guessing. No API key required.

Server: github.com/seandavi/ols-mcp-server

---

### Part 2, Step 1 — Install uv

```bash
# Install uv (macOS/Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload your shell
source ~/.zshrc   # or source ~/.bash_profile

# Verify
uv --version
```

---

### Part 2, Step 2 — Install the OLS MCP server

```bash
git clone https://github.com/seandavi/ols-mcp-server.git
cd ols-mcp-server
uv tool install .

# Verify
ols-mcp-server --help
```

`uv tool install` makes `ols-mcp-server` available system-wide on your PATH — no virtual environment activation needed.

---

### Part 2, Step 3 — Configure Claude Desktop MCP (both servers)

```bash
open -e ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Replace the file contents with the combined config:

```json
{
  "mcpServers": {
    "neo4j-reactome": {
      "command": "/usr/local/bin/neo4j-mcp",
      "args": [
        "--neo4j-uri", "bolt://localhost:7687",
        "--neo4j-username", "neo4j",
        "--neo4j-password", "neo4j",
        "--neo4j-database", "graph.db",
        "--neo4j-read-only", "true"
      ]
    },
    "ols-mcp-server": {
      "command": "ols-mcp-server",
      "args": [],
      "env": {}
    }
  }
}
```

Save, then fully quit Claude Desktop and reopen it.

> The OLS server requires no authentication or API key. It uses the public EBI OLS v2 API over HTTPS — an internet connection is required for OLS queries.

---

### Part 2, Step 4 — Verify OLS MCP connection

1. In Claude Desktop, go to **Settings > Developer**.
2. Confirm `ols-mcp-server` shows status: **running** (blue badge).
3. Open a new chat and type: `What ontology tools do you have available?`
4. Claude should describe these tools:

| Tool | Description |
|---|---|
| `search_terms` | Search for terms across all ontologies or within a specified one |
| `search_ontologies` | List and search available ontologies by name or identifier |
| `get_term_info` | Retrieve full details for a specific term by IRI and ontology |
| `get_term_children` | Get direct child terms of a given term |
| `get_term_ancestors` | Get ancestor (parent) terms of a given term |
| `find_similar_terms` | Find semantically similar terms using LLM embeddings |
| `get_ontology_info` | Retrieve metadata about a specific ontology |

---

## Quarterly Update SOP

Reactome releases approximately every 3 months. The OLS MCP server requires no periodic update — it always queries the live EBI OLS API.

### Option A — Automated update script (recommended)

An update script is provided at `~/update_reactome.sh` (see this skill directory).
Make sure Docker Desktop is running first, then:

```bash
bash ~/update_reactome.sh
```

Total time: approximately 15–30 minutes.

### Option B — Manual update steps

**1. Stop and remove the existing container**

```bash
docker stop reactome-neo4j && docker rm reactome-neo4j
```

**2. Download the new database dump**

```bash
curl -L https://reactome.org/download/current/reactome.graphdb.dump \
  -o ~/reactome-neo4j/reactome.graphdb.dump
```

**3. Load the new dump**

```bash
docker run --rm \
  -v ~/reactome-neo4j/reactome.graphdb.dump:/dump/reactome.graphdb.dump \
  -v ~/reactome-neo4j/data:/data \
  neo4j:4.4 \
  neo4j-admin load --from=/dump/reactome.graphdb.dump --database=graph.db --force
```

**4. Restart Neo4j**

```bash
docker run -d \
  --name reactome-neo4j \
  -p 7474:7474 \
  -p 7687:7687 \
  -e NEO4J_AUTH=none \
  -e NEO4J_dbms_default__database=graph.db \
  -e NEO4J_PLUGINS='["apoc"]' \
  -e NEO4J_dbms_security_procedures_unrestricted=apoc.* \
  -e NEO4J_dbms_security_procedures_allowlist=apoc.* \
  -v ~/reactome-neo4j/data:/data \
  neo4j:4.4
```

### After updating

- No changes needed to the Claude Desktop config file.
- The MCP server reconnects automatically when Claude Desktop is restarted.
- Verify: run `MATCH (n:Pathway) RETURN count(n)` in Neo4j Browser (http://localhost:7474).
- Check reactome.org/about/news to confirm which version you are now running.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| Reactome MCP shows 'failed' in Developer settings | Run `docker ps` — confirm Neo4j container is running. If not, start it with the `docker run` command in Step 4. |
| OLS MCP shows 'failed' in Developer settings | Run `ols-mcp-server --help` to confirm the binary is on your PATH. If not found, re-run `uv tool install .` from inside the `ols-mcp-server` repository folder. |
| Hammer/tools icon not visible in chat | Check Settings > Developer for 'running' status. Start a new chat and type: `What tools do you have available?` |
| Neo4j container exits immediately | Run `docker logs reactome-neo4j` and check for errors. Usually insufficient memory — close other applications. |
| Docker not running | Open Docker Desktop from Applications and wait for the whale icon in the menu bar to stop animating. |
| Cypher query returns no results | Ask Claude to first run `get-schema` to inspect database structure, then rephrase your question. |
| OLS search returns no results | Broaden your search term or omit the ontology filter. Confirm you have an active internet connection. |
| `uv` command not found after install | Run `source ~/.zshrc` (or `source ~/.bash_profile`) to reload your shell, then retry. |
| `graph.db` is unavailable error | The Neo4j database service needs to be restarted on the host. Run `docker restart reactome-neo4j` and check `docker logs reactome-neo4j` for errors. |

---

## Example Queries

### Reactome queries (paste after setting the system prompt)

```
Show me all pathways that contain a human protein with UniProt ID Q01196
Show me all events authored by [person's surname]
What reactions involve the protein RUNX1?
List all pathways in the apoptosis category
Show me the top-level pathways for Homo sapiens
What physical entities participate in pathway R-HSA-109606?
```

### OLS queries

```
Search for terms related to apoptosis in the Gene Ontology
Find the HP term for osteogenesis imperfecta and show its children
What ontologies are available for chemical compounds?
Look up the EFO term for type 2 diabetes and show its ancestors
Find all GO terms containing 'mitochondrial membrane'
What is the definition of GO:0006915?
```
