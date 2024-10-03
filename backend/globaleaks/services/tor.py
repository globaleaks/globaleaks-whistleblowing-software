# -*- coding: utf-8 -*-
# Implements configuration of Tor onion services
import os
import txtorcon

from txtorcon import build_local_tor_connection
from twisted.internet import reactor
from twisted.internet.defer import Deferred, returnValue
from txtorcon import TorConfig

from globaleaks.services.service import Service
from globaleaks.state import State
from globaleaks.utils.log import log
from globaleaks.utils.utility import deferred_sleep


__all__ = ['Tor']


class Tor(Service):
    print_startup_error = True
    tor_conn = None

    def __init__(self):
        self.tor = txtorcon.launch(
            reactor,
            socks_port=State.settings.socks_port,
            control_port='unix:' + State.settings.tor_control,
        )

        Service.__init__(self)

    def reset(self):
        self.tor_conn = None

    def stop(self):
        super(Tor, self).stop()

        if self.tor_conn is None:
            return

        tor_conn = self.tor_conn
        self.tor_conn = None
        return tor_conn.protocol.quit()

    def load_onion_service(self, tid, hostname, key):
        if self.tor_conn is None:
            return

        onion_service = None

        hs_loc = '80 localhost:8083'

        log.err('Setting up the onion service %s', hostname, tid=tid)

        config = TorConfig(self.tor_conn.protocol)

        def init_callback(ret):
            nonlocal onion_service

            if ret:
                onion_service = ret

            if tid in State.tenants:
                State.tenants[tid].ephs = onion_service

            log.err('Initialization of onion-service %s completed.', onion_service.hostname, tid=tid)

        try:
            from txtorcon.onion import EphemeralOnionService
            onion_service = EphemeralOnionService.create(reactor, config, [hs_loc], private_key=key)
            return onion_service.addCallbacks(init_callback)  # pylint: disable=no-member
        except:
            from txtorcon.torconfig import EphemeralHiddenService
            onion_service = EphemeralHiddenService(hs_loc, key)
            return onion_service.add_to_tor(self.tor_conn.protocol).addCallbacks(init_callback)  # pylint: disable=no-member

    def load_all_onion_services(self):
        if self.tor_conn is None:
            return

        for tid in self.state.tenants:
            if self.state.tenants[tid].cache.tor_onion_key and not hasattr(self.state.tenants[tid], 'ephs'):
                # Track that the onion service is starting
                self.state.tenants[tid].ephs = False
                self.load_onion_service(tid, self.state.tenants[tid].cache.onionservice, self.state.tenants[tid].cache.tor_onion_key)

    def unload_onion_service(self, tid):
        if self.tor_conn is None:
            return

        if hasattr(self.state.tenants[tid], 'ephs') and self.state.tenants[tid].ephs:
           try:
               self.state.tenants[tid].ephs.remove()
           except AttributeError:
               yield self.state.tenants[tid].ephs.remove_from_tor(self.tor_conn.protocol)

    def operation(self):
        restart_deferred = Deferred()

        def startup_callback(tor_conn):
            self.print_startup_error = True
            self.tor_conn = tor_conn
            self.tor_conn.protocol.on_disconnect = restart_deferred

            log.err('Successfully connected to Tor control port')

            self.load_all_onion_services()

        def startup_errback(err):
            if self.print_startup_error:
                # Print error only on first run or failure or on a failure subsequent to a success condition
                self.print_startup_error = False
                log.err('Failed to initialize Tor connection; error: %s', err)

            restart_deferred.callback(None)

        if not os.path.exists(self.state.settings.tor_control):
            startup_errback(Exception('Tor control port not open on %s; waiting for Tor to become available' % self.state.settings.tor_control))
            return deferred_sleep(1)

        if not os.access(self.state.settings.tor_control, os.R_OK):
            startup_errback(Exception('Unable to access %s; manual permission recheck needed' % self.state.settings.tor_control))
            return deferred_sleep(1)

        def connect(_):
            build_local_tor_connection(reactor, socket=self.state.settings.tor_control).addCallbacks(startup_callback, startup_errback)

        self.tor.addCallback(connect)

        return restart_deferred
