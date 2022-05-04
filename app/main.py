from fastapi import FastAPI, Websocket
from pydantic import BaseModel
import requests

app = FastAPI()

KEYCLOAK_URL = "https://auth.csp-staging.eng-softwarelabs.de"
DEVICE_CODE_ENDPOINT = "/auth/realms/default/protocol/openid-connect/auth/device"
VERNEMQ_URL = "wss://mqtt.csp-staging.eng-softwarelabs.de"

class DeviceCodeResponse(BaseModel):
    AuthURL: str
    DeviceCode: str

# HTTP Endpoint for getting an Device Code from Keycloak
@app.get("/auth/device")
async def getDeviceCode(req):
    # Proxy Request to Keycloak
    keycloakRes: DeviceCodeResponse = await requests.get(KEYCLOAK_URL + DEVICE_CODE_ENDPOINT)

    # Mail Auth URL to the User
    await sendAuthMail(keycloakRes.AuthURL)

    # Return Keycloak Response to Device
    return keycloakRes

# WS Endpoint for MQTT Requests from the Device
@app.websocket("/mqtt")
async def proxyMqtt(websocket: Websocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        
        # Check Header for JWT
        if not websocket.header.jwt:
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


def verifyJWT(jwt):
    # Check if JWT is valid by verifying its signature with Keycloaks PubKey
    return True

async def sendAuthMail(AuthURL):
    # Send an Authorization Email containing the Link returned by Keycloak to the User
    return True

async def proxyRequestToVerneMQ(data):
    # TODO make it Websocket
    return await requests.post(VERNEMQ_URL)