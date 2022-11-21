import http
import http
import time
from base64 import b64decode

import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response
from pydantic import BaseModel
import uvicorn
import requests
import jwt
from cryptography.hazmat.primitives import serialization
import smtplib, ssl
from email.mime.text import MIMEText
import websockets
import ssl
import logging

# Import local libs
import utils

file_handler = logging.FileHandler(filename='mqtt-wrapper.log')
stdout_handler = logging.StreamHandler(stream=sys.stdout)
handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger('MQTT_WRAPPER')

app = FastAPI(
    docs_url=None,
    redoc_url=None
)

# TODO use gunicorn and tune it for prod release

# ENV-Vars
PORT = utils.env_var('PORT', default=8000)
HOT_RELOAD = utils.env_var('HOT_RELOAD', default=False)
KEYCLOAK_URL = utils.env_var('KEYCLOAK_URL', 'https://auth.csp-staging.eng-softwarelabs.de')
CLIENT_ID = utils.env_var('CLIENT_ID', "mqtt-wrapper")
REALM = utils.env_var('REALM', "default")
VERNEMQ_URL = utils.env_var('VERNEMQ_URL', "ws://vernemq")
VERNEMQ_PORT = utils.env_var('VERNEMQ_PORT', 8080)

# SMTP Email Credentials
SMTP_SENDER_EMAIL = utils.env_var('SMTP_SENDER_EMAIL', "noreply@dlr.de")
SMTP_PASSWORD = utils.env_var('SMTP_PASSWORD', "1234")
SMTP_PROXY = utils.env_var('SMTP_PROXY', "smtp.gmail.com")
SMTP_PORT = utils.env_var('SMTP_PORT', 465)
RESOURCE_OWNER_MAIL = utils.env_var('RESOURCE_OWNER_MAIL', "jonas.leitner@eng-its.de")

# Hardcoded Keycloak Endpoints
DEVICE_CODE_ENDPOINT = "/auth/realms/" + REALM + "/protocol/openid-connect/auth/device"
TOKEN_ENDPOINT = "/auth/realms/" + REALM + "/protocol/openid-connect/token"
PUB_KEY_ENDPOINT = "/auth/realms/default"

# Global Variables
keycloak_pub_key = None

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        loop='asyncio',
        reload=HOT_RELOAD,
        port=int(PORT),
        ws_ping_timeout=None,
        ws_ping_interval=None,
        ws="websockets",
        app_dir="/app/src"
    )


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
    except requests.exceptions.RequestException:
        logger.critical('Keycloak cannot be reached, exiting...')
        exit(1)


# HTTP Endpoint for getting a Device Code from Keycloak
# TODO obfusctate URL / add token
@app.get("/auth/device")
async def get_device_code(res: Response):
    global RESOURCE_OWNER_MAIL, SMTP_PASSWORD, SMTP_PORT, SMTP_PROXY, SMTP_SENDER_EMAIL

    logger.debug('Getting Device Code from Keycloak')
    # Proxy Request to Keycloak
    try:
        keycloak_res = requests.post(KEYCLOAK_URL + DEVICE_CODE_ENDPOINT, {"client_id": CLIENT_ID})
    except requests.exceptions.ConnectionError as e:
        logger.warning('Connection Error to Keycloak occured')
        res.status_code = 400
        res = {'error': 'HTTP Error while communicating with Keycloak'}
        return res

    res.status_code = keycloak_res.status_code

    if keycloak_res.status_code != 200:
        logger.info('Token Request failed')
        logger.debug(keycloak_res.json())
        return keycloak_res.json()

    # Mail Auth URL to the User
    try:
        send_auth_mail(
            auth_url=keycloak_res.json()['verification_uri_complete'],
            sender_email=SMTP_SENDER_EMAIL,
            receiver_email=RESOURCE_OWNER_MAIL,
            smtp_proxy=SMTP_PROXY,
            smtp_port=SMTP_PORT,
            smtp_password=SMTP_PASSWORD
        )
    except smtplib.SMTPAuthenticationError as err:
        logger.error("SMTP Auth failed")
        logger.error(err)

    # Return Keycloak Response to Device
    return keycloak_res.json()


# HTTP Endpoint for getting a Token from Keycloak using the Device Code (works only after Authorization from User)
class CreateTokenReq(BaseModel):
    device_code: str


# TODO: test if simultaneous devices polling the endpoint trigger the ratelimit
@app.post("/auth/token")
async def get_token(create_token_req: CreateTokenReq, res: Response):
    logger.debug("Getting JWT from Keycloak")
    payload = 'client_id=' + CLIENT_ID + '&grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Adevice_code&device_code=' + create_token_req.device_code

    try:
        keycloak_res = requests.request(
            "POST",
            KEYCLOAK_URL + TOKEN_ENDPOINT,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data=payload
        )
    except requests.exceptions.ConnectionError as e:
        logger.warning('Connection Error to Keycloak occured')
        res.status_code = 400
        res = {'error': 'HTTP Error while communicating with Keycloak'}
        return res

    if keycloak_res.status_code != 200:
        logger.info('Token Request failed')
        logger.debug(keycloak_res.json())

    res.status_code = keycloak_res.status_code

    return keycloak_res.json()


# HTTP Endpoint for getting fresh Tokens from Keycloak using refresh Tokens
class RefreshTokenReq(BaseModel):
    refresh_token: str


@app.post("/auth/refresh")
async def refresh_token(refresh_token_req: RefreshTokenReq, res: Response):
    logger.debug('Refreshing JWT Token')

    payload = 'refresh_token=' + refresh_token_req.refresh_token + '&grant_type=refresh_token&client_id=' + CLIENT_ID

    try:
        keycloak_res = requests.request(
            "POST",
            KEYCLOAK_URL + TOKEN_ENDPOINT,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            data=payload
        )
    except requests.exceptions.ConnectionError as e:
        logger.warning('Connection Error to Keycloak occured')
        res.status_code = 400
        res = {'error': 'HTTP Error while communicating with Keycloak'}
        return res

    if keycloak_res.status_code != 200:
        logger.info('Token Refresh failed')
        logger.debug(keycloak_res.json())

    res.status_code = keycloak_res.status_code

    return keycloak_res.json()


# WS Endpoint for MQTT Requests from the Device
@app.websocket("/mqtt")
async def websocket_endpoint(
        ws_client: WebSocket
):
    global keycloak_pub_key
    await ws_client.accept()
    while True:
        ws_vernemq = None
        try:
            # Check Header for JWT
            try:
                cookie = ws_client.headers["Cookie"]
            except KeyError:
                logger.warning("JWT missing")
                logger.debug("Send CONNACK with Result Code 4 - Authorization invalid")
                await ws_client.send_bytes(utils.CONNACK_INVALID_AUTH)
                await ws_client.close()
                break

            # Verify Authorization
            try:
                utils.verify_jwt(cookie, keycloak_pub_key)
            except jwt.exceptions.PyJWTError as err:
                # JWT invalid
                logger.warning("JWT invalid")
                logger.debug(err)
                logger.debug("Send CONNACK with Result Code 5 - Not Authorized")
                await ws_client.send_bytes(utils.CONNACK_UNAUTHORIZED)
                await ws_client.close()
                break

            # JWT valid, send CONNACK
            logger.info("JWT valid")

            # Authorization to MQTT-Wrapper was successful
            logger.debug("Receiving data from client...")
            initial_connection_data = await ws_client.receive_bytes()

            # # Create a Connection to VerneMQ
            logger.debug("Creating WS Connection to VerneMQ...")

            ws_vernemq = await websockets.connect(
                VERNEMQ_URL + ':' + str(VERNEMQ_PORT) + '/mqtt',
                subprotocols=['mqtt']
            )

            logger.debug("Sending client-data to VerneMQ...")
            logger.debug(initial_connection_data)
            await ws_vernemq.send(initial_connection_data)
            logger.debug('Receiving answer from VerneMQ...')
            initial_connection_answer = await ws_vernemq.recv()
            logger.debug(initial_connection_answer)
            logger.debug('Sending answer to client...')
            await ws_client.send_bytes(initial_connection_answer)

            # Enter the Proxy-Loop
            # TODO document WS-Tunneling
            logger.debug("Proxy Connection started, entering proxy loop...")
            while True:
                # Check if token has expired (or is otherwise invalid) every few requests
                try:
                    utils.verify_jwt(cookie, keycloak_pub_key)
                except jwt.exceptions.PyJWTError as err:
                    # JWT invalid, send
                    logger.warning("JWT expired")
                    logger.debug(err)
                    logger.debug("Send DISCONNECT")
                    await ws_client.send_bytes(utils.DISCONNECT)
                    await ws_client.close()
                    await ws_vernemq.close()
                    break

                logger.debug("Receiving data from client...")
                data = await ws_client.receive_bytes()
                logger.debug(data)
                logger.debug("Sending client data to VerneMQ...")
                await ws_vernemq.send(data)
                logger.debug('Receiving answer from VerneMQ...')
                answer = await ws_vernemq.recv()
                logger.debug(answer)
                logger.debug("Sending VerneMQ answer to Client...")
                await ws_client.send_bytes(answer)

        except WebSocketDisconnect:
            logger.warning("Client has disconnected from WebSocket.")
            if ws_vernemq is not None:
                await ws_vernemq.close()
            break

        except websockets.ConnectionClosedError:
            logger.error("Connection closed by VerneMQ")
            await ws_client.close()
            break


# Tarpit for all probing requests
@app.api_route('/{full_path:path}', status_code=http.HTTPStatus.IM_A_TEAPOT)
def tarpit():
    time.sleep(30)


def send_auth_mail(auth_url, sender_email, receiver_email, smtp_proxy, smtp_port, smtp_password):
    # Send an Authorization Email containing the Link returned by Keycloak to the User
    logger.info("Sending new Auth URL:\n" + auth_url)
    msg = MIMEText(auth_url)

    msg['Subject'] = 'New MQTT Authorization Request'
    msg['From'] = sender_email
    msg['To'] = receiver_email

    # Create a secure SSL context
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(smtp_proxy, smtp_port, context=context) as server:
        server.login(sender_email, smtp_password)
        server.sendmail(sender_email, [receiver_email], msg.as_string())