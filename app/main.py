from fastapi import FastAPI, WebSocket, status, Cookie, Query, Depends
from typing import Optional
import requests
import python_jwt as jwt
import smtplib, ssl

app = FastAPI()

KEYCLOAK_URL = "https://auth.csp-staging.eng-softwarelabs.de"
RESOURCE_OWNER_MAIL = "jonas.leitner@eng-its.de"
CLIENT_ID = "mqtt-wrapper"
DEVICE_CODE_ENDPOINT = "/auth/realms/default/protocol/openid-connect/auth/device"
PUB_KEY_ENDPOINT = "/auth/realms/default"
VERNEMQ_URL = "wss://mqtt.csp-staging.eng-softwarelabs.de"

keycloakPubKey = None

@app.on_event("startup")
async def startup_event():
    # Pull the PubKey from Keycloak
    keycloakRes = requests.get(KEYCLOAK_URL + PUB_KEY_ENDPOINT)
    keycloakPubKey = keycloakRes.json()['public_key']

# HTTP Endpoint for getting an Device Code from Keycloak
@app.get("/auth/device")
async def getDeviceCode():
    # Proxy Request to Keycloak
    keycloakRes = requests.post(KEYCLOAK_URL + DEVICE_CODE_ENDPOINT, {"client_id": CLIENT_ID}).json()

    # Mail Auth URL to the User
    if sendAuthMail(keycloakRes.verification_uri_complete):
        # Return Keycloak Response to Device
        return keycloakRes
    else:
        return {"error": "sending mail failed"}

async def get_cookie_or_token(
    websocket: WebSocket,
    session: Optional[str] = Cookie(None),
    token: Optional[str] = Query(None),
):
    #if session is None and token is None:
    #    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return session or token


# WS Endpoint for MQTT Requests from the Device
@app.websocket("/mqtt")
async def websocket_endpoint(
    websocket: WebSocket
):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        #print(websocket)
        print(websocket.headers["Cookie"])
        print(data)
        continue
        # Check Header for JWT
        if not websocket.Headers:
            await websocket.send_text("JWT Missing")
            continue

        jwt = websocket.header.jwt

        # Verify Authorization
        if not verifyJWT(jwt): 
            await websocket.send_text("JWT invalid")
            continue
        
        # Proxy MQTT Request to VerneMQ
        vernemqRes = await proxyRequestToVerneMQ(data)
        
        # Return VerneMQ Response
        await websocket.send_text(vernemqRes)


def verifyJWT(token):
    # Check if JWT is valid by verifying its signature with Keycloaks PubKey
    header, claims = jwt.verify_jwt(token, keycloakPubKey, ['RS256'])
    print(header)
    print(claims)
    

async def sendAuthMail(AuthURL):
    # Send an Authorization Email containing the Link returned by Keycloak to the User


    port = 465  # For SSL
    password = input("Type your password and press enter: ")

    # Create a secure SSL context
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login("my@gmail.com", password)
    # TODO: Send email here

    return True

async def proxyRequestToVerneMQ(data):
    # TODO make it Websocket
    return await requests.post(VERNEMQ_URL)