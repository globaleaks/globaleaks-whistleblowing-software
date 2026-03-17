# Refresh of the JWKS of the IdP configured on each tenant
from twisted.internet.defer import inlineCallbacks

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

        for issuer in issuers:
            try:
                yield self.state.oidcauth.fetch_jwks(issuer)
            except Exception:
                pass

        # Drop cached JWKS of issuers that are no longer configured
        for issuer in list(self.state.oidcauth.jwks.keys()):
            if issuer not in issuers:
                del self.state.oidcauth.jwks[issuer]
