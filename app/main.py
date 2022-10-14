from base64 import b64decode

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from pydantic import BaseModel
import requests
import jwt
from cryptography.hazmat.primitives import serialization
import smtplib, ssl
from email.mime.text import MIMEText
# import paho.mqtt.client as mqtt
from websocket import create_connection
import ssl

# Import local libs
import utils

app = FastAPI()

# TODO set all of these as ENV-VARs
KEYCLOAK_URL = "https://auth.csp-staging.eng-softwarelabs.de"
RESOURCE_OWNER_MAIL = "jonas.leitner@eng-its.de"
CLIENT_ID = "mqtt-wrapper"
REALM = "default"
DEVICE_CODE_ENDPOINT = "/auth/realms/" + REALM + "/protocol/openid-connect/auth/device"
TOKEN_ENDPOINT = "/auth/realms/" + REALM + "/protocol/openid-connect/token"
PUB_KEY_ENDPOINT = "/auth/realms/default"
VERNEMQ_URL = "ws://vernemq"
VERNEMQ_PORT = 8080

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
    payload = 'client_id=' + CLIENT_ID + '&grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code&device_code=' + token_req.device_code

    keycloak_res = requests.request(
        "POST",
        KEYCLOAK_URL + TOKEN_ENDPOINT,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded'
        },
        data=payload
    )

    res.status_code = keycloak_res.status_code

    return keycloak_res.json()


# TODO refresh tokens endpoint - longer refresh expiration time

# WS Endpoint for MQTT Requests from the Device
# TODO check for JWT expiration once in a while
@app.websocket("/mqtt")
async def websocket_endpoint(
        ws_client: WebSocket
):
    await ws_client.accept()
    while True:
        ws_vernemq = None
        try:
            # Check Header for JWT
            cookie = None
            print(ws_client.headers)
            cookie = ws_client.headers["Cookie"]
            print(cookie)
            if cookie is None:
                print("JWT missing")
                print("Send CONNACK with Result Code 4 - Authorization invalid")
                await ws_client.send_bytes(utils.CONNACK_INVALID_AUTH)
                break

            # Verify Authorization
            if not verify_jwt(cookie):
                # JWT invalid, send
                print("JWT invalid")
                print("Send CONNACK with Result Code 5 - Not Authorized")
                await ws_client.send_bytes(utils.CONNACK_UNAUTHORIZED)
                break

            # JWT valid, send CONNACK
            print("JWT valid")

            # Authorization to MQTT-Wrapper was successful
            initial_connection_data = await ws_client.receive_bytes()
            print("Receiving data from client...")
            print(initial_connection_data)

            # # Create a Connection to VerneMQ
            print("Creating WS Connection to VerneMQ...")
            ws_vernemq = create_connection(VERNEMQ_URL + ':' + str(VERNEMQ_PORT))

            print("Sending client-data to VerneMQ...")
            await ws_vernemq.send_bytes(initial_connection_data)
            print('Receiving answer from VerneMQ...')
            initial_connection_answer = await ws_vernemq.receive_bytes()
            print(initial_connection_answer)
            print('Sending answer to client...')
            await ws_client.send_bytes(initial_connection_answer)

            # def on_message(client, userdata, msg):
            #     # Proxy MQTT Request to VerneMQ
            #     await websocket.send_bytes()
            #
            # client = mqtt.Client(transport="websockets")
            # client.enable_logger()
            # # client.ws_set_options(path="/mqtt")
            # client.on_message = on_message
            # client.on_connect = print
            # client.on_connect_fail = print
            # client.on_log = print
            #
            # client.connect(VERNEMQ_URL, VERNEMQ_PORT, 60)

            # Enter the Proxy-Loop
            while True:
                data = await ws_client.receive_bytes()
                print(data)
                ws_vernemq.send_bytes(data)
                answer = await ws_vernemq.receive_bytes()
                print(answer)
                await ws_client.send_bytes(answer)


        except WebSocketDisconnect:
            print("Client has disconnected.")
            if ws_vernemq is not None:
                ws_vernemq.close()
            break


def verify_jwt(token):
    # Check if JWT is valid by verifying its signature with Keycloaks PubKey
    global keycloak_pub_key
    try:
        payload = jwt.decode(token, keycloak_pub_key, algorithms=["RS256"])
    except:
        print("invalid jwt")
        return False

    return True


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
