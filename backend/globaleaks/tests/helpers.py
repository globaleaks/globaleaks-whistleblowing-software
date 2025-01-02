# -*- coding: utf-8
"""
Utilities and basic TestCases.
"""
import base64
import json
import os
import shutil

from datetime import timedelta

from nacl.encoding import Base32Encoder, Base64Encoder

from urllib.parse import urlsplit  # pylint: disable=import-error

from twisted.internet.address import IPv4Address
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred
from twisted.internet.task import Clock
from twisted.python.failure import Failure
from twisted.trial import unittest
from twisted.web.test.requesthelper import DummyRequest

from . import TEST_DIR

from globaleaks import db, models, orm, event, jobs, __version__, DATABASE_VERSION
from globaleaks.db.appdata import load_appdata
from globaleaks.orm import transact, tw
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.admin.context import create_context, get_context
from globaleaks.handlers.admin.field import db_create_field
from globaleaks.handlers.admin.questionnaire import db_get_questionnaire
from globaleaks.handlers.admin.step import db_create_step
from globaleaks.handlers.admin.tenant import create as create_tenant
from globaleaks.handlers.admin.user import create_user
from globaleaks.handlers.recipient import rtip
from globaleaks.handlers.wizard import db_wizard
from globaleaks.handlers.whistleblower import wbtip
from globaleaks.handlers.whistleblower.submission import create_submission
from globaleaks.models import serializers
from globaleaks.models.config import db_set_config_variable
from globaleaks.rest import decorators
from globaleaks.rest.api import JSONEncoder
from globaleaks.sessions import initialize_submission_session, Sessions
from globaleaks.settings import Settings
from globaleaks.state import State, TenantState
from globaleaks.utils import tempdict, token
from globaleaks.utils.crypto import generateRandomKey, GCE
from globaleaks.utils.securetempfile import SecureTemporaryFile
from globaleaks.utils.utility import datetime_now, uuid4
from globaleaks.utils.log import log

GCE.options['OPSLIMIT'] = 1

################################################################################
# BEGIN MOCKS NECESSARY FOR DETERMINISTIC ENCRYPTION
VALID_PASSWORD1 = 'ACollectionOfDiplomaticHistorySince_1966_ToThe_Pr esentDay#'
VALID_PASSWORD2 = VALID_PASSWORD1
VALID_SALT1 = GCE.generate_salt()
VALID_SALT2 = GCE.generate_salt()
VALID_HASH1 = GCE.hash_password(VALID_PASSWORD1, VALID_SALT1)
VALID_HASH2 = GCE.hash_password(VALID_PASSWORD2, VALID_SALT2)
VALID_BASE64_IMG = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQYV2NgYAAAAAMAAWgmWQ0AAAAASUVORK5CYII='
INVALID_PASSWORD = 'antani'

KEY = GCE.generate_key()
USER_KEY = GCE.derive_key(VALID_PASSWORD1, VALID_SALT1)
USER_PRV_KEY, USER_PUB_KEY = GCE.generate_keypair()
USER_PRV_KEY_ENC = Base64Encoder.encode(GCE.symmetric_encrypt(USER_KEY, USER_PRV_KEY))
USER_BKP_KEY, USER_REC_KEY = GCE.generate_recovery_key(USER_PRV_KEY)
USER_REC_KEY_PLAIN = GCE.asymmetric_decrypt(USER_PRV_KEY, Base64Encoder.decode(USER_REC_KEY))
USER_REC_KEY_PLAIN = Base32Encoder.encode(USER_REC_KEY_PLAIN).replace(b'=', b'').decode('utf-8')
GCE_orig_generate_key = GCE.generate_key
GCE_orig_generate_keypair = GCE.generate_keypair

TOKEN = b"31b780b6eb6357e324eea7c3a5d2542067c4d537f4f4de77473c93d48dd8a758"
TOKEN_ANSWER = b"31b780b6eb6357e324eea7c3a5d2542067c4d537f4f4de77473c93d48dd8a758:149619"
def mock_nullfunction(*args, **kwargs):
    return


def mock_GCE_generate_key():
    return KEY


def mock_GCE_generate_keypair():
    return USER_PRV_KEY, USER_PUB_KEY


setattr(GCE, 'generate_key', mock_GCE_generate_key)
setattr(GCE, 'generate_keypair', mock_GCE_generate_keypair)
# END MOCKS NECESSARY FOR DETERMINISTIC ENCRYPTION
################################################################################

PGPKEYS = {}

DATA_DIR = os.path.join(TEST_DIR, 'data')
kp = os.path.join(DATA_DIR, 'gpg')
for filename in os.listdir(kp):
    with open(os.path.join(kp, filename)) as pgp_file:
        PGPKEYS[filename] = pgp_file.read()


log.print = mock_nullfunction


HTTPS_DATA = {
  'key': 'key.pem',
  'cert': 'cert.pem',
  'chain': 'chain.pem'
}


HTTPS_DATA_DIR = os.path.join(DATA_DIR, 'https')
for k, fname in HTTPS_DATA.items():
    with open(os.path.join(HTTPS_DATA_DIR, 'valid', fname), 'r') as fd:
        HTTPS_DATA[k] = fd.read()


class FakeThreadPool(object):
    """
    A fake L{twisted.python.threadpool.ThreadPool}, running functions inside
    the main thread instead for easing tests.
    """

    def callInThreadWithCallback(self, onResult, func, *args, **kw):
        success = True
        try:
            result = func(*args, **kw)
        except:
            result = Failure()
            success = False

        onResult(success, result)


def init_state():
    Settings.set_devel_mode()
    Settings.disable_notifications = True
    Settings.failed_login_attempts.clear()
    Settings.working_path = os.path.abspath('./working_path')

    Settings.eval_paths()

    if os.path.exists(Settings.working_path):
        shutil.rmtree(Settings.working_path)

    orm.set_thread_pool(FakeThreadPool())

    State.settings.enable_api_cache = False
    State.tenants[1] = TenantState()
    State.tenants[1].cache.hostname = 'www.globaleaks.org'
    State.tenants[1].cache.encryption = True

    State.init_environment()

    Sessions.clear()


@transact
def mock_users_keys(session):
    for user in session.query(models.User):
        user.hash = VALID_HASH1
        user.salt = VALID_SALT1
        user.crypto_prv_key = USER_PRV_KEY_ENC
        user.crypto_pub_key = USER_PUB_KEY
        user.crypto_bkp_key = USER_BKP_KEY
        user.crypto_rec_key = USER_REC_KEY


def get_token():
    token = State.tokens.new(1)
    State.tokens.pop(token.id)
    token.id = TOKEN
    State.tokens[token.id] = token
    return TOKEN_ANSWER


def get_dummy_step():
    return {
        'id': '',
        'label': 'Step 1',
        'description': 'Step Description',
        'order': 0,
        'triggered_by_score': 0,
        'triggered_by_options': [],
        'questionnaire_id': '',
        'children': []
    }


def get_dummy_field():
    return {
        'id': '',
        'instance': 'template',
        'template_id': '',
        'template_override_id': '',
        'step_id': '',
        'fieldgroup_id': '',
        'label': 'antani',
        'placeholder': '',
        'type': 'checkbox',
        'description': 'field description',
        'hint': 'field hint',
        'multi_entry': False,
        'required': False,
        'attrs': {},
        'options': get_dummy_fieldoption_list(),
        'children': [],
        'y': 1,
        'x': 1,
        'width': 0,
        'triggered_by_score': 0,
        'triggered_by_options': []
    }


def get_dummy_fieldoption_list():
    return [
        {
            'id': uuid4(),
            'label': 'Cafe del mare',
            'order': 0,
            'score_points': 100,
            'score_type': 'none',
            'trigger_receiver': [],
            'hint1': '',
            'hint2': '',
            'block_submission': False
        },
        {
            'id': uuid4(),
            'label': 'skrilx is here',
            'order': 0,
            'score_points': 97,
            'score_type': 'none',
            'trigger_field': '',
            'trigger_step': '',
            'trigger_receiver': [],
            'hint1': '',
            'hint2': '',
            'block_submission': False
        }
    ]


class MockDict:
    """
    This class just create all the shit we need for emulate a Node
    """

    def __init__(self):
        self.dummyUser = {
            'id': '',
            'username': 'maker@iz.cool.yeah',
            'password': VALID_PASSWORD1,
            'old_password': '',
            'salt': VALID_SALT1,
            'role': 'receiver',
            'enabled': True,
            'name': 'Generic User',
            'description': 'King MockDummy',
            'last_login': '1970-01-01 00:00:00.000000',
            'language': 'en',
            'password_change_needed': False,
            'password_change_date': '1970-01-01 00:00:00.000000',
            'pgp_key_fingerprint': '',
            'pgp_key_public': '',
            'pgp_key_expiration': '1970-01-01 00:00:00.000000',
            'pgp_key_remove': False,
            'notification': True,
            'forcefully_selected': True,
            'can_edit_general_settings': False,
            'can_grant_access_to_reports': True,
            'can_transfer_access_to_reports': True,
            'can_delete_submission': True,
            'can_postpone_expiration': True,
            'can_mask_information': True,
            'can_redact_information': True,
            'contexts': []
        }

        self.dummyContext = {
            'id': '',
            'name': 'Already localized name',
            'description': 'Already localized desc',
            'order': 0,
            'receivers': [],
            'questionnaire_id': 'default',
            'additional_questionnaire_id': '',
            'select_all_receivers': True,
            'tip_timetolive': 20,
            'tip_reminder': 80,
            'maximum_selectable_receivers': 0,
            'show_context': True,
            'allow_recipients_selection': False,
            'show_receivers_in_alphabetical_order': False,
        }

        self.dummySubmission = {
            'context_id': '',
            'answers': {},
            'receivers': [],
            'removed_files': [],
            'mobile': False
        }

        self.dummyNode = {
            'name': 'Please, set me: name/title',
            'description': 'Platform description',
            'presentation': 'This is whæt æpp€ærs on top',
            'footer': 'check it out https://www.youtube.com/franksentus ;)',
            'footer_accessibility_declaration': '',
            'footer_privacy_policy': '',
            'footer_whistleblowing_policy': '',
            'disclaimer_text': '',
            'whistleblowing_question': '',
            'whistleblowing_button': '',
            'hostname': 'www.globaleaks.org',
            'rootdomain': 'antani.gov',
            'email': 'email@dummy.net',
            'languages_supported': [],  # ignored
            'languages_enabled': ['it', 'en'],
            'latest_version': __version__,
            'receipt_salt': '<<the Lannisters send their regards>>',
            'maximum_filesize': 30,
            'allow_indexing': False,
            'disable_submissions': False,
            'disable_privacy_badge': False,
            'timezone': 0,
            'default_language': 'en',
            'default_questionnaire': 'default',
            'admin_language': 'en',
            'simplified_login': False,
            'enable_scoring_system': False,
            'enable_signup': True,
            'mode': 'default',
            'signup_tos1_enable': False,
            'signup_tos1_title': '',
            'signup_tos1_text': '',
            'signup_tos1_checkbox_label': '',
            'signup_tos2_enable': False,
            'signup_tos2_title': '',
            'signup_tos2_text': '',
            'signup_tos2_checkbox_label': '',
            'enable_custom_privacy_badge': False,
            'custom_privacy_badge_text': '',
            'header_title_homepage': '',
            'contexts_clarification': '',
            'show_contexts_in_alphabetical_order': False,
            'threshold_free_disk_megabytes_high': 200,
            'threshold_free_disk_megabytes_low': 1000,
            'threshold_free_disk_percentage_high': 3,
            'threshold_free_disk_percentage_low': 10,
            'password_change_period': 90,
            'unread_reminder_time': 1,
            'enable_admin_exception_notification': True,
            'enable_developers_exception_notification': True,
            'counter_submissions': 0,
            'log_level': 'DEBUG',
            'log_accesses_of_internal_users': False,
            'two_factor': False,
            'encryption': False,
            'escrow': False,
            'adminonly': False,
            'basic_auth': False,
            'basic_auth_username': '',
            'basic_auth_password': '',
            'custom_support_url': '',
            'pgp': False,
            'user_privacy_policy_text': '',
            'user_privacy_policy_url': ''
        }

        self.dummyNetwork = {
            'anonymize_outgoing_connections': True,
            'hostname': 'www.globaleaks.org',
            'https_admin': True,
            'https_analyst': True,
            'https_custodian': True,
            'https_receiver': True,
            'https_whistleblower': True,
            'ip_filter_admin': '',
            'ip_filter_admin_enable': False,
            'ip_filter_analyst': '',
            'ip_filter_analyst_enable': False,
            'ip_filter_custodian': '',
            'ip_filter_custodian_enable': False,
            'ip_filter_receiver': '',
            'ip_filter_receiver_enable': False,
            'reachable_via_web': True
        }

        self.dummyWizard = {
            'node_language': 'en',
            'node_name': 'test',
            'admin_username': 'admin',
            'admin_name': 'Giovanni Pellerano',
            'admin_password': 'P4ssword!@#',
            'admin_mail_address': 'evilaliv3@globaleaks.org',
            'admin_escrow': True,
            'receiver_username': 'receipient',
            'receiver_name': 'Fabio Pietrosanti',
            'receiver_password': 'P4ssword!@#',
            'receiver_mail_address': 'naif@globaleaks.org',
            'profile': 'default',
            'skip_admin_account_creation': False,
            'skip_recipient_account_creation': False,
            'enable_developers_exception_notification': True
        }

        self.dummySignup = {
            'name': 'Responsabile',
            'surname': 'Anticorruzione',
            'role': '',
            'email': 'rpct@anticorruzione.it',
            'phone': '',
            'subdomain': 'anac',
            'organization_name': 'Autorità Nazionale Anticorruzione',
            'organization_tax_code': '',
            'organization_vat_code': '',
            'organization_location': '',
            'tos1': True,
            'tos2': True
        }


def get_dummy_file(content=None):
    filename = generateRandomKey() + ".pdf"

    content_type = 'application/pdf'

    if content is None:
        content = base64.b64decode(VALID_BASE64_IMG)

    temporary_file = SecureTemporaryFile(Settings.tmp_path)

    with temporary_file.open('w') as f:
        f.write(content)

    State.TempUploadFiles[os.path.basename(temporary_file.filepath)] = temporary_file

    return {
        'id': filename,
        'date': datetime_now(),
        'name': filename,
        'description': 'description',
        'body': temporary_file,
        'size': len(content),
        'filename': os.path.basename(temporary_file.filepath),
        'type': content_type,
        'submission': False,
        "reference_id": '',
        "visibility": b'public'
    }


def check_confirmation(self):
    return


BaseHandler.check_confirmation = check_confirmation


def get_file_upload(self):
    return get_dummy_file()


BaseHandler.get_file_upload = get_file_upload


def forge_request(uri=b'https://www.globaleaks.org/',
                  headers=None, body='', args=None, client_addr=b'127.0.0.1', method=b'GET'):
    """
    Creates a twisted.web.Request compliant request that is from an external
    IP address.
    """
    if headers is None:
        headers = {}

    if args is None:
        args = {}

    _, host, path, query, frag = urlsplit(uri)

    x = host.split(b':')
    if len(x) > 1:
        host = x[0]
        port = int(x[1])
    else:
        if uri.startswith(b'http://'):
            port = 8080
        else:
            port = 8443

    request = DummyRequest([b''])
    request.tid = 1
    request.method = method
    request.uri = uri
    request.path = path
    request.args = args
    request._serverName = host

    request.code = 200
    request.hostname = b''
    request.headers = None
    request.client_ip = client_addr
    request.client_ua = b''
    request.client_using_mobile = False
    request.client_using_tor = False
    request.port = 8443
    request.language = 'en'
    request.multilang = False

    def isSecure():
        if request.port == 8443:
            return True
        else:
            return False

    request.isSecure = isSecure
    request.client_using_tor = False

    def getResponseBody():
        # Ugh, hack. Twisted returns this all as bytes, and we want it as str
        if isinstance(request.written[0], bytes):
            return b''.join(request.written)
        else:
            return ''.join(request.written)

    request.getResponseBody = getResponseBody

    def getHost():
        return IPv4Address('TCP', request.client_ip, port)

    request.client = getHost()
    request.getHost = getHost

    def notifyFinish():
        return Deferred()

    request.notifyFinish = notifyFinish

    request.requestHeaders.setRawHeaders('host', [b'127.0.0.1'])
    request.requestHeaders.setRawHeaders('user-agent', [b'NSA Agent'])

    for k, v in headers.items():
        request.requestHeaders.setRawHeaders(k, [v])

    request.headers = request.getAllHeaders()

    class fakeBody(object):
        def read(self):
            ret = body
            if isinstance(ret, dict):
                ret = json.dumps(ret, cls=JSONEncoder)

            if isinstance(ret, str):
                ret = ret.encode()

            return ret

        def close(self):
            pass

    request.content = fakeBody()

    return request


class TestGL(unittest.TestCase):
    initialize_test_database_using_archived_db = True
    pgp_configuration = 'ALL'

    @inlineCallbacks
    def setUp(self):
        self.test_reactor = Clock()

        jobs.job.reactor = self.test_reactor
        tempdict.TempDict.reactor = self.test_reactor

        self.state = State

        init_state()

        self.setUp_dummy()

        if self.initialize_test_database_using_archived_db:
            shutil.copy(
                os.path.join(TEST_DIR, 'db', 'empty', 'globaleaks-%d.db' % DATABASE_VERSION),
                os.path.join(Settings.db_file_path)
            )
        else:
            yield db.create_db()
            yield db.initialize_db()

        yield self.set_hostnames(1)

        yield db.refresh_tenant_cache()

        self.state.reset_minutely()
        self.state.reset_hourly()

        self.internationalized_text = load_appdata()['node']['whistleblowing_button']

    @transact
    def set_hostnames(self, session, i):
        hosts = [('www.globaleaks.org', 'aaaaaaaaaaaaaaaa.onion'),
                 ('www.domain-a.com', 'bbbbbbbbbbbbbbbb.onion'),
                 ('www.domain-b.com', 'cccccccccccccccc.onion')]

        hostname, onionservice = hosts[i - 1]
        db_set_config_variable(session, i, 'hostname', hostname)
        db_set_config_variable(session, i, 'onionservice', onionservice)

    def setUp_dummy(self):
        dummyStuff = MockDict()

        self.dummyWizard = dummyStuff.dummyWizard
        self.dummySignup = dummyStuff.dummySignup
        self.dummyNetwork = dummyStuff.dummyNetwork
        self.dummyContext = dummyStuff.dummyContext
        self.dummySubmission = dummyStuff.dummySubmission
        self.dummyAdmin = self.get_dummy_user('admin', 'admin')
        self.dummyAnalyst = self.get_dummy_user('analyst', 'analyst')
        self.dummyCustodian = self.get_dummy_user('custodian', 'custodian')
        self.dummyReceiver_1 = self.get_dummy_receiver('receiver1')
        self.dummyReceiver_2 = self.get_dummy_receiver('receiver2')

        if self.pgp_configuration == 'ALL':
            self.dummyReceiver_1['pgp_key_public'] = PGPKEYS['VALID_PGP_KEY1_PUB']
            self.dummyReceiver_2['pgp_key_public'] = PGPKEYS['VALID_PGP_KEY2_PUB']
        elif self.pgp_configuration == 'ONE_VALID_ONE_EXPIRED':
            self.dummyReceiver_1['pgp_key_public'] = PGPKEYS['VALID_PGP_KEY1_PUB']
            self.dummyReceiver_2['pgp_key_public'] = PGPKEYS['EXPIRED_PGP_KEY_PUB']
        elif self.pgp_configuration == 'NONE':
            self.dummyReceiver_1['pgp_key_public'] = ''
            self.dummyReceiver_2['pgp_key_public'] = ''

        self.dummyNode = dummyStuff.dummyNode

        self.assertEqual(os.listdir(Settings.attachments_path), [])
        self.assertEqual(os.listdir(Settings.tmp_path), [])

    def get_dummy_user(self, role, username):
        new_u = dict(MockDict().dummyUser)
        new_u['role'] = role
        new_u['username'] = username
        new_u['name'] = new_u['public_name'] = new_u['mail_address'] = "%s@%s.xxx" % (username, username)
        new_u['description'] = ''
        new_u['password'] = VALID_PASSWORD1
        new_u['enabled'] = True
        new_u['salt'] = VALID_SALT1

        return new_u

    def get_dummy_receiver(self, username):
        new_u = self.get_dummy_user('receiver', username)
        new_r = dict(MockDict().dummyUser)

        return {**new_r, **new_u}

    def fill_random_field_recursively(self, answers, field):
        field_type = field['type']

        if field_type == 'checkbox':
            value = {}
            for option in field['options']:
                value[option['id']] = 'True'
        elif field_type == 'selectbox':
            value = {'value': field['options'][0]['id']}
        elif field_type == 'date':
            value = {'value': datetime_now()}
        elif field_type == 'tos':
            value = {'value': 'True'}
        elif field_type == 'fieldgroup':
            value = {}
            for child in field['children']:
                self.fill_random_field_recursively(value, child)
        else:
            value = {'value': ''.join(chr(x) for x in range(0x400, 0x4FF))}

        answers[field['id']] = [value]

    @transact
    def fill_random_answers(self, session, questionnaire_id):
        """
        return randomly populated questionnaire
        """
        answers = {}

        questionnaire = db_get_questionnaire(session, 1, questionnaire_id, 'en')

        for step in questionnaire['steps']:
            for field in step['children']:
                self.fill_random_field_recursively(answers, field)

        return answers

    @inlineCallbacks
    def get_dummy_submission(self, context_id):
        """
        this may works until the content of the fields do not start to be validated. like
        numbers shall contain only number, and not URL.
        This validation would not be implemented in validate_request but in structures.Fields

        need to be enhanced generating appropriate data based on the fields.type
        """
        context = yield get_context(1, context_id, 'en')
        answers = yield self.fill_random_answers(context['questionnaire_id'])

        returnValue({
            'context_id': context_id,
            'receivers': context['receivers'],
            'removed_files': [],
            'identity_provided': False,
            'score': 0,
            'answers': answers
        })

    def get_dummy_file(self, content=None):
        return get_dummy_file(content)

    def get_dummy_redirect(self, x=''):
        return {
            'path1': '/path1-' + x,
            'path2': '/path2-' + x
        }

    def emulate_file_upload(self, session, n):
        """
        This emulates the file upload of an incomplete submission
        """
        for _ in range(n):
            session.files.append(self.get_dummy_file())

    def pollute_events(self, number_of_times=10):
        for _ in range(number_of_times):
            for event_obj in event.events_monitored:
                for x in range(2):
                    e = event.Event(event_obj, timedelta(seconds=1.0 * x))
                    self.state.tenants[1].RecentEventQ.append(e)
                    self.state.tenants[1].EventQ.append(e)

    @transact
    def get_rtips(self, session):
        ret = []
        for i, r in session.query(models.InternalTip, models.ReceiverTip) \
                         .filter(models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                 models.InternalTip.tid == 1):
            ret.append(serializers.serialize_rtip(session, i, r, 'en'))

        return ret

    @transact
    def get_wbfiles(self, session, rtip_id):
        return [x[0] for x in session.query(models.WhistleblowerFile.id) \
                                     .filter(models.WhistleblowerFile.receivertip_id == rtip_id)]

    @transact
    def get_ifiles_by_wbtip_id(self, session, wbtip_id):
        return [x[0] for x in session.query(models.InternalFile.id) \
                                     .filter(models.InternalFile.internaltip_id == wbtip_id)]

    @transact
    def get_wbtips(self, session):
        ret = []
        for i in session.query(models.InternalTip) \
                        .filter(models.InternalTip.tid == 1):
            x = serializers.serialize_wbtip(session, i, 'en')
            x['receivers_ids'] = list(zip(*session.query(models.ReceiverTip.receiver_id)
                                           .filter(models.ReceiverTip.internaltip_id == i.id)))[0]
            ret.append(x)

        return ret

    @transact
    def get_rfiles(self, session, wbtip_id):
        return [{'id': rfile.id} for rfile in session.query(models.ReceiverFile)
                                                       .filter(models.ReceiverFile.internaltip_id == wbtip_id)]

    def db_test_model_count(self, session, model, n):
        self.assertEqual(session.query(model).count(), n)

    @transact
    def test_model_count(self, session, model, n):
        self.db_test_model_count(session, model, n)

    @transact
    def get_model_count(self, session, model):
        return session.query(model).count()


class TestGLWithPopulatedDB(TestGL):
    complex_field_population = False
    population_of_recipients = 2
    population_of_submissions = 2
    population_of_attachments = 2
    population_of_tenants = 3

    @inlineCallbacks
    def setUp(self):
        yield TestGL.setUp(self)
        yield self.fill_data()
        yield db.refresh_tenant_cache()

    @inlineCallbacks
    def fill_data(self):
        # fill_data/create_admin
        self.dummyAdmin = yield create_user(1, None, self.dummyAdmin, 'en')

        # fill_data/create_custodian
        self.dummyAnalyst = yield create_user(1, None, self.dummyAnalyst, 'en')

        # fill_data/create_custodian
        self.dummyCustodian = yield create_user(1, None, self.dummyCustodian, 'en')

        # fill_data/create_receiver
        self.dummyReceiver_1 = yield create_user(1, None, self.dummyReceiver_1, 'en')
        self.dummyReceiver_2 = yield create_user(1, None, self.dummyReceiver_2, 'en')

        yield mock_users_keys()

        # fill_data/create_context
        self.dummyContext['receivers'] = [self.dummyReceiver_1['id'], self.dummyReceiver_2['id']]
        self.dummyContext = yield create_context(1, None, self.dummyContext, 'en')

        self.dummyQuestionnaire = yield tw(db_get_questionnaire, 1, self.dummyContext['questionnaire_id'], 'en')

        self.dummyQuestionnaire['steps'].append(get_dummy_step())
        self.dummyQuestionnaire['steps'][1]['questionnaire_id'] = self.dummyContext['questionnaire_id']
        self.dummyQuestionnaire['steps'][1]['label'] = 'Whistleblower identity'
        self.dummyQuestionnaire['steps'][1]['order'] = 1
        self.dummyQuestionnaire['steps'][1] = yield tw(db_create_step, 1, self.dummyQuestionnaire['steps'][1], 'en')

        if self.complex_field_population:
            yield self.add_whistleblower_identity_field_to_step(self.dummyQuestionnaire['steps'][1]['id'])

        for i in range(1, self.population_of_tenants):
            name = 'tenant-' + str(i+1)
            t = yield create_tenant({'mode': 'default', 'name': name, 'active': True, 'subdomain': name})
            yield tw(db_wizard, t['id'], '127.0.0.1', self.dummyWizard)
            yield self.set_hostnames(i+1)

    @transact
    def add_whistleblower_identity_field_to_step(self, session, step_id):
        wbf = session.query(models.Field).filter(models.Field.id == 'whistleblower_identity', models.Field.tid == 1).one()

        reference_field = get_dummy_field()
        reference_field['instance'] = 'reference'
        reference_field['template_id'] = wbf.id
        reference_field['step_id'] = step_id
        db_create_field(session, 1, reference_field, 'en')

    def perform_submission_start(self):
        return initialize_submission_session(1)

    def perform_submission_uploads(self, submission_id):
        for _ in range(self.population_of_attachments):
            Sessions.get(submission_id).files.append(self.get_dummy_file())

    @inlineCallbacks
    def perform_submission_actions(self, session_id):
        session = Sessions.get(session_id)

        self.dummySubmission['context_id'] = self.dummyContext['id']
        self.dummySubmission['receivers'] = self.dummyContext['receivers']
        self.dummySubmission['identity_provided'] = False
        self.dummySubmission['answers'] = yield self.fill_random_answers(self.dummyContext['questionnaire_id'])
        self.dummySubmission['score'] = 0
        self.dummySubmission['removed_files'] = []

        self.lastReceipt = (yield create_submission(1,
                                                   self.dummySubmission,
                                                   session,
                                                   True,
                                                   False))['receipt']

    @inlineCallbacks
    def perform_post_submission_actions(self):
        self.dummyRTips = yield self.get_rtips()

        for rtip_desc in self.dummyRTips:
            yield rtip.create_comment(1,
                                      rtip_desc['receiver_id'],
                                      rtip_desc['id'],
                                      'comment')

        self.dummyWBTips = yield self.get_wbtips()

        for wbtip_desc in self.dummyWBTips:
            yield wbtip.create_comment(1,
                                       wbtip_desc['id'],
                                       'comment')

    @inlineCallbacks
    def perform_minimal_submission_actions(self):
        session = self.perform_submission_start()
        self.perform_submission_uploads(session.id)
        yield self.perform_submission_actions(session.id)

    @inlineCallbacks
    def perform_full_submission_actions(self):
        """Populates the DB with tips, comments, and files"""
        for x in range(self.population_of_submissions):
            session = self.perform_submission_start()
            self.perform_submission_uploads(session.id)
            yield self.perform_submission_actions(session.id)

        yield self.perform_post_submission_actions()

    @transact
    def force_wbtip_expiration(self, session):
        session.query(models.InternalTip).update({'last_access': datetime_now()})

    @transact
    def force_itip_expiration(self, session):
        session.query(models.InternalTip).update({'expiration_date': datetime_now()})

    @transact
    def set_itips_near_to_expire(self, session):
        date = datetime_now() + timedelta(hours=self.state.tenants[1].cache.notification.tip_expiration_threshold - 1)
        session.query(models.InternalTip).update({'expiration_date': date})

    @transact
    def set_contexts_timetolive(self, session, ttl):
        session.query(models.Context).update({'tip_timetolive': ttl})


class TestHandler(TestGLWithPopulatedDB):
    """
    :attr _handler: handler class to be tested
    """
    _handler = None
    _test_desc = {}
    # _test_desc = {
    #  'model': Context
    #  'create': context.create_context
    #  'data': {
    #
    #  }
    # }

    def setUp(self):
        self.session = None
        return TestGL.setUp(self)

    def request(self, body='', uri=b'https://www.globaleaks.org/',
                user_id=None, role=None, multilang=False, headers=None, args=None,
                client_addr=b'127.0.0.1', handler_cls=None, attached_file=None,
                kwargs=None, token=False):
        """
        Constructs a handler for preforming mock requests using the bag of params described below.
        """
        from globaleaks.rest import api
        if headers is None:
            headers = {}

        if args is None:
            args = {}

        if kwargs is None:
            kwargs = {}

        session = None

        if user_id is None and role is not None:
            if role == 'admin':
                user_id = self.dummyAdmin['id']
            elif role == 'analyst':
                user_id = self.dummyAnalyst['id']
            elif role == 'receiver':
                user_id = self.dummyReceiver_1['id']
            elif role == 'custodian':
                user_id = self.dummyCustodian['id']

        if role is not None:
            if role == 'whistlebower':
                session = initialize_submission_session(1)
            else:
                session = Sessions.new(1, user_id, 1, role, USER_PRV_KEY)

            headers[b'x-session'] = session.id

        # during unit tests a token is always provided to any handler
        headers[b'x-token'] = get_token()

        if handler_cls is None:
            handler_cls = self._handler

        request = forge_request(uri=uri,
                                headers=headers,
                                args=args,
                                body=body,
                                client_addr=client_addr,
                                method=b'GET')

        x = api.APIResourceWrapper()

        if not getattr(handler_cls, 'decorated', False):
            for method in ['get', 'post', 'put', 'delete']:
                if getattr(handler_cls, method, None) is not None:
                    decorators.decorate_method(handler_cls, method)
                    handler_cls.decorated = True

        handler = handler_cls(self.state, request, **kwargs)

        if multilang:
            request.language = None

        if handler.upload_handler:
            handler.uploaded_file = self.get_dummy_file(attached_file)

        return handler

    def ss_serial_desc(self, safe_set, request_desc):
        """
        Constructs a request_dec parser of a handler that uses a safe_set in its serialization
        """
        return {k: v for k, v in request_desc.items() if k in safe_set}

    def get_dummy_request(self):
        return self._test_desc['model']().dict(u'en')


class TestCollectionHandler(TestHandler):
    @inlineCallbacks
    def setUp(self):
        yield TestHandler.setUp(self)
        yield self.fill_data()

    @inlineCallbacks
    def fill_data(self):
        # fill_data/create_admin
        self.dummyAdmin = yield create_user(1, None, self.dummyAdmin, 'en')

    @inlineCallbacks
    def test_get(self):
        if not self._test_desc:
            return

        data = self.get_dummy_request()

        yield self._test_desc['create'](1, self.session, data, 'en')

        handler = self.request(role='admin')

        if hasattr(handler, 'get'):
            yield handler.get()

    @inlineCallbacks
    def test_post(self):
        if not self._test_desc:
            return

        data = self.get_dummy_request()

        for k, v in self._test_desc['data'].items():
            data[k] = v

        handler = self.request(data, role='admin')

        if hasattr(handler, 'post'):
            data = yield handler.post()

            for k, v in self._test_desc['data'].items():
                self.assertEqual(data[k], v)


class TestInstanceHandler(TestHandler):
    @inlineCallbacks
    def setUp(self):
        yield TestHandler.setUp(self)
        yield self.fill_data()

    @inlineCallbacks
    def fill_data(self):
        # fill_data/create_admin
        self.dummyAdmin = yield create_user(1, None, self.dummyAdmin, 'en')

    @inlineCallbacks
    def test_get(self):
        if not self._test_desc:
            return

        data = self.get_dummy_request()

        data = yield self._test_desc['create'](1, self.session, data, 'en')

        handler = self.request(data, role='admin')

        if hasattr(handler, 'get'):
            yield handler.get(data['id'])

    @inlineCallbacks
    def test_put(self):
        if not self._test_desc:
            return

        data = self.get_dummy_request()

        data = yield self._test_desc['create'](1, self.session, data, 'en')

        for k, v in self._test_desc['data'].items():
            data[k] = v

        handler = self.request(data, role='admin')

        if hasattr(handler, 'put'):
            data = yield handler.put(data['id'])

            for k, v in self._test_desc['data'].items():
                self.assertEqual(data[k], v)

    @inlineCallbacks
    def test_delete(self):
        if not self._test_desc:
            return

        data = self.get_dummy_request()

        data = yield self._test_desc['create'](1, self.session, data, 'en')

        handler = self.request(data, role='admin')

        if hasattr(handler, 'delete'):
            yield handler.delete(data['id'])


class TestHandlerWithPopulatedDB(TestHandler):
    def setUp(self):
        return TestGLWithPopulatedDB.setUp(self)
