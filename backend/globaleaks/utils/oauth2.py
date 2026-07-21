# OAuth2 client-credentials token retrieval for SMTP modern authentication
import json
import time

from io import BytesIO
from urllib.parse import urlencode

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import FileBodyProducer, readBody
from twisted.web.http_headers import Headers


# Access tokens are cached in memory and reused until shortly before they
# expire. The cache is keyed by the parameters that identify the credential so
# that different tenants and SMTP profiles never share a token.
_token_cache = {}

# Renew a token slightly before its real expiration to avoid presenting an
# almost-expired token to the mail server.
EXPIRY_MARGIN = 60


class OAuth2Error(Exception):
    pass


@inlineCallbacks
def get_access_token(agent, token_endpoint, client_id, client_secret, scope):
    """
    Return an OAuth2 access token obtained via the client-credentials grant.

    The request is issued through the provided agent so that it inherits the
    anonymization policy configured for outgoing connections.

    :param agent: A twisted web agent used to reach the token endpoint
    :param token_endpoint: The OAuth2 token endpoint URL
    :param client_id: The application client id
    :param client_secret: The application client secret
    :param scope: The requested scope
    :return: A deferred resolving to the access token string
    """
    cache_key = (token_endpoint, client_id, scope)

    cached = _token_cache.get(cache_key)
    if cached is not None and cached['expires_at'] > time.monotonic():
        returnValue(cached['access_token'])

    body = urlencode({
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': scope
    }).encode()

    headers = Headers({b'Content-Type': [b'application/x-www-form-urlencoded']})

    response = yield agent.request(b'POST',
                                   token_endpoint.encode(),
                                   headers,
                                   FileBodyProducer(BytesIO(body)))

    content = yield readBody(response)

    if response.code != 200:
        raise OAuth2Error("Token endpoint returned HTTP %d" % response.code)

    data = json.loads(content)

    access_token = data.get('access_token')
    if not access_token:
        raise OAuth2Error("Token endpoint response did not contain an access token")

    _token_cache[cache_key] = {
        'access_token': access_token,
        'expires_at': time.monotonic() + data.get('expires_in', 3600) - EXPIRY_MARGIN
    }

    returnValue(access_token)


def invalidate_token(token_endpoint, client_id, scope):
    """
    Drop a cached token, forcing a fresh one to be fetched on the next send.

    This is used to recover from an authentication failure caused by a token
    that the mail server rejected before its expected expiration.
    """
    _token_cache.pop((token_endpoint, client_id, scope), None)
