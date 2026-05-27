from OpenSSL import crypto
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import db_log, transact, tw
from globaleaks.rest import errors, requests
from globaleaks.settings import Settings
from globaleaks.state import State
from globaleaks.utils import letsencrypt, tls


def db_load_tls_config(session, tid, test=False):
    """
    Transaction for loading the TLS configuration of a tenant

    :param session: An ORM session
    :param tid: A tenant ID
    :param test: A boolean to indicate if we are performing a test on the actual config
    :return: The serialized TLS configuration for the specified tenant
    """
    node = ConfigFactory(session, tid)

    if test or node.get_val('https_enabled'):
        key = node.get_val('https_key')
        cert = node.get_val('https_cert')
        chain = node.get_val('https_chain')
        hostname = node.get_val('hostname')
    else:
        key = node.get_val('https_selfsigned_key')
        cert = node.get_val('https_selfsigned_cert')
        chain = ''
        hostname = '127.0.0.1'

    return {
        'tid': tid,
        'ssl_key': key,
        'ssl_cert': cert,
        'ssl_intermediate': chain,
        'https_enabled': node.get_val('https_enabled'),
        'hostname': hostname
    }


def db_load_tls_configs(session):
    return [db_load_tls_config(session, tid[0]) for tid in session.query(models.Tenant.id).filter(models.Tenant.active.is_(True))]


def db_generate_acme_key(session, tid):
    priv_fact = ConfigFactory(session, tid)

    key = tls.gen_rsa_key(Settings.rsa_key_bits)
    priv_fact.set_val('acme_accnt_key', key)

    return key


def db_acme_cert_request(session, tid):
    priv_fact = ConfigFactory(session, tid)
    hostname = priv_fact.get_val('hostname')

    acme_accnt_key = ConfigFactory(session, 1).get_val('acme_accnt_key').encode()

    if not acme_accnt_key:
        acme_accnt_key = db_generate_acme_key(session, tid)

    acme_accnt_key = serialization.load_pem_private_key(acme_accnt_key,
                                                        password=None,
                                                        backend=default_backend())

    https_key = priv_fact.get_val('https_key')

    https_cert, https_chain = letsencrypt.request_new_certificate(hostname,
                                                                  acme_accnt_key,
                                                                  https_key,
                                                                  State.tenants[tid].acme_tmp_chall_dict,
                                                                  Settings.acme_directory_url)

    priv_fact.set_val('acme', True)
    priv_fact.set_val('https_cert', https_cert)
    priv_fact.set_val('https_chain', https_chain)
    State.tenants[tid].cache.https_cert = https_cert
    State.tenants[tid].cache.https_chain = https_chain


def db_load_https_key(session, tid, data=None):
    if not data:
      data = tls.gen_ecc_key()

    db_cfg = db_load_tls_config(session, tid, True)
    db_cfg['ssl_key'] = data

    config = ConfigFactory(session, tid)
    pkv = tls.KeyValidator()
    ok, _ = pkv.validate(db_cfg)
    if ok:
        config.set_val('https_key', data)

    return ok


def db_load_https_cert(session, tid, data):
    db_cfg = db_load_tls_config(session, tid, True)
    db_cfg['ssl_cert'] = data

    config = ConfigFactory(session, tid)
    pkv = tls.CertValidator()
    ok, _ = pkv.validate(db_cfg)
    if ok:
        config.set_val('https_cert', data)
        State.tenants[tid].cache.https_cert = data

    return ok


def db_load_https_chain(session, tid, data):
    db_cfg = db_load_tls_config(session, tid, True)
    db_cfg['ssl_intermediate'] = data

    config = ConfigFactory(session, tid)
    pkv = tls.ChainValidator()
    ok, _ = pkv.validate(db_cfg)
    if ok:
        config.set_val('https_chain', data)
        State.tenants[tid].cache.https_intermediate = data

    return ok


def db_serialize_https_config_summary(session, tid):
    config = ConfigFactory(session, tid)

    file_summaries = {}
    for key, file_res_cls in FileHandler.mapped_resources.items():
        file_summaries[key] = file_res_cls.db_serialize(session, tid)

    return {
        'enabled': config.get_val('https_enabled'),
        'files': file_summaries,
        'acme': config.get_val('acme')
    }


def db_try_to_enable_https(session, tid, user_id):
    config = ConfigFactory(session, tid)

    cv = tls.ChainValidator()
    tls_config = db_load_tls_config(session, tid, True)
    tls_config['https_enabled'] = False

    ok, _ = cv.validate(tls_config)
    if not ok:
        raise errors.InputValidationError

    config.set_val('https_enabled', True)
    State.tenants[tid].cache.https_enabled = True
    State.snimap.load(tid, tls_config)

    db_log(session, tid=tid, type='enable_https', user_id=user_id)


def db_disable_https(session, tid, user_id):
    config = ConfigFactory(session, tid)
    config.set_val('https_enabled', False)
    State.snimap.unload(tid)
    State.tenants[tid].cache.https_enabled = False

    db_log(session, tid=tid, type='disable_https', user_id=user_id)


def db_reset_https_config(session, tid, user_id):
    config = ConfigFactory(session, tid)
    config.set_val('https_enabled', False)
    config.set_val('https_key', '')
    config.set_val('https_cert', '')
    config.set_val('https_chain', '')
    config.set_val('acme', False)
    config.set_val('acme_accnt_key', '')

    State.tenants[tid].cache.https_enabled = False

    State.snimap.unload(tid)

    State.snimap.load(tid, db_load_tls_config(session, tid))

    db_log(session, tid=tid, type='reset_https_config', user_id=user_id)


class FileResource(object):
    """
    An interface for interacting with files stored on disk or in the db
    """
    @classmethod
    def perform_action(cls, tid):
        raise errors.MethodNotImplemented

    @staticmethod
    @transact
    def get_file(session, tid):
        raise errors.MethodNotImplemented

    @staticmethod
    @transact
    def delete_file(session, tid):
        raise errors.MethodNotImplemented

    @staticmethod
    def db_serialize(session, tid):
        raise errors.MethodNotImplemented

    @classmethod
    @transact
    def serialize(cls, session, tid):
        return cls.db_serialize(session)


class KeyFileRes(FileResource):
    @classmethod
    @inlineCallbacks
    def perform_action(cls, tid):
        yield tw(db_load_https_key, tid)

    @staticmethod
    @transact
    def delete_file(session, tid):
        config = ConfigFactory(session, tid)
        config.set_val('https_key', '')

    @staticmethod
    def db_serialize(session, tid):
        config = ConfigFactory(session, tid)

        return {
            'set': config.get_val('https_key') != ''
        }


class CertFileRes(FileResource):
    @staticmethod
    @transact
    def delete_file(session, tid):
        ConfigFactory(session, tid).set_val('https_cert', '')
        State.tenants[tid].cache.https_cert = ''

    @staticmethod
    def db_serialize(session, tid):
        c = ConfigFactory(session, tid).get_val('https_cert')
        if not c:
            return {
                'name': 'cert',
                'set': False
            }

        c = """{}""".format(c)
        x509 = crypto.load_certificate(crypto.FILETYPE_PEM, c)
        expr_date = letsencrypt.convert_asn1_date(x509.get_notAfter())

        return {
            'name': 'cert',
            'issuer': tls.parse_issuer_name(x509),
            'expiration_date': expr_date,
            'set': True,
        }


class ChainFileRes(FileResource):
    @staticmethod
    @transact
    def delete_file(session, tid):
        ConfigFactory(session, tid).set_val('https_chain', '')

    @staticmethod
    def db_serialize(session, tid):
        c = ConfigFactory(session, tid).get_val('https_chain')
        if not c:
            return {
                'name': 'chain',
                'set': False
            }

        c = tls.split_pem_chain(c)[0]
        x509 = crypto.load_certificate(crypto.FILETYPE_PEM, c)
        expr_date = letsencrypt.convert_asn1_date(x509.get_notAfter())

        return {
            'name': 'chain',
            'issuer': tls.parse_issuer_name(x509),
            'expiration_date': expr_date,
            'set': True
        }


class FileHandler(BaseHandler):
    check_roles = 'admin'
    root_tenant_or_management_only = True

    mapped_resources = {
        'key': KeyFileRes,
        'cert': CertFileRes,
        'chain': ChainFileRes
    }

    def get_res_or_raise(self, name):
        if name not in self.mapped_resources:
            raise errors.MethodNotImplemented

        return self.mapped_resources[name]

    @inlineCallbacks
    def delete(self, name):
        yield self.get_res_or_raise(name).delete_file(self.request.tid)
        yield tw(db_log, tid=self.request.tid, type='delete_tls_cert', user_id=self.session.user_id, data={'name': name})

    @inlineCallbacks
    def post(self, name):
        req = self.validate_request(self.request.content.read(),
                                    requests.AdminTLSCfgFileResourceDesc)

        if name == 'key':
            ok = yield tw(db_load_https_key, self.request.tid, req['content'])
        elif name == 'cert':
            ok = yield tw(db_load_https_cert, self.request.tid, req['content'])
        elif name == 'chain':
            ok = yield tw(db_load_https_chain, self.request.tid, req['content'])
        else:
            ok = False

        if not ok:
            raise errors.InputValidationError

        yield tw(db_log, tid=self.request.tid, type='upload_tls_cert', user_id=self.session.user_id, data={'name': name})

    @inlineCallbacks
    def put(self, name):
        file_res_cls = self.get_res_or_raise(name)

        yield file_res_cls.perform_action(self.request.tid)

        yield tw(db_log, tid=self.request.tid, type='upload_tls_cert', user_id=self.session.user_id, data={'name': name})

    def get(self, name):
        return self.get_res_or_raise(name).get_file(self.request.tid)


class ConfigHandler(BaseHandler):
    check_roles = 'admin'
    root_tenant_or_management_only = True

    def get(self):
        return tw(db_serialize_https_config_summary, self.request.tid)

    def post(self):
        return tw(db_try_to_enable_https, self.request.tid, self.session.user_id)

    def put(self):
        return tw(db_disable_https, self.request.tid, self.session.user_id)

    def delete(self):
        return tw(db_reset_https_config, self.request.tid, self.session.user_id)


class CSRHandler(BaseHandler):
    check_roles = 'admin'
    root_tenant_or_management_only = True

    def post(self):
        request = self.validate_request(self.request.content.read(),
                                        requests.AdminCSRDesc)

        csr_fields = {
            'C': request['country'].upper(),
            'ST': request['province'],
            'L': request['city'],
            'O': request['company'],
            'OU': request['company'],
            'CN': State.tenants[self.request.tid].cache.hostname,
            'emailAddress': request['email'],
        }

        return self.perform_action(self.request.tid, csr_fields)

    @staticmethod
    @transact
    def perform_action(session, tid, csr_fields):
        db_cfg = db_load_tls_config(session, tid, True)

        pkv = tls.KeyValidator()
        ok, _ = pkv.validate(db_cfg)
        if not ok:
            raise errors.InputValidationError

        key_pair = db_cfg['ssl_key']
        return tls.gen_x509_csr_pem(key_pair, csr_fields, Settings.csr_sign_bits)


class AcmeHandler(BaseHandler):
    check_roles = 'admin'
    root_tenant_or_management_only = True

    @inlineCallbacks
    def post(self):
        yield tw(db_acme_cert_request, self.request.tid)
        yield tw(db_log, tid=self.request.tid, type='request_acme_cert', user_id=self.session.user_id)


class AcmeChallengeHandler(BaseHandler):
    check_roles = 'any'

    def get(self, token):
        tmp_chall_dict = State.tenants[self.request.tid].acme_tmp_chall_dict
        if token in tmp_chall_dict:
            return tmp_chall_dict[token].tok

        raise errors.ResourceNotFound
