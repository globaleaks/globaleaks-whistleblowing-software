# Microsoft Graph transport for outgoing mail (modern authentication)
import base64

from io import BytesIO
from urllib.parse import quote

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.client import FileBodyProducer, readBody
from twisted.web.http_headers import Headers

from globaleaks.utils.mail import MIME_mail_build


# Base URL of the Microsoft Graph API. Kept as a constant so that it can be
# adjusted for sovereign clouds if ever needed.
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"


class GraphError(Exception):
    pass


@inlineCallbacks
def send_mail(agent, access_token, from_name, from_address, to_address, subject, body):
    """
    Deliver an email through the Microsoft Graph sendMail endpoint.

    The message is built as a standard MIME document and submitted base64
    encoded, exactly as the SMTP transport would compose it, so that both
    transports produce identical mails.

    :param agent: A twisted web agent used to reach the Graph API
    :param access_token: An OAuth2 bearer token authorizing the request
    :param from_name: A from name
    :param from_address: A from address, also used as the sending mailbox
    :param to_address: The destination address
    :param subject: A mail subject
    :param body: A mail body
    :return: A deferred resolving to True once the message is accepted
    """
    message = MIME_mail_build(from_name, from_address, to_address, to_address, subject, body)

    payload = base64.b64encode(message.read())

    url = "%s/users/%s/sendMail" % (GRAPH_API_BASE, quote(from_address))

    headers = Headers({
        b'Authorization': [b'Bearer ' + access_token.encode()],
        b'Content-Type': [b'text/plain']
    })

    response = yield agent.request(b'POST',
                                   url.encode(),
                                   headers,
                                   FileBodyProducer(BytesIO(payload)))

    yield readBody(response)

    if response.code != 202:
        raise GraphError("Graph sendMail returned HTTP %d" % response.code)

    returnValue(True)
