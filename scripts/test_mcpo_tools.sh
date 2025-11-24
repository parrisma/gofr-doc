#!/bin/bash
# Test what tools MCPO is exposing

MCPO_URL="http://localhost:8011"

echo "===== Testing MCPO Tool Exposure ====="
echo ""
echo "1. Getting OpenAPI spec from MCPO:"
echo "GET $MCPO_URL/openapi.json"
curl -s "$MCPO_URL/openapi.json" | python3 -m json.tool | head -100
echo ""
echo ""
echo "2. Listing MCP tools via MCPO:"
echo "POST $MCPO_URL/tools/list"
curl -s -X POST "$MCPO_URL/tools/list" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -m json.tool
echo ""
echo ""
echo "3. Calling help tool via MCPO:"
echo "POST $MCPO_URL/tools/call"
curl -s -X POST "$MCPO_URL/tools/call" \
  -H "Content-Type: application/json" \
  -d '{"name": "help", "arguments": {}}' | python3 -m json.tool | head -200
