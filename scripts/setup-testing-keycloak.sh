#!/bin/bash

# Configuration
KC_IMAGE="quay.io/keycloak/keycloak:latest"
KC_CONTAINER_NAME="keycloak"
KC_ADMIN_USER="admin"
KC_ADMIN_PASSWORD="Admin1234@#$"
KC_REALM_NAME="globaleaks"
KC_NEW_USER="admin"
KC_NEW_USER_PASSWORD="Admin1234@#$"
KC_NEW_USER_EMAIL="globaleaks-admin@mailinator.com"
KC_CLIENT_ID="globaleaks"
KC_CLIENT_SECRET="globaleaks"

# Pull Keycloak image
echo "Pulling Keycloak Docker image..."
docker pull $KC_IMAGE

# Remove any existing Keycloak container
docker rm -f $KC_CONTAINER_NAME &>/dev/null

# Start Keycloak container
echo "Starting Keycloak container..."
docker run -d --name $KC_CONTAINER_NAME \
  -p 9090:8080 \
  -e KEYCLOAK_ADMIN=$KC_ADMIN_USER \
  -e KEYCLOAK_ADMIN_PASSWORD=$KC_ADMIN_PASSWORD \
  -e KEYCLOAK_HTTP_CORS=true \
  -e KEYCLOAK_HTTP_CORS_ALLOWED_ORIGINS=$KC_CORS_ALLOWED_ORIGINS \
  -e KEYCLOAK_HTTP_CORS_ALLOWED_METHODS="GET,POST,PUT,DELETE" \
  -e KEYCLOAK_HTTP_CORS_ALLOWED_HEADERS="Authorization,Content-Type" \
  $KC_IMAGE start-dev


# Wait for Keycloak to start
echo "Waiting for Keycloak to start..."
until $(curl --output /dev/null --silent --head --fail http://127.0.0.1:9090/realms/master); do
    printf '.'
    sleep 5
done
echo " Keycloak is ready!"

# Get admin access token
echo "Fetching admin access token..."
TOKEN=$(curl -s -X POST "http://127.0.0.1:9090/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=$KC_ADMIN_USER" \
  -d "password=$KC_ADMIN_PASSWORD" \
  -d "grant_type=password" \
  -d "client_id=admin-cli" | jq -r '.access_token')

if [[ -z "$TOKEN" || "$TOKEN" == "null" ]]; then
    echo "Failed to retrieve admin token. Check Keycloak logs: docker logs $KC_CONTAINER_NAME"
    exit 1
fi

# Create a new realm
echo "Creating realm: $KC_REALM_NAME..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:9090/admin/realms" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "realm": "'$KC_REALM_NAME'",
        "enabled": true
      }')

if [[ "$RESPONSE" -ne 201 ]]; then
    echo "Failed to create realm. Response code: $RESPONSE"
    exit 1
fi

# Create a new user
echo "Creating user: $KC_NEW_USER..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:9090/admin/realms/$KC_REALM_NAME/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "username": "'$KC_NEW_USER'",
        "email": "'$KC_NEW_USER_EMAIL'",
        "firstName": "'$KC_NEW_USER'",
        "lastName": "'$KC_NEW_USER'",
        "enabled": true,
        "credentials": [{
            "type": "password",
            "value": "'$KC_NEW_USER_PASSWORD'",
            "temporary": false
        }]
      }')

if [[ "$RESPONSE" -ne 201 ]]; then
    echo "Failed to create user. Response code: $RESPONSE"
    exit 1
fi

# Create a new client (application)
echo "Creating client: $KC_CLIENT_ID..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://127.0.0.1:9090/admin/realms/$KC_REALM_NAME/clients" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "clientId": "'$KC_CLIENT_ID'",
        "secret": "'$KC_CLIENT_SECRET'",
        "directAccessGrantsEnabled": true,
        "publicClient": true,
        "redirectUris": ["https://127.0.0.1:8443/*"]
      }')

if [[ "$RESPONSE" -ne 201 ]]; then
    echo "Failed to create client. Response code: $RESPONSE"
    exit 1
fi

echo "✅ Setup complete! Access Keycloak at: http://127.0.0.1:9090"
echo "Login to $KC_REALM_NAME realm with username: $KC_NEW_USER and password: $KC_NEW_USER_PASSWORD"
