from unicodedata import name
from fastapi import FastAPI, requests
from fastapi.encoders import jsonable_encoder
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse, RedirectResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
import logging
import sys 
import json

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="0e641fb3-c923-405f-83fa-f6a561041ead")
oauth = OAuth()

log = logging.getLogger('authlib')
log.addHandler(logging.StreamHandler(sys.stdout))
log.setLevel(logging.DEBUG)

accessToken =''

oauth.register(
    name="wobcom",
    authorization_endpoint="https://auth.dlr.wobcom.tech/auth/realms/default/protocol/openid-connect/auth",
    token_endpoint="https://auth.dlr.wobcom.tech/auth/realms/default/protocol/openid-connect/token",
    client_id="test-client",
    client_secret="a41f10fb-8930-434e-999c-299a9cdeed5c"
    )

@app.get('/')
async def homepage(request: Request):
    user = request.session.get('user')
    log.debug('user in homepage: %s' % type(user))

    if user:
        data = user
        data = jsonable_encoder(data)
        #html = (
        #    '<pre>{data}</pre>'
        #    '<a href="/logout">logout</a>'
        #)
        html=data
        return HTMLResponse(html)
    return HTMLResponse('<a href="/login">login</a>')


@app.get('/login')
async def login(request: Request):
    # absolute url for callback
    # we will define it below
    redirect_uri = request.url_for('auth')
    
    log.debug('request baseurl: %s' % request.base_url)
    log.debug('redirect_uri: %s' % redirect_uri)
    return await oauth.wobcom.authorize_redirect(request,redirect_uri)


@app.get('/auth')
async def auth(request: Request):
    log.debug(str(request))
    token = await oauth.wobcom.authorize_access_token(request)
    print(token)
    accessToken = token
    # has to be adapted to keycloak, for example to verify the user, get info etc.
    userInfoUrl = "https://auth.dlr.wobcom.tech/auth/realms/default/protocol/openid-connect/userinfo"
    #url = 'account/verify_credentials.json'
    resp = await oauth.wobcom.get(
        userInfoUrl, params={'skip_status': True}, token=token)
    user = resp.json()

    log.debug("user: %s" %user)
    request.session['user'] = dict(user)
    return RedirectResponse(url='/')

@app.get('/logout')
async def logout(request: Request):
    log.debug('logout function')
    logoutUrl = "https://auth.dlr.wobcom.tech/auth/realms/default/protocol/openid-connect/logout"

    resp = await oauth.wobcom.get(
        logoutUrl, params={'skip_status': True}, token=accessToken)
    log.debug('response: %s' % resp)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

