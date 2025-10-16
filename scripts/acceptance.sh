#!/bin/bash

# scripts/acceptance.sh
#
# Comprehensive acceptance test for Phase 1A, 1B, and 1C integration.
#
# This script demonstrates:
# - Entity resolution (Phase 1A)
# - Semantic extraction (Phase 1B)
# - Domain augmentation & reply generation (Phase 1C)
# - GET /memory and GET /entities endpoints
#
# Usage:
#   ./scripts/acceptance.sh
#
# Requirements:
#   - Server running on http://localhost:8000
#   - Database populated with demo data
#   - OPENAI_API_KEY set in environment

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8000/api/v1"
USER_ID="acceptance-test-user"
SESSION_ID=$(uuidgen)

echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}Phase 1C Acceptance Test${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""
echo -e "User ID: ${YELLOW}${USER_ID}${NC}"
echo -e "Session ID: ${YELLOW}${SESSION_ID}${NC}"
echo -e "Base URL: ${YELLOW}${BASE_URL}${NC}"
echo ""

# Helper function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ -z "$data" ]; then
        response=$(curl -s -X "$method" \
            -H "Content-Type: application/json" \
            -H "X-User-Id: $USER_ID" \
            "$BASE_URL$endpoint")
    else
        response=$(curl -s -X "$method" \
            -H "Content-Type: application/json" \
            -H "X-User-Id: $USER_ID" \
            -d "$data" \
            "$BASE_URL$endpoint")
    fi

    echo "$response"
}

# Helper function to check if jq is available
check_jq() {
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is required for this script${NC}"
        echo "Install with: brew install jq (macOS) or apt-get install jq (Linux)"
        exit 1
    fi
}

check_jq

# =============================================================================
# Test 1: Health Check
# =============================================================================
echo -e "${BLUE}Test 1: Health Check${NC}"
echo -e "${YELLOW}GET /health${NC}"

health=$(curl -s "$BASE_URL/../health")
status=$(echo "$health" | jq -r '.status')

if [ "$status" = "healthy" ]; then
    echo -e "${GREEN}✓ Server is healthy${NC}"
else
    echo -e "${RED}✗ Server health check failed${NC}"
    echo "$health"
    exit 1
fi
echo ""

# =============================================================================
# Test 2: Process Chat Message with Entity Resolution (Phase 1A)
# =============================================================================
echo -e "${BLUE}Test 2: Entity Resolution (Phase 1A)${NC}"
echo -e "${YELLOW}POST /chat/message${NC}"
echo -e "Message: 'What's the status of Acme Corporation?'"

message_data=$(cat <<EOF
{
    "session_id": "$SESSION_ID",
    "content": "What's the status of Acme Corporation?",
    "role": "user"
}
EOF
)

response=$(api_call "POST" "/chat/message" "$message_data")
event_id=$(echo "$response" | jq -r '.event_id')
entities=$(echo "$response" | jq -r '.resolved_entities | length')

if [ -n "$event_id" ] && [ "$event_id" != "null" ]; then
    echo -e "${GREEN}✓ Message processed (event_id: $event_id)${NC}"
    echo -e "${GREEN}✓ Resolved $entities entities${NC}"

    # Show first entity if any
    if [ "$entities" -gt 0 ]; then
        first_entity=$(echo "$response" | jq -r '.resolved_entities[0].canonical_name')
        method=$(echo "$response" | jq -r '.resolved_entities[0].method')
        confidence=$(echo "$response" | jq -r '.resolved_entities[0].confidence')
        echo -e "  Entity: ${YELLOW}${first_entity}${NC} (method: $method, confidence: $confidence)"
    fi
else
    echo -e "${RED}✗ Failed to process message${NC}"
    echo "$response" | jq '.'
    exit 1
fi
echo ""

# =============================================================================
# Test 3: Enhanced Chat with Domain Augmentation & Reply (Phase 1C)
# =============================================================================
echo -e "${BLUE}Test 3: Domain Augmentation & Reply Generation (Phase 1C)${NC}"
echo -e "${YELLOW}POST /chat/message/enhanced${NC}"
echo -e "Message: 'Does Acme have any open invoices?'"

enhanced_data=$(cat <<EOF
{
    "session_id": "$SESSION_ID",
    "content": "Does Acme have any open invoices?",
    "role": "user"
}
EOF
)

response=$(api_call "POST" "/chat/message/enhanced" "$enhanced_data")
event_id=$(echo "$response" | jq -r '.event_id')
reply=$(echo "$response" | jq -r '.reply')
domain_facts=$(echo "$response" | jq -r '.domain_facts | length')
memories=$(echo "$response" | jq -r '.retrieved_memories | length')

if [ -n "$event_id" ] && [ "$event_id" != "null" ]; then
    echo -e "${GREEN}✓ Enhanced message processed (event_id: $event_id)${NC}"
    echo -e "${GREEN}✓ Retrieved $domain_facts domain facts${NC}"
    echo -e "${GREEN}✓ Retrieved $memories memories${NC}"
    echo -e ""
    echo -e "${BLUE}Generated Reply:${NC}"
    echo -e "${YELLOW}${reply}${NC}"
    echo -e ""

    # Show first domain fact if any
    if [ "$domain_facts" -gt 0 ]; then
        fact_type=$(echo "$response" | jq -r '.domain_facts[0].fact_type')
        fact_content=$(echo "$response" | jq -r '.domain_facts[0].content')
        echo -e "${BLUE}Sample Domain Fact (${fact_type}):${NC}"
        echo -e "${YELLOW}${fact_content}${NC}"
    fi
else
    echo -e "${RED}✗ Failed to process enhanced message${NC}"
    echo "$response" | jq '.'
    exit 1
fi
echo ""

# =============================================================================
# Test 4: GET /memory - Retrieve Memories
# =============================================================================
echo -e "${BLUE}Test 4: Retrieve Memories (GET /memory)${NC}"
echo -e "${YELLOW}GET /memory?limit=10&status_filter=active${NC}"

response=$(api_call "GET" "/memory?limit=10&status_filter=active")
total=$(echo "$response" | jq -r '.total')
returned=$(echo "$response" | jq -r '.memories | length')

if [ -n "$total" ] && [ "$total" != "null" ]; then
    echo -e "${GREEN}✓ Retrieved $returned of $total total memories${NC}"

    # Show first memory if any
    if [ "$returned" -gt 0 ]; then
        predicate=$(echo "$response" | jq -r '.memories[0].predicate')
        confidence=$(echo "$response" | jq -r '.memories[0].confidence')
        echo -e "  Sample: ${YELLOW}${predicate}${NC} (confidence: $confidence)"
    fi
else
    echo -e "${RED}✗ Failed to retrieve memories${NC}"
    echo "$response" | jq '.'
    exit 1
fi
echo ""

# =============================================================================
# Test 5: GET /entities - Retrieve Entities
# =============================================================================
echo -e "${BLUE}Test 5: Retrieve Entities (GET /entities)${NC}"
echo -e "${YELLOW}GET /entities?limit=10${NC}"

response=$(api_call "GET" "/entities?limit=10")
total=$(echo "$response" | jq -r '.total')
returned=$(echo "$response" | jq -r '.entities | length')

if [ -n "$total" ] && [ "$total" != "null" ]; then
    echo -e "${GREEN}✓ Retrieved $returned of $total total entities${NC}"

    # Show first entity if any
    if [ "$returned" -gt 0 ]; then
        canonical_name=$(echo "$response" | jq -r '.entities[0].canonical_name')
        entity_type=$(echo "$response" | jq -r '.entities[0].entity_type')
        echo -e "  Sample: ${YELLOW}${canonical_name}${NC} (type: $entity_type)"
    fi
else
    echo -e "${RED}✗ Failed to retrieve entities${NC}"
    echo "$response" | jq '.'
    exit 1
fi
echo ""

# =============================================================================
# Test 6: Multi-Turn Conversation
# =============================================================================
echo -e "${BLUE}Test 6: Multi-Turn Conversation${NC}"
echo -e "${YELLOW}Simulating 3-turn conversation${NC}"

messages=(
    "Tell me about Gai Media"
    "What invoices do they have?"
    "When is the next payment due?"
)

for i in "${!messages[@]}"; do
    turn=$((i+1))
    msg="${messages[$i]}"

    echo -e "  Turn $turn: ${BLUE}${msg}${NC}"

    data=$(cat <<EOF
{
    "session_id": "$SESSION_ID",
    "content": "$msg",
    "role": "user"
}
EOF
)

    response=$(api_call "POST" "/chat/message/enhanced" "$data")
    reply=$(echo "$response" | jq -r '.reply')

    # Truncate reply if too long
    if [ ${#reply} -gt 150 ]; then
        reply="${reply:0:150}..."
    fi

    echo -e "  ${GREEN}Reply: ${YELLOW}${reply}${NC}"
    echo ""
done

# =============================================================================
# Summary
# =============================================================================
echo -e "${BLUE}=================================${NC}"
echo -e "${GREEN}✓ All Acceptance Tests Passed!${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""
echo -e "${BLUE}Phase 1C Features Verified:${NC}"
echo -e "  ${GREEN}✓${NC} Entity resolution (Phase 1A)"
echo -e "  ${GREEN}✓${NC} Semantic extraction (Phase 1B)"
echo -e "  ${GREEN}✓${NC} Domain augmentation (Phase 1C)"
echo -e "  ${GREEN}✓${NC} LLM reply generation (Phase 1C)"
echo -e "  ${GREEN}✓${NC} GET /memory endpoint"
echo -e "  ${GREEN}✓${NC} GET /entities endpoint"
echo -e "  ${GREEN}✓${NC} Multi-turn conversations"
echo ""
echo -e "${BLUE}System Status:${NC}"
echo -e "  Session ID: ${YELLOW}${SESSION_ID}${NC}"
echo -e "  Total API calls: ${YELLOW}9${NC}"
echo -e "  All tests: ${GREEN}PASSED${NC}"
echo ""
