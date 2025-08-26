#!/bin/bash

echo "Testing key Docker builds for WaddleBot modules..."

# Test AI Interaction (already working)
echo -n "Testing ai_interaction_module... "
if docker build -f ai_interaction_module/Dockerfile -t test-ai --quiet . >/dev/null 2>&1; then
    echo "✅ SUCCESS"
    docker rmi test-ai >/dev/null 2>&1
else
    echo "❌ FAILED"
fi

# Test Identity Core (already working)
echo -n "Testing identity_core_module... "
if docker build -f identity_core_module/Dockerfile -t test-identity --quiet . >/dev/null 2>&1; then
    echo "✅ SUCCESS"
    docker rmi test-identity >/dev/null 2>&1
else
    echo "❌ FAILED"
fi

# Test Portal Module
echo -n "Testing portal_module... "
if docker build -f portal_module/Dockerfile -t test-portal --quiet . >/dev/null 2>&1; then
    echo "✅ SUCCESS"
    docker rmi test-portal >/dev/null 2>&1
else
    echo "❌ FAILED - Dockerfile needs fixing"
fi

# Test Twitch Module
echo -n "Testing twitch_module... "
if docker build -f twitch_module/Dockerfile -t test-twitch --quiet . >/dev/null 2>&1; then
    echo "✅ SUCCESS"
    docker rmi test-twitch >/dev/null 2>&1
else
    echo "❌ FAILED - Dockerfile needs fixing"
fi

echo "Build testing complete!"