#!/bin/bash
# Script to set up Kong consumers and API keys for WaddleBot services

KONG_ADMIN_URL="http://localhost:8001"

echo "Setting up Kong consumers and API keys for WaddleBot..."

# Function to create consumer with API key
create_consumer() {
    local username=$1
    local api_key=$2
    local group=$3
    
    echo "Creating consumer: $username"
    
    # Create consumer
    curl -X POST $KONG_ADMIN_URL/consumers \
        -H "Content-Type: application/json" \
        -d "{\"username\": \"$username\"}"
    
    # Add API key
    curl -X POST $KONG_ADMIN_URL/consumers/$username/key-auth \
        -H "Content-Type: application/json" \
        -d "{\"key\": \"$api_key\"}"
    
    # Add to ACL group
    if [ ! -z "$group" ]; then
        curl -X POST $KONG_ADMIN_URL/consumers/$username/acls \
            -H "Content-Type: application/json" \
            -d "{\"group\": \"$group\"}"
    fi
    
    echo "Created consumer $username with API key $api_key"
}

# Wait for Kong to be ready
echo "Waiting for Kong Admin API..."
until curl -f $KONG_ADMIN_URL/status > /dev/null 2>&1; do
    echo "Kong not ready, waiting..."
    sleep 5
done

echo "Kong is ready. Creating consumers..."

# Create collector consumers
create_consumer "twitch-collector-1" "wbot_twitch_collector_1_$(openssl rand -hex 16)" "collectors"
create_consumer "discord-collector-1" "wbot_discord_collector_1_$(openssl rand -hex 16)" "collectors"
create_consumer "slack-collector-1" "wbot_slack_collector_1_$(openssl rand -hex 16)" "collectors"

# Create admin consumers
create_consumer "router-admin" "wbot_router_admin_$(openssl rand -hex 16)" "admins"
create_consumer "marketplace-admin" "wbot_marketplace_admin_$(openssl rand -hex 16)" "admins"

# Create interaction module consumers
create_consumer "interaction-module-1" "wbot_interaction_1_$(openssl rand -hex 16)" "interactions"
create_consumer "webhook-handler" "wbot_webhook_$(openssl rand -hex 16)" "webhooks"

echo "Consumer setup complete!"

# Display all consumers
echo -e "\nCreated consumers:"
curl -s $KONG_ADMIN_URL/consumers | jq -r '.data[] | "\(.username): \(.id)"'

echo -e "\nTo view API keys, run:"
echo "curl -s $KONG_ADMIN_URL/consumers/{username}/key-auth"