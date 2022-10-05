from base64 import b64decode

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from pydantic import BaseModel
import requests
import jwt
from cryptography.hazmat.primitives import serialization
import smtplib, ssl
from email.mime.text import MIMEText

app = FastAPI()

# TODO set all of these as ENV-VARs
KEYCLOAK_URL = "https://auth.csp-staging.eng-softwarelabs.de"
RESOURCE_OWNER_MAIL = "jonas.leitner@eng-its.de"
CLIENT_ID = "mqtt-wrapper"
REALM = "default"
DEVICE_CODE_ENDPOINT = "/auth/realms/" + REALM + "/protocol/openid-connect/auth/device"
TOKEN_ENDPOINT = "/auth/realms/" + REALM + "/protocol/openid-connect/token"
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
    try:
        r = requests.get(KEYCLOAK_URL + PUB_KEY_ENDPOINT)
        r.raise_for_status()
        key_der_base64 = r.json()["public_key"]
        key_der = b64decode(key_der_base64.encode())
        keycloak_pub_key = serialization.load_der_public_key(key_der)
    except:
        print('Keycloak seems to be down, exiting...')
        exit(1)


# HTTP Endpoint for getting a Device Code from Keycloak
@app.get("/auth/device")
async def get_device_code():
    # Proxy Request to Keycloak
    keycloak_res = requests.post(KEYCLOAK_URL + DEVICE_CODE_ENDPOINT, {"client_id": CLIENT_ID}).json()
    # Mail Auth URL to the User
    send_auth_mail(keycloak_res['verification_uri_complete'])
    # Return Keycloak Response to Device
    return keycloak_res


# HTTP Endpoint for getting a Token from Keycloak using the Device Code (works only after Authorization from User)
class TokenReq(BaseModel):
    device_code: str


@app.post("/auth/token")
async def get_token(token_req: TokenReq, res: Response):
    print(token_req)
    payload = 'client_id=' + CLIENT_ID + '&grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code&device_code=' + token_req.device_code

    keycloak_res = requests.request(
        "POST",
        KEYCLOAK_URL + TOKEN_ENDPOINT,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        data=payload
    )
    print(keycloak_res.status_code)
    print(keycloak_res.json())

    res.status_code = keycloak_res.status_code

    return keycloak_res.json()


# WS Endpoint for MQTT Requests from the Device
# TODO check for JWT expiration once in a while
@app.websocket("/mqtt")
async def websocket_endpoint(
        websocket: WebSocket
):
    await websocket.accept()
    while True:
        try:
            # Check Header for JWT
            cookie = None
            try:
                cookie = websocket.headers["Cookie"]
            except KeyError:
                print("JWT missing")
                print("Send CONNACK with Result Code 4 - Authorization invalid")
                await websocket.send_bytes(create_connack_response(4))

            # Verify Authorization
            if not verify_jwt(cookie):
                # JWT invalid, send
                print("JWT invalid")
                print("Send CONNACK with Result Code 5 - Not Authorized")
                await websocket.send_bytes(create_connack_response(5))
                break

            # JWT valid, send CONNACK
            print("JWT valid")
            print("Send CONNACK with Result Code 0")
            await websocket.send_bytes(create_connack_response(0))

            # Authorization to MQTT-Wrapper was successful
            # Enter the Proxy-Loop
            while True:
                data = await websocket.receive_bytes()
                # Proxy MQTT Request to VerneMQ
                vernemq_res = await proxy_request_to_vernemq(data)

                # Return VerneMQ Response
                await websocket.send_bytes(vernemq_res)

        except WebSocketDisconnect:
            print("Client has disconnected.")
            break


def verify_jwt(token):
    # Check if JWT is valid by verifying its signature with Keycloaks PubKey
    global keycloak_pub_key
    try:
        payload = jwt.decode(token, keycloak_pub_key, algorithms=["RS256"])
    except:
        return False

    return True

def create_connack_response(rc):
    # create bytecodes for mqtt payloads here: https://npm.runkit.com/mqtt-packet
    if rc == 0:
        return b'\x20\x02\x00\x00'
    elif rc == 4:
        return b'\x20\x02\x00\x04'
    elif rc == 5:
        return b'\x20\x02\x00\x05'
    else:
        raise Exception("invalid return code")


def send_auth_mail(auth_url):
    # Send an Authorization Email containing the Link returned by Keycloak to the User
    print("Sending new Auth URL:\n" + auth_url)
    try:
        msg = MIMEText(auth_url)

        msg['Subject'] = 'New MQTT Authorization Request'
        msg['From'] = SMTP_SENDER_EMAIL
        msg['To'] = SMTP_RECEIVERS[0]

        # Create a secure SSL context
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(SMTP_PROXY, SMTP_PORT, context=context) as server:
            server.login(SMTP_SENDER_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_SENDER_EMAIL, SMTP_RECEIVERS, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        print("SMTP Auth failed")


async def proxy_request_to_vernemq(data):
    # TODO make it Websocket
    return requests.post(VERNEMQ_URL)
