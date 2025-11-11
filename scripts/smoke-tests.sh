#!/bin/bash

# VBRPG Smoke Tests
# Feature 002: Room Join & AI Agent Management
#
# Runs basic smoke tests to verify core functionality after deployment.
# These tests use the actual API endpoints and validate real-time behavior.

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
API_BASE="$BACKEND_URL/api/v1"
TEST_TIMEOUT=10
VERBOSE="${VERBOSE:-false}"

# Test state tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Utility functions
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

run_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    info "Test $TESTS_RUN: $1"
}

# Check if backend is running
check_backend_health() {
    info "=========================================="
    info "Pre-flight: Checking backend health..."
    info "=========================================="
    
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health" 2>&1 || echo "000")
    
    if [ "$HEALTH_RESPONSE" = "200" ]; then
        success "Backend is healthy (HTTP $HEALTH_RESPONSE)"
        return 0
    else
        fail "Backend health check failed (HTTP $HEALTH_RESPONSE)"
        fail "Is the backend running at $BACKEND_URL?"
        exit 1
    fi
}

# Test 1: Create guest player
test_create_guest_player() {
    run_test "Create guest player account"
    
    RESPONSE=$(curl -s -X POST "$API_BASE/players/guest" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}" 2>&1)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
        PLAYER_ID=$(echo "$BODY" | grep -o '"player_id":"[^"]*"' | cut -d'"' -f4)
        
        if [ -n "$PLAYER_ID" ]; then
            success "Created guest player: $PLAYER_ID"
            echo "$PLAYER_ID" > /tmp/smoke_test_player_id.txt
            return 0
        else
            fail "No player_id in response"
            [ "$VERBOSE" = "true" ] && echo "$BODY"
            return 1
        fi
    else
        fail "Failed to create guest player (HTTP $HTTP_CODE)"
        [ "$VERBOSE" = "true" ] && echo "$BODY"
        return 1
    fi
}

# Test 2: Create room
test_create_room() {
    run_test "Create game room"
    
    PLAYER_ID=$(cat /tmp/smoke_test_player_id.txt 2>/dev/null || echo "")
    
    if [ -z "$PLAYER_ID" ]; then
        fail "No player ID from previous test"
        return 1
    fi
    
    RESPONSE=$(curl -s -X POST "$API_BASE/rooms/create" \
        -H "Content-Type: application/json" \
        -d "{
            \"creator_id\": \"$PLAYER_ID\",
            \"game_type\": \"crime-scene\",
            \"max_players\": 4,
            \"difficulty\": \"medium\",
            \"turn_time_limit\": 60,
            \"use_ai_narrator\": true
        }" \
        -w "\n%{http_code}" 2>&1)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
        ROOM_CODE=$(echo "$BODY" | grep -o '"room_code":"[^"]*"' | cut -d'"' -f4 || echo "$BODY" | grep -o '"code":"[^"]*"' | cut -d'"' -f4)
        
        if [ -n "$ROOM_CODE" ]; then
            success "Created room: $ROOM_CODE"
            echo "$ROOM_CODE" > /tmp/smoke_test_room_code.txt
            return 0
        else
            fail "No room_code in response"
            [ "$VERBOSE" = "true" ] && echo "$BODY"
            return 1
        fi
    else
        fail "Failed to create room (HTTP $HTTP_CODE)"
        [ "$VERBOSE" = "true" ] && echo "$BODY"
        return 1
    fi
}

# Test 3: Join room (second player)
test_join_room() {
    run_test "Second player joins room"
    
    ROOM_CODE=$(cat /tmp/smoke_test_room_code.txt 2>/dev/null || echo "")
    
    if [ -z "$ROOM_CODE" ]; then
        fail "No room code from previous test"
        return 1
    fi
    
    # Create second guest player
    RESPONSE2=$(curl -s -X POST "$API_BASE/players/guest" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}" 2>&1)
    
    HTTP_CODE2=$(echo "$RESPONSE2" | tail -1)
    BODY2=$(echo "$RESPONSE2" | head -n -1)
    
    if [ "$HTTP_CODE2" != "201" ] && [ "$HTTP_CODE2" != "200" ]; then
        fail "Failed to create second guest player (HTTP $HTTP_CODE2)"
        return 1
    fi
    
    PLAYER2_ID=$(echo "$BODY2" | grep -o '"player_id":"[^"]*"' | cut -d'"' -f4)
    echo "$PLAYER2_ID" > /tmp/smoke_test_player2_id.txt
    
    # Join room
    RESPONSE=$(curl -s -X POST "$API_BASE/rooms/$ROOM_CODE/join" \
        -H "Content-Type: application/json" \
        -d "{\"player_id\": \"$PLAYER2_ID\"}" \
        -w "\n%{http_code}" 2>&1)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        PARTICIPANT_COUNT=$(echo "$BODY" | grep -o '"current_participant_count":[0-9]*' | grep -o '[0-9]*$')
        
        if [ "$PARTICIPANT_COUNT" = "2" ]; then
            success "Second player joined (participants: $PARTICIPANT_COUNT)"
            return 0
        else
            warn "Unexpected participant count: $PARTICIPANT_COUNT (expected 2)"
            [ "$VERBOSE" = "true" ] && echo "$BODY"
            return 0
        fi
    else
        fail "Failed to join room (HTTP $HTTP_CODE)"
        [ "$VERBOSE" = "true" ] && echo "$BODY"
        return 1
    fi
}

# Test 4: Add AI agent
test_add_ai_agent() {
    run_test "Owner adds AI agent to room"
    
    ROOM_CODE=$(cat /tmp/smoke_test_room_code.txt 2>/dev/null || echo "")
    OWNER_ID=$(cat /tmp/smoke_test_player_id.txt 2>/dev/null || echo "")
    
    if [ -z "$ROOM_CODE" ] || [ -z "$OWNER_ID" ]; then
        fail "Missing room code or owner ID from previous tests"
        return 1
    fi
    
    RESPONSE=$(curl -s -X POST "$API_BASE/rooms/$ROOM_CODE/ai-agents" \
        -H "Content-Type: application/json" \
        -d "{\"owner_player_id\": \"$OWNER_ID\"}" \
        -w "\n%{http_code}" 2>&1)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "201" ]; then
        AI_AGENT_NAME=$(echo "$BODY" | grep -o '"player_name":"[^"]*"' | cut -d'"' -f4)
        AI_AGENT_ID=$(echo "$BODY" | grep -o '"player_id":"[^"]*"' | cut -d'"' -f4)
        
        if [ -n "$AI_AGENT_NAME" ]; then
            success "Added AI agent: $AI_AGENT_NAME"
            echo "$AI_AGENT_ID" > /tmp/smoke_test_ai_id.txt
            return 0
        else
            warn "AI agent added but no name in response"
            [ "$VERBOSE" = "true" ] && echo "$BODY"
            return 0
        fi
    else
        fail "Failed to add AI agent (HTTP $HTTP_CODE)"
        [ "$VERBOSE" = "true" ] && echo "$BODY"
        return 1
    fi
}

# Test 5: Get room details
test_get_room_details() {
    run_test "Get room details"
    
    ROOM_CODE=$(cat /tmp/smoke_test_room_code.txt 2>/dev/null || echo "")
    
    if [ -z "$ROOM_CODE" ]; then
        fail "No room code from previous test"
        return 1
    fi
    
    RESPONSE=$(curl -s -X GET "$API_BASE/rooms/$ROOM_CODE" \
        -w "\n%{http_code}" 2>&1)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        PARTICIPANT_COUNT=$(echo "$BODY" | grep -o '"current_participant_count":[0-9]*' | grep -o '[0-9]*$' || echo "$BODY" | grep -o '"current_players":[0-9]*' | grep -o '[0-9]*$')
        
        if [ "$PARTICIPANT_COUNT" = "3" ]; then
            success "Room has 3 participants (2 humans + 1 AI)"
            return 0
        else
            warn "Participant count: $PARTICIPANT_COUNT (expected 3)"
            [ "$VERBOSE" = "true" ] && echo "$BODY"
            return 0
        fi
    else
        fail "Failed to get room details (HTTP $HTTP_CODE)"
        [ "$VERBOSE" = "true" ] && echo "$BODY"
        return 1
    fi
}

# Test 6: Remove AI agent
test_remove_ai_agent() {
    run_test "Owner removes AI agent from room"
    
    ROOM_CODE=$(cat /tmp/smoke_test_room_code.txt 2>/dev/null || echo "")
    OWNER_ID=$(cat /tmp/smoke_test_player_id.txt 2>/dev/null || echo "")
    AI_AGENT_ID=$(cat /tmp/smoke_test_ai_id.txt 2>/dev/null || echo "")
    
    if [ -z "$ROOM_CODE" ] || [ -z "$OWNER_ID" ] || [ -z "$AI_AGENT_ID" ]; then
        fail "Missing room code, owner ID, or AI agent ID from previous tests"
        return 1
    fi
    
    RESPONSE=$(curl -s -X DELETE "$API_BASE/rooms/$ROOM_CODE/ai-agents/$AI_AGENT_ID" \
        -H "Content-Type: application/json" \
        -d "{\"owner_player_id\": \"$OWNER_ID\"}" \
        -w "\n%{http_code}" 2>&1)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    
    if [ "$HTTP_CODE" = "204" ]; then
        success "Removed AI agent"
        return 0
    else
        fail "Failed to remove AI agent (HTTP $HTTP_CODE)"
        [ "$VERBOSE" = "true" ] && echo "$RESPONSE"
        return 1
    fi
}

# Test 7: Leave room
test_leave_room() {
    run_test "Second player leaves room"
    
    ROOM_CODE=$(cat /tmp/smoke_test_room_code.txt 2>/dev/null || echo "")
    PLAYER2_ID=$(cat /tmp/smoke_test_player2_id.txt 2>/dev/null || echo "")
    
    if [ -z "$ROOM_CODE" ] || [ -z "$PLAYER2_ID" ]; then
        fail "Missing room code or player 2 ID from previous tests"
        return 1
    fi
    
    RESPONSE=$(curl -s -X DELETE "$API_BASE/rooms/$ROOM_CODE/participants/$PLAYER2_ID" \
        -w "\n%{http_code}" 2>&1)
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    
    if [ "$HTTP_CODE" = "204" ]; then
        success "Player left room"
        return 0
    else
        fail "Failed to leave room (HTTP $HTTP_CODE)"
        [ "$VERBOSE" = "true" ] && echo "$RESPONSE"
        return 1
    fi
}

# Test 8: Room capacity enforcement
test_room_capacity() {
    run_test "Room capacity enforcement (join full room)"
    
    ROOM_CODE=$(cat /tmp/smoke_test_room_code.txt 2>/dev/null || echo "")
    
    if [ -z "$ROOM_CODE" ]; then
        fail "No room code from previous test"
        return 1
    fi
    
    # Add 3 more players to fill room (current: 1 owner + 0 after leave = 1)
    # Room max is 4, so add 3 more
    for i in {1..4}; do
        RESPONSE=$(curl -s -X POST "$API_BASE/players/guest" \
            -H "Content-Type: application/json" 2>&1)
        EXTRA_PLAYER_ID=$(echo "$RESPONSE" | grep -o '"player_id":"[^"]*"' | cut -d'"' -f4)
        
        JOIN_RESPONSE=$(curl -s -X POST "$API_BASE/rooms/$ROOM_CODE/join" \
            -H "Content-Type: application/json" \
            -d "{\"player_id\": \"$EXTRA_PLAYER_ID\"}" \
            -w "\n%{http_code}" 2>&1)
        
        JOIN_HTTP_CODE=$(echo "$JOIN_RESPONSE" | tail -1)
        
        # After 3 successful joins (1 owner + 3 = 4), 4th should fail with 409
        if [ $i -eq 4 ]; then
            if [ "$JOIN_HTTP_CODE" = "409" ]; then
                success "Room correctly rejected 5th player (HTTP 409)"
                return 0
            else
                fail "Expected HTTP 409 for full room, got $JOIN_HTTP_CODE"
                return 1
            fi
        fi
    done
}

# Cleanup function
cleanup() {
    info "=========================================="
    info "Cleaning up test data..."
    info "=========================================="
    
    rm -f /tmp/smoke_test_*.txt
    
    success "Cleanup completed"
}

# Main execution
main() {
    info "=========================================="
    info "VBRPG Smoke Tests - Feature 002"
    info "Backend: $BACKEND_URL"
    info "=========================================="
    echo ""
    
    # Pre-flight checks
    check_backend_health
    echo ""
    
    # Run tests
    info "=========================================="
    info "Running Smoke Tests..."
    info "=========================================="
    echo ""
    
    test_create_guest_player
    echo ""
    
    test_create_room
    echo ""
    
    test_join_room
    echo ""
    
    test_add_ai_agent
    echo ""
    
    test_get_room_details
    echo ""
    
    test_remove_ai_agent
    echo ""
    
    test_leave_room
    echo ""
    
    test_room_capacity
    echo ""
    
    # Cleanup
    cleanup
    echo ""
    
    # Summary
    info "=========================================="
    info "Test Summary"
    info "=========================================="
    info "Tests Run:    $TESTS_RUN"
    success "Tests Passed: $TESTS_PASSED"
    
    if [ $TESTS_FAILED -gt 0 ]; then
        fail "Tests Failed: $TESTS_FAILED"
        echo ""
        fail "SMOKE TESTS FAILED"
        exit 1
    else
        echo ""
        success "ALL SMOKE TESTS PASSED ✓"
        exit 0
    fi
}

# Run main function
main
