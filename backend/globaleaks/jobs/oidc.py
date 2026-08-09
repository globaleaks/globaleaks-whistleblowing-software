# Refresh of the JWKS of the IdP configured on each tenant
from twisted.internet.defer import DeferredList, inlineCallbacks

from globaleaks.jobs.job import LoopingJob

__all__ = ['OIDC']


class OIDC(LoopingJob):
    interval = 60
    monitor_interval = 10

    @inlineCallbacks
    def operation(self):
        """
        This scheduler is responsible for:
            - Refreshing the JWKS of the IdP configured on each tenant
        """
        issuers = set()
        for tid in self.state.tenants:
            cache = self.state.tenants[tid].cache
            if cache.get('idp') and cache.get('idp_issuer'):
                issuers.add(cache.get('idp_issuer'))

            # The IdP used for authenticating the signups is inherited from
            # the profile configured for the tenants created via signup
            if cache.get('signup_idp') and cache.get('signup_idp_issuer'):
                issuers.add(cache.get('signup_idp_issuer'))

        # The issuers are refreshed concurrently, so that an unresponsive
        # identity provider does not delay the refresh of the other tenants
        yield DeferredList([self.state.oidcauth.fetch_jwks(issuer) for issuer in issuers],
                           consumeErrors=True)

        # Drop cached documents of issuers that are no longer configured
        for issuer in list(self.state.oidcauth.jwks.keys()):
            if issuer not in issuers:
                del self.state.oidcauth.jwks[issuer]

        for issuer in list(self.state.oidcauth.metadata.keys()):
            if issuer not in issuers:
                del self.state.oidcauth.metadata[issuer]
