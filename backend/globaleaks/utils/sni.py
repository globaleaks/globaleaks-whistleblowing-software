
# This TLS SNI implementation is an extract of https://github.com/glyph/txsni
# For original authors and related LICENSE refer to the original repository
#
# The code is directly included into GlobaLeaks as the original library
# is currently not released as Debian package.

import collections

from OpenSSL.SSL import Connection
from twisted.internet.interfaces import IOpenSSLServerConnectionCreator
from zope.interface import implementer

from globaleaks.utils.tls import ChainValidator, TLSServerContextFactory, new_tls_server_context


class _NegotiationData:
    """
    A container for the negotiation data.
    """
    __slots__ = [
        'alpn_select_callback',
        'alpn_protocols'
    ]

    def __init__(self):
        self.alpn_select_callback = None
        self.alpn_protocols = None

    def negotiate_alpn(self, context):
        if self.alpn_select_callback and self.alpn_protocols:
            context.set_alpn_select_callback(self.alpn_select_callback)
            context.set_alpn_protos(self.alpn_protocols)


class _ContextProxy:
    """
    A basic proxy object for the OpenSSL Context object that records the
    values of the ALPN callback, to ensure that they get set appropriately
    if a context is swapped out during connection setup.
    """

    def __init__(self, original, factory):
        self._obj = original
        self._factory = factory

    def set_alpn_select_callback(self, cb):
        self._factory._alpn_select_callback_for_context(self._obj, cb)
        return self._obj.set_alpn_select_callback(cb)

    def set_alpn_protos(self, protocols):
        self._factory._alpn_protocols_for_context(self._obj, protocols)
        return self._obj.set_alpn_protos(protocols)

    def __getattr__(self, attr):
        return getattr(self._obj, attr)

    def __setattr__(self, attr, val):
        if attr in ('_obj', '_factory'):
            self.__dict__[attr] = val
        else:
            setattr(self._obj, attr, val)

    def __delattr__(self, attr):
        if attr in ('_obj', '_factory'):
            del self.__dict__[attr]
        else:
            delattr(self._obj, attr)

class _ConnectionProxy:
    """
    A basic proxy for an OpenSSL Connection object that returns a ContextProxy
    wrapping the actual OpenSSL Context whenever it's asked for.
    """

    def __init__(self, original, factory):
        self._obj = original
        self._factory = factory

    def get_context(self):
        """
        A basic override of get_context to ensure that the appropriate proxy
        object is returned.
        """
        return _ContextProxy(self._obj.get_context(), self._factory)

    def __getattr__(self, attr):
        return getattr(self._obj, attr)

    def __setattr__(self, attr, val):
        if attr in ('_obj', '_factory'):
            self.__dict__[attr] = val

        return setattr(self._obj, attr, val)

    def __delattr__(self, attr):
        delattr(self._obj, attr)


@implementer(IOpenSSLServerConnectionCreator)
class SNIMap:
    def __init__(self):
        self.default_context = None
        self.configs_by_tid = {}
        self.contexts_by_hostname = {}
        self._negotiation_data_for_context = collections.defaultdict(_NegotiationData)
        self.set_default_context(new_tls_server_context())

    def set_default_context(self, context):
        self.default_context = context
        self.default_context.set_tlsext_servername_callback(self.select_context)

    def load(self, tid, conf):
        chnv = ChainValidator()
        ok, err = chnv.validate(conf, check_expiration=False)
        if not ok or err is not None:
            return

        self.configs_by_tid[tid] = conf

        context = TLSServerContextFactory(conf['ssl_key'],
                                          conf['ssl_cert'],
                                          conf['ssl_intermediate'])

        self.contexts_by_hostname[conf['hostname']] = context

        if tid == 1:
            self.set_default_context(context.getContext())

    def unload(self, tid):
        conf = self.configs_by_tid.pop(tid, None)
        if conf:
            context = self.contexts_by_hostname.pop(conf['hostname'], None)
            if context:
                self._negotiation_data_for_context.pop(context.getContext(), None)

        if tid == 1:
            self.set_default_context(new_tls_server_context())

    def select_context(self, connection):
        try:
            common_name = connection.get_servername().decode().lower()
        except (AttributeError, UnicodeDecodeError):
            # AttributeError: get_servername() returned None (no SNI).
            # UnicodeDecodeError: server_name not valid UTF-8.
            common_name = '127.0.0.1'

        context_factory = self.contexts_by_hostname.get(common_name)
        context = context_factory.getContext() if context_factory else self.default_context

        negotiation_data = self._negotiation_data_for_context.get(connection.get_context())
        if negotiation_data:
            negotiation_data.negotiate_alpn(context)
        connection.set_context(context)

    def serverConnectionForTLS(self, protocol):
        return _ConnectionProxy(Connection(self.default_context, None), self)

    def _alpn_select_callback_for_context(self, context, callback):
        self._negotiation_data_for_context[context].alpn_select_callback = callback

    def _alpn_protocols_for_context(self, context, protocols):
        self._negotiation_data_for_context[context].alpn_protocols = protocols
