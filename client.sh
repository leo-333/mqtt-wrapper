#!/bin/sh
DOMAIN="auth.csp-staging.eng-softwarelabs.de"
CLIENT_ID="mqtt-wrapper"
REALM="default"

# lookup well-known keycloak endpoints at https://auth.csp-staging.eng-softwarelabs.de/auth/realms/default/.well-known/openid-configuration

# Request Auth
AUTH_REQUEST=$(curl -X POST \
    -d "client_id=$CLIENT_ID" \
    "https://$DOMAIN/auth/realms/$REALM/protocol/openid-connect/auth/device")
echo $AUTH_REQUEST | jq
echo "Visit $(echo $AUTH_REQUEST | jq .verification_uri_complete) to grant your device access."

DEVICE_CODE=$(echo $AUTH_REQUEST | jq .device_code | tr -d \")

# Let the Device request the access token (User must grant access via Verification URI first)
TOKEN_REQUEST=$(curl -X POST \
-d "grant_type=urn:ietf:params:oauth:grant-type:device_code" \
-d "client_id=$CLIENT_ID" \
-d "device_code=$DEVICE_CODE" \
"https://$DOMAIN/auth/realms/$REALM/protocol/openid-connect/token")
echo $TOKEN_REQUEST | jq

ACCESS_TOKEN=$(echo $TOKEN_REQUEST | jq .access_token | tr -d \")

# verify token
KEYCLOAK_PUB_KEY=$(curl https://$DOMAIN/auth/realms/$REALM/protocol/openid-connect/certs | jq)
echo $KEYCLOAK_PUB_KEY | jq