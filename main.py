import json
from typing import Optional
from authlib.integrations.requests_client import OAuth2Session
from fastapi import Depends, FastAPI, Request, HTTPException
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer, OAuth2AuthorizationCodeBearer

app = FastAPI()

tokenUrl = "https://auth.dlr.wobcom.tech/auth/realms/default/protocol/openid-connect/token"

authUrl = "https://auth.dlr.wobcom.tech/auth/realms/default/protocol/openid-connect/auth"

#oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
#oauth2_scheme = OAuth2PasswordBearer(tokenUrl=tokenUrl, authorizationUrl=authUrl)
oauth2_scheme = OAuth2AuthorizationCodeBearer(tokenUrl=tokenUrl, authorizationUrl=authUrl)


client_id='servicemqttmec'
secret='0e641fb3-c923-405f-83fa-f6a561041ead'

class Item(BaseModel):
    name: str
    price: float
    is_offer: Optional[bool] = None

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}

@app.get("/hello/")
async def read_hello(token: str = Depends(oauth2_scheme)):
    oauth = OAuth2Session(client_id=client_id, client_secret=secret)
    result = oauth.introspect_token(
        url="https://auth.dlr.wobcom.tech/auth/realms/default/protocol/openid-connect/introspect", token=token)
    content = json.loads(result.content.decode())
    if not content['active']:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    else:
        return content

    return {"token": token}

@app.get("/callbackUrl/")
async def callbackUrl():
    print('this is the callback url')

