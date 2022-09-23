from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Cookie, Query, Depends
from typing import Optional
import requests
import python_jwt as jwt
import smtplib, ssl
from email.mime.text import MIMEText

app = FastAPI()

KEYCLOAK_URL = "https://auth.csp-staging.eng-softwarelabs.de"
RESOURCE_OWNER_MAIL = "jonas.leitner@eng-its.de"
CLIENT_ID = "mqtt-wrapper"
DEVICE_CODE_ENDPOINT = "/auth/realms/default/protocol/openid-connect/auth/device"
PUB_KEY_ENDPOINT = "/auth/realms/default"
VERNEMQ_URL = "wss://mqtt.csp-staging.eng-softwarelabs.de"

# SMTP Email Credentials
SMTP_SENDER_EMAIL = "noreply@dlr.de"
SMTP_PASSWORD = "1234"
SMTP_PROXY = "smtp.gmail.com"
SMTP_PORT = 465
SMTP_RECEIVERS = ["jonas.leitner@eng-its.de"]

keycloak_pub_key = None


@app.on_event("startup")
async def startup_event():
    global keycloak_pub_key
    # Pull the PubKey from Keycloak
    keycloak_res = requests.get(KEYCLOAK_URL + PUB_KEY_ENDPOINT)
    if keycloak_res.status_code == 200:
        keycloak_pub_key = keycloak_res.json()['public_key']
    else:
        print('Keycloak seems to be down, exiting...')
        exit(1)

# HTTP Endpoint for getting an Device Code from Keycloak
@app.get("/auth/device")
async def get_device_code():
    # Proxy Request to Keycloak
    keycloak_res = requests.post(KEYCLOAK_URL + DEVICE_CODE_ENDPOINT, {"client_id": CLIENT_ID}).json()

    # Mail Auth URL to the User
    send_auth_mail(keycloak_res.verification_uri_complete)
    # Return Keycloak Response to Device
    return keycloak_res


async def get_cookie_or_token(
        websocket: WebSocket,
        session: Optional[str] = Cookie(None),
        token: Optional[str] = Query(None),
):
    # if session is None and token is None:
    #    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return session or token


# WS Endpoint for MQTT Requests from the Device
@app.websocket("/mqtt")
async def websocket_endpoint(
        websocket: WebSocket
):
    await websocket.accept()
    while True:
        try:
            # Accept the initial MQTT Connection
            #await websocket.send_text("CONNACK")
            # Wait for the JWT
            data = await websocket.receive()
            print(data)
            # Check Header for JWT
            cookie = None
            try:
                cookie = websocket.headers["Cookie"]
            except KeyError:
                print("Cookie not found")
                await websocket.send_text("JWT Missing")
                continue

            # Verify Authorization
            if not verify_jwt(cookie):
                await websocket.send_text("JWT invalid")
                continue


            # JWT valid, lets accept the connection
            await websocket.send_text("CONNACK")

            # Proxy MQTT Request to VerneMQ
            # vernemq_res = await proxy_request_to_vernemq(data)

            # Return VerneMQ Response
            await websocket.send_text(vernemq_res.json())
        except WebSocketDisconnect:
            print("Client has disconnected.")
            break


def verify_jwt(token):
    # Check if JWT is valid by verifying its signature with Keycloaks PubKey
    try:
        header, claims = jwt.verify_jwt(token, keycloak_pub_key, ['RS256'])
        print(header)
        print(claims)
    except:
        return False

    return True


def send_auth_mail(auth_url):
    # Send an Authorization Email containing the Link returned by Keycloak to the User
    msg = MIMEText(auth_url)

    msg['Subject'] = 'New MQTT Authorization Request'
    msg['From'] = SMTP_SENDER_EMAIL
    msg['To'] = SMTP_RECEIVERS[0]

    # Create a secure SSL context
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(SMTP_PROXY, SMTP_PORT, context=context) as server:
        server.login(SMTP_SENDER_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_SENDER_EMAIL, SMTP_RECEIVERS, msg.as_string())

    print("Send new Auth URL: " + auth_url)


async def proxy_request_to_vernemq(data):
    # TODO make it Websocket
    return requests.post(VERNEMQ_URL)
