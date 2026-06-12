# GlobaLeaks Utility used to handle Mail, format, exception, etc
from io import BytesIO

from email import utils  # pylint: disable=no-name-in-module
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from twisted.internet import reactor, defer
from twisted.internet._sslverify import ClientTLSOptions
from twisted.internet.endpoints import TCP4ClientEndpoint, UNIXClientEndpoint
from twisted.mail.smtp import messageid, ESMTPSenderFactory
from twisted.protocols import tls

from globaleaks.utils.socks import SOCKS5ClientEndpoint
from globaleaks.utils.tls import new_tls_client_context
from globaleaks.utils.log import log


def MIME_mail_build(src_name, src_mail, dest_name, dest_mail, mail_subject, mail_body):
    """
    Prepare the mail headers

    :param src_name: A source name
    :param src_mail: A source email adddress
    :param dest_name: A destination name
    :param dest_mail: A destination email address
    :param mail_subject: A mail subject
    :param mail_body: A mail body
    :return: A mail headers
    """
    multipart = MIMEMultipart('alternative')
    multipart['Message-Id'] = Header(messageid())
    multipart['Subject'] = Header(mail_subject.encode(), 'UTF-8').encode()
    multipart['Date'] = utils.formatdate()
    multipart['To'] = Header(dest_name.encode(), 'UTF-8').encode() + " <" + dest_mail + ">"
    multipart['From'] = Header(src_name.encode(), 'UTF-8').encode() + " <" + src_mail + ">"
    multipart['X-Mailer'] = "fnord"
    multipart.attach(MIMEText(mail_body.encode(), 'plain', 'UTF-8'))
    return BytesIO(multipart.as_bytes())  # pylint: disable=no-member


def sendmail(tid, smtp_host, smtp_port, security, authentication, username, password, from_name, from_address, to_address, subject, body, anonymize=True, socks_socket=None):
    """
    Send an email using SMTPS/SMTP+TLS and maybe torify the connection.

    :param tid: A tenant id
    :param smtp_host: A SMTP host
    :param smtp_port: A SMTP port
    :param security: A type of security to be applied (SMTPS/SMTP+TLS)
    :param authentication: A boolean to enable authentication
    :param username: A mail account username
    :param password: A mail account password
    :param from_name: A from name
    :param from_address: A from address
    :param to_address:  The to address
    :param subject: A mail subject
    :param body: A mail body
    :param anonymize: A boolean to enable anonymous mail connection
    :param socks_socket: The path of the tor SOCKS unix-domain socket
    :return: A deferred resource resolving at the end of the connection
    """
    try:
        timeout = 30
        message = MIME_mail_build(from_name,
                                  from_address,
                                  to_address,
                                  to_address,
                                  subject,
                                  body)

        log.debug('Sending email to %s using SMTP server [%s:%d] [%s]',
                  to_address, smtp_host, smtp_port, security, tid=tid)

        context_factory = ClientTLSOptions(smtp_host, new_tls_client_context())
        smtp_deferred = defer.Deferred()

        factory = ESMTPSenderFactory(
            username.encode() if authentication else None,
            password.encode() if authentication else None,
            from_address,
            to_address,
            message,
            smtp_deferred,
            contextFactory=context_factory,
            requireAuthentication=authentication,
            requireTransportSecurity=(security == 'TLS'),
            retries=0,
            timeout=timeout)

        if security == "SSL":
            factory = tls.TLSMemoryBIOFactory(context_factory, True, factory)

        if anonymize:
            socksProxy = UNIXClientEndpoint(reactor, socks_socket, timeout=timeout)
            endpoint = SOCKS5ClientEndpoint(smtp_host.encode('utf-8'), smtp_port, socksProxy)
        else:
            endpoint = TCP4ClientEndpoint(reactor, smtp_host, smtp_port, timeout=timeout)

        conn_deferred = endpoint.connect(factory)

        # Ensure smtp_deferred always fires if connection fails
        conn_deferred.addErrback(lambda f: smtp_deferred.errback(f) if not smtp_deferred.called else None)

        final = defer.DeferredList([conn_deferred, smtp_deferred], fireOnOneErrback=True, consumeErrors=True)

        # --- Timeout safeguard ---
        def timeout_cb():
            if not smtp_deferred.called:
                log.err("SMTP deferred timeout reached, forcing errback for %s", to_address, tid=tid)
                smtp_deferred.errback(Exception("SMTP deferred timeout"))
        reactor.callLater(timeout + 30, timeout_cb)  # 30s extra buffer

        def failure_cb(failure):
            """
            :param failure {Failure {twisted.internet.FirstError {Failure}}}
            """
            log.err("SMTP connection failed (Exception: %s)",
                    failure.value.subFailure.value, tid=tid)
            return False

        def success_cb(results):
            """
            :param results {list of (success, return_val) tuples}
            """
            return True

        return final.addCallbacks(success_cb, failure_cb)

    except Exception as e:
        # avoids raising an exception inside email logic to avoid chained errors
        log.err("Unexpected exception in sendmail: %s", e, tid=tid)
        return defer.succeed(False)
