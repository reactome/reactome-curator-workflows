#!/usr/bin/env bash
# Quarterly Reactome Neo4j database update script.
# Run after each Reactome release. Docker Desktop must be running.
# Usage: bash ~/update_reactome.sh

set -euo pipefail

echo "=== Reactome Neo4j Quarterly Update ==="
echo ""

# Step 1: Stop and remove existing container
echo "[1/4] Stopping and removing existing Neo4j container..."
docker stop reactome-neo4j 2>/dev/null && echo "  Container stopped." || echo "  Container was not running."
docker rm reactome-neo4j 2>/dev/null && echo "  Container removed." || echo "  Container did not exist."

# Step 2: Download new dump
echo ""
echo "[2/4] Downloading latest Reactome database dump (~500 MB)..."
curl -L https://reactome.org/download/current/reactome.graphdb.dump \
  -o ~/reactome-neo4j/reactome.graphdb.dump
echo "  Download complete."

# Step 3: Load dump
echo ""
echo "[3/4] Loading database dump into Neo4j (this takes a few minutes)..."
docker run --rm \
  -v ~/reactome-neo4j/reactome.graphdb.dump:/dump/reactome.graphdb.dump \
  -v ~/reactome-neo4j/data:/data \
  neo4j:4.4 \
  neo4j-admin load --from=/dump/reactome.graphdb.dump --database=graph.db --force
echo "  Load complete."

# Step 4: Start Neo4j
echo ""
echo "[4/4] Starting Neo4j container..."
docker run -d \
  --name reactome-neo4j \
  -p 127.0.0.1:7474:7474 \
  -p 127.0.0.1:7687:7687 \
  -e NEO4J_AUTH=none \
  -e NEO4J_dbms_default__database=graph.db \
  -e NEO4J_PLUGINS='["apoc"]' \
  -e NEO4J_dbms_security_procedures_unrestricted=apoc.* \
  -e NEO4J_dbms_security_procedures_allowlist=apoc.* \
  -v ~/reactome-neo4j/data:/data \
  neo4j:4.4

echo ""
echo "=== Update complete ==="
echo ""
echo "Verify: open http://localhost:7474 and run: MATCH (n:Pathway) RETURN count(n)"
echo "Expected result: ~23,290 pathways (number increases with each release)."
echo "Check reactome.org/about/news to confirm which version you are now running."
