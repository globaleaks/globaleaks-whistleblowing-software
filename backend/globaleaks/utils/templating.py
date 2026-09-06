# This filte contains routines dealing with texts templates and variables replacement used
# mainly in mail notifications.
import copy
import re

from datetime import datetime, timedelta

from globaleaks import __version__
from globaleaks.rest import errors
from globaleaks.utils.pgp import PGPContext
from globaleaks.utils.sock import is_ip_address
from globaleaks.utils.utility import \
    datetime_to_pretty_str, \
    datetime_to_day_str, \
    bytes_to_pretty_str, \
    iso8601_to_day_str, \
    snake_case

node_keywords = [
    '{NodeName}',
    '{TorSite}',
    '{HTTPSSite}',
    '{TorUrl}',
    '{HTTPSUrl}',
    '{Site}',
    '{Url}',
    '{DocumentationUrl}',
    '{LoginUrl}',
]

user_keywords = [
    '{RecipientName}',
    '{Username}'
]

tip_keywords = [
    '{TipID}',
    '{TipNum}',
    '{TipLabel}',
    '{TipStatus}',
    '{EventTime}',
    '{SubmissionDate}',
    '{QuestionnaireAnswers}',
    '{Comments}'
]

file_keywords = [
    '{FileName}',
    '{FileSize}'
]

export_comment_keywords = [
    '{Author}',
    '{Content}'
]

transmission_keywords = [
    '{TransmissionTenantName}'
]

expiration_summary_keywords = [
    '{ExpiringSubmissionCount}',
    '{EarliestExpirationDate}'
]

admin_pgp_alert_keywords = [
    '{PGPKeyInfoList}'
]

user_pgp_alert_keywords = [
    '{PGPKeyInfo}'
]

admin_anomaly_keywords = [
    '{AnomalyDetailDisk}',
    '{FreeMemory}',
    '{TotalMemory}'
]

https_expr_keywords = [
    '{ExpirationDate}'
]

software_update_keywords = [
    '{InstalledVersion}',
    '{LatestVersion}',
    '{ChangeLogUrl}',
    '{UpdateGuideUrl}',
]

user_credentials_keywords = [
    '{Role}',
    '{Username}',
    '{Password}'
]

signup_invite_keywords = [
    '{RecipientName}',
    '{OrganizationName}',
    '{InviteUrl}',
    '{ExpirationDate}'
]

platform_signup_keywords = [
    '{RecipientName}',
    '{ActivationUrl}',
    '{ExpirationDate}',
    '{Name}',
    '{Surname}',
    '{Email}',
    '{Language}',
    '{Credentials}',
    '{AdminCredentials}',
    '{RecipientCredentials}'
]

email_validation_keywords = [
    '{RecipientName}',
    '{NewEmailAddress}'
]

identity_access_request_keywords = [
    '{RecipientName}',
    '{TipNum}',
]

two_factor_auth_keywords = [
    '{AuthCode}'
]


account_activation_keywords = [
    '{AccountRecoveryKeyInstructions}'
]


def indent(n=1):
    return '  ' * n


def indent_text(text, n=1):
    """
    Add n * 2 space as indentation to each of the non empty lines of the provided text
    """
    return '\n'.join([('  ' * n if not line.isspace() else '') + line for line in text.splitlines()])


class Keyword:
    keyword_list = []
    data_keys = []

    def __init__(self, data):
        for k in self.data_keys:
            if k not in data:
                raise errors.InternalServerError(f'Missing key \'{k}\' while resolving template \'{type(self).__name__}\'')

        self.data = data


class NodeKeyword(Keyword):
    keyword_list = node_keywords
    data_keys = ['node', 'notification']

    def node_name(self):
        return self.data['node']['name']

    def tor_site(self):
        if self.data['node']['onionservice']:
            return 'http://' + self.data['node']['onionservice']

        return '[UNDEFINED]'

    def https_site(self):
        if self.data['node']['hostname']:
            if is_ip_address(self.data['node']['hostname']):
                return 'http://' + self.data['node']['hostname']
            else:
                return 'https://' + self.data['node']['hostname']

        return '[UNDEFINED]'

    def site(self):
        if self.data['node']['hostname']:
            return self.https_site()

        elif self.data['node']['onionservice']:
            return self.tor_site()

        return ''

    def url_path(self):
        return '/'

    def url(self):
        return self.site() + self.url_path()

    def tor_url(self):
        return self.tor_site() + self.url_path()

    def https_url(self):
        return self.https_site() + self.url_path()

    def documentation_url(self):
        return 'https://docs.globaleaks.org'

    def login_url(self):
        return self.site() + '/#/login'


class UserKeyword(Keyword):
    keyword_list = user_keywords
    data_keys = ['user']

    def recipient_name(self):
        return self.data['user']['name']

    def username(self):
        return '{}'.format(self.data['user']['username'])


class UserNodeKeyword(NodeKeyword, UserKeyword):
    keyword_list = NodeKeyword.keyword_list + UserKeyword.keyword_list
    data_keys = NodeKeyword.data_keys + UserKeyword.data_keys


def _fields_in_display_order(fields):
    """
    Yield the fields of a step in the order they are displayed in, by row and by column

    :param fields: The fields of the step
    """
    rows = {}
    for f in fields:
        rows.setdefault(f['y'], []).append(f)

    for y in sorted(rows):
        for field in sorted(rows[y], key=lambda k: k['x']):
            yield field


def _dump_checkbox_answer(field, entry, indent_n):
    """
    Return the labels of the options a checkbox answer selects
    """
    output = ''

    for k, v in entry.items():
        for option in field['options']:
            if k == option.get('id', '') and v is True:
                output += indent(indent_n) + option['label'] + '\n'

    return output


def _dump_choice_answer(field, entry, indent_n):
    """
    Return the label of the option a single choice answer selects
    """
    output = ''

    for option in field['options']:
        if entry.get('value', '') == option['id']:
            output += indent(indent_n) + option['label'] + '\n'

    return output


def _dump_date_answer(entry, indent_n):
    """
    Return the day a date answer carries
    """
    date = entry.get('value')

    return indent(indent_n) + iso8601_to_day_str(date) + '\n' if date is not None else ''


def _dump_daterange_answer(entry, indent_n):
    """
    Return the two days a date range answer carries
    """
    daterange = entry.get('value')

    if daterange is None:
        return ''

    daterange = daterange.split(':')

    return (indent(indent_n) + datetime_to_day_str(datetime.fromtimestamp(int(daterange[0])/1000)) + '\n' +
            indent(indent_n) + datetime_to_day_str(datetime.fromtimestamp(int(daterange[1])/1000)) + '\n')


def _dump_tos_answer(entry, indent_n):
    """
    Return the box a terms of service answer is rendered as
    """
    return indent(indent_n) + ('☑' if entry.get('value', '') is True else '☐') + '\n'


def _dump_answer(field_type, field, entry, indent_n):
    """
    Return the text an answer of a field is rendered as, apart from a field group

    :param field_type: The type of the field
    :param field: The field the answer belongs to
    :param entry: The answer
    :param indent_n: The depth the answer is rendered at
    """
    if field_type == 'checkbox':
        return _dump_checkbox_answer(field, entry, indent_n)

    if field_type in ['multichoice', 'selectbox']:
        return _dump_choice_answer(field, entry, indent_n)

    if field_type == 'date':
        return _dump_date_answer(entry, indent_n)

    if field_type == 'daterange':
        return _dump_daterange_answer(entry, indent_n)

    if field_type == 'tos':
        return _dump_tos_answer(entry, indent_n)

    return indent_text(entry.get('value', ''), indent_n) + '\n'


class TipKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + tip_keywords
    data_keys = UserNodeKeyword.data_keys + ['tip']

    def dump_field_entry(self, output, field, entry, indent_n):
        try:
            field_type = field['type']

            if field_type == 'fieldgroup':
                output = self.dump_fields(output, field['children'], entry, indent_n)
            else:
                output += _dump_answer(field_type, field, entry, indent_n)
        except (KeyError, TypeError, AttributeError, ValueError, OverflowError, OSError):
            # KeyError/TypeError/AttributeError: malformed field or answer dict.
            # ValueError/OverflowError/OSError: the 'daterange' branch can fail in
            # int()/datetime.fromtimestamp() on a malformed or out-of-range value
            # (e.g. an oversized timestamp). Submission validation already rejects
            # such values; this stays a defense-in-depth guard so a value that
            # nonetheless reaches the export (e.g. legacy data) degrades gracefully
            # instead of crashing the report export.
            pass

        return output + '\n'

    def dump_field(self, output, field, entries, indent_n):
        """
        Return the text a field and the answers given to it are rendered as

        :param output: The text the report is being rendered into
        :param field: The field
        :param entries: The answers given to the field
        :param indent_n: The depth the field is rendered at
        """
        output += indent(indent_n) + field['label'] + '\n'

        if len(entries) == 1:
            return self.dump_field_entry(output, field, entries[0], indent_n + 1)

        for i, entry in enumerate(entries, start=1):
            output += indent(indent_n) + '#' + str(i) + '\n'
            output = self.dump_field_entry(output, field, entry, indent_n + 2)

        return output

    def dump_fields(self, output, fields, answers, indent_n):
        for field in _fields_in_display_order(fields):
            if field['id'] not in answers or \
               field['type'] == 'fileupload' or \
               field['template_id'] == 'whistleblower_identity':
                continue

            output = self.dump_field(output, field, answers[field['id']], indent_n)

        return output

    def dump_questionnaire_answers(self, questionnaire, answers):
        output = ''

        questionnaire = sorted(questionnaire, key=lambda k: k.get('order', 0))

        for step in questionnaire:
            output += step['label'] + '\n'
            output = self.dump_fields(output, step['children'], answers, 1) + '\n'

        return output

    def dump_comments(self, comments):
        ret = ''
        for comment in comments:
            if comment['visibility'] == 'personal':
                continue

            data = copy.deepcopy(self.data)
            data['type'] = 'export_comment'
            data['comment'] = copy.deepcopy(comment)
            template = 'export_comment_recipient' if comment['author_id'] else 'export_comment_whistleblower'
            ret += indent_text('-' * 40) + '\n'
            ret += indent_text(str(Templating().format_template(self.data['notification'][template], data))) + '\n\n'

        return ret

    def tip_id(self):
        return self.data['tip']['id']

    def url_path(self):
        return '/#/reports/' + self.data['tip']['id']

    def tip_num(self):
        return str(self.data['tip']['progressive'])

    def tip_label(self):
        return self.data['tip']['label']

    def tip_status(self):
        ret = ''

        status = None

        for s in self.data['submission_statuses']:
            if self.data['tip']['status'] == s['id']:
                status = s
                ret += s['label']
                break

        if status is not None:
            for s in status['substatuses']:
                if self.data['tip']['substatus'] == s['id']:
                    ret += ' (' + s['label'] + ')'
                    break

        return ret

    def event_time(self):
        return datetime_to_pretty_str(self.data['tip']['creation_date'])

    def submission_date(self):
        return self.event_time()

    def questionnaire_answers(self):
        return self.dump_questionnaire_answers(self.data['tip']['questionnaires'][0]['steps'], self.data['tip']['questionnaires'][0]['answers'])

    def comments(self):
        comments = self.data.get('comments', [])
        comments = self.dump_comments(comments)
        return 'Comments\n' + comments + '\n' if comments else ''


class TransmissionKeyword(TipKeyword):
    """
    The report created by a transmission announces the transmission to the recipients of
    """
    keyword_list = TipKeyword.keyword_list + transmission_keywords

    def transmission_tenant_name(self):
        return (self.data['tip'].get('exchange') or {}).get('to_tenant_name', '')


class ExportMessageKeyword(TipKeyword):
    keyword_list = TipKeyword.keyword_list + export_comment_keywords
    data_keys = TipKeyword.data_keys + ['comment']

    def author(self):
        return 'Recipient' if self.data['comment']['author_id'] else 'Reporting person'

    def content(self):
        return self.data['comment']['content']

    def event_time(self):
        return datetime_to_pretty_str(self.data['comment']['creation_date'])


class ExpirationSummaryKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + expiration_summary_keywords
    data_keys = UserNodeKeyword.data_keys + ['expiring_submission_count', 'earliest_expiration_date']

    def expiring_submission_count(self):
        return str(self.data['expiring_submission_count'])

    def earliest_expiration_date(self):
        return datetime_to_pretty_str(self.data['earliest_expiration_date'])

    def url_path(self):
        return '/#/recipient/reports'


class AdminPGPAlertKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + admin_pgp_alert_keywords
    data_keys = UserNodeKeyword.data_keys + ['users']

    def pgp_key_info_list(self):
        ret = ''
        for r in self.data['users']:
            fingerprint = r['pgp_key_fingerprint']
            key = fingerprint[:7] if fingerprint is not None else ''

            ret += '\t{}, {} ({})\n'.format(r['name'],
                                        key,
                                        datetime_to_day_str(r['pgp_key_expiration']))
        return ret


class PGPAlertKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + user_pgp_alert_keywords

    def pgp_key_info(self):
        fingerprint = self.data['user']['pgp_key_fingerprint']
        key = fingerprint[:7] if fingerprint is not None else ''

        return '\t0x{} ({})'.format(key, datetime_to_day_str(self.data['user']['pgp_key_expiration']))


class AnomalyKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + admin_anomaly_keywords
    data_keys = UserNodeKeyword.data_keys + ['alert']

    def anomaly_detail_disk(self):
        # This happens all the time anomalies are present but disk is ok
        if self.data['alert']['alarm_level_disk'] == 0:
            return ''

        if self.data['alert']['alarm_level_disk'] == 1:
            return self.data['notification']['admin_anomaly_disk_low']
        else:
            return self.data['notification']['admin_anomaly_disk_high']

    def free_memory(self):
        return '{}'.format(bytes_to_pretty_str(self.data['alert']['measured_freespace']))

    def total_memory(self):
        return '{}'.format(bytes_to_pretty_str(self.data['alert']['measured_totalspace']))


class CertificateExprKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + https_expr_keywords
    data_keys = UserNodeKeyword.data_keys + ['expiration_date']

    def expiration_date(self):
        return datetime_to_pretty_str(self.data['expiration_date'])

    def url_path(self):
        return '/#/admin/network'


class SoftwareUpdateKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + software_update_keywords
    data_keys = UserNodeKeyword.data_keys + ['latest_version']

    def latest_version(self):
        return '{}'.format(self.data['latest_version'])

    def installed_version(self):
        return f'{__version__}'

    def change_log_url(self):
        return 'https://github.com/globaleaks/globaleaks-whistleblowing-software/blob/stable/CHANGELOG'

    def update_guide_url(self):
        return 'https://docs.globaleaks.org/en/stable/setup/update.html'


class UserCredentials(Keyword):
    keyword_list = user_credentials_keywords
    data_keys = ['role', 'username', 'password']

    def role(self):
        return '{}'.format(self.data['role'])

    def username(self):
        return '{}'.format(self.data['username'])

    def password(self):
        return '{}'.format(self.data['password'])


class PlatformSignupKeyword(NodeKeyword):
    keyword_list = NodeKeyword.keyword_list + platform_signup_keywords
    data_keys = NodeKeyword.data_keys + ['signup']

    def tor_site(self):
        return 'http://' + self.data['signup']['subdomain'] + '.' + self.data['node']['onionservice']

    def https_site(self):
        return 'https://' + self.data['signup']['subdomain'] + '.' + self.data['node']['rootdomain']

    def recipient_name(self):
        return self.data['signup']['name'] + ' ' + self.data['signup']['surname']

    def activation_url(self):
        if self.data['node']['hostname']:
            site = 'https://' + self.data['node']['hostname']
        elif self.data['node']['onionservice']:
            site = 'http://' + self.data['node']['onionservice']
        else:
            site = ''

        return site + '/#/activation?token=' + self.data['signup']['activation_token']

    def expiration_date(self):
        date = self.data['signup']['registration_date'] + timedelta(30)
        return datetime_to_pretty_str(date)

    def name(self):
        return self.data['signup']['name'] + ' ' + self.data['signup']['surname']

    def email(self):
        return self.data['signup']['email']

    def language(self):
        return self.data['signup']['language']

    def credentials(self):
        # Credentials are rendered only in the notification carrying the generated password
        if not self.data.get('password'):
            return ''

        data = {
            'type': 'user_credentials',
            'role': self.data.get('signup_user_role', ''),
            'username': self.data.get('signup_user_username', ''),
            'password': self.data['password']
        }

        return Templating().format_template(self.data['notification']['user_credentials'], data) + "\n"

    def admin_credentials(self):
        if not self.data['password_admin']:
            return ''

        data = {
            'type': 'user_credentials',
            'role': 'admin',
            'username': 'admin',
            'password': self.data['password_admin']
        }

        return Templating().format_template(self.data['notification']['user_credentials'], data) + "\n"

    def recipient_credentials(self):
        if not self.data['password_recipient']:
            return ''

        data = {
            'type': 'user_credentials',
            'role': 'recipient',
            'username': 'recipient',
            'password': self.data['password_recipient']
        }

        return Templating().format_template(self.data['notification']['user_credentials'], data) + "\n"


class AdminPlatformSignupKeyword(PlatformSignupKeyword):
    def recipient_name(self):
        return self.data['user']['name']


class EmailValidationKeyword(UserNodeKeyword):
    keyword_list = NodeKeyword.keyword_list + email_validation_keywords
    data_keys = NodeKeyword.data_keys + \
        ['new_email_address', 'validation_token']

    def new_email_address(self):
        return self.data['new_email_address']

    def url_path(self):
        return '/api/user/validate/email/' + self.data['validation_token']


class AccountActivationKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + account_activation_keywords

    def url_path(self):
        return '/#/password/reset' + '?token=' + self.data['reset_token']

    def account_recovery_key_instructions(self):
        if not self.data['node']['encryption']:
            return ''

        data = {'type': 'null'}

        return Templating().format_template(self.data['notification']['account_recovery_key_instructions'], data) + "\n"


class PasswordResetValidationKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list

    data_keys = UserNodeKeyword.data_keys + ['reset_token']

    def url_path(self):
        return '/#/password/reset?token=' + self.data['reset_token']


class IdentityAccessRequestKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + identity_access_request_keywords
    data_keys = UserNodeKeyword.data_keys + ['iar', 'tip', 'user']

    def tip_num(self):
        return str(self.data['tip']['progressive'])

    def url_path(self):
        return '/#/custodian/requests/'


class TenantInviteKeyword(NodeKeyword):
    keyword_list = NodeKeyword.keyword_list + signup_invite_keywords
    data_keys = NodeKeyword.data_keys + ['invite']

    def recipient_name(self):
        return self.data['invite']['organization_email']

    def organization_name(self):
        return self.data['invite']['organization_name']

    def invite_url(self):
        if self.data['node']['hostname']:
            site = 'https://' + self.data['node']['hostname']
        else:
            site = ''

        return site + '/#/signup?token=' + self.data['invite']['token']

    def expiration_date(self):
        return datetime_to_pretty_str(self.data['invite']['expiration_date'])


supported_template_types = {
    'null': Keyword,
    'tip': TipKeyword,
    'tip_access': UserNodeKeyword,
    'tip_reminder': UserNodeKeyword,
    'tip_update': TipKeyword,
    'transmission': TransmissionKeyword,
    'tip_expiration_summary': ExpirationSummaryKeyword,
    'unread_tips': UserNodeKeyword,
    'pgp_alert': PGPAlertKeyword,
    'admin_pgp_alert': AdminPGPAlertKeyword,
    'export_template': TipKeyword,
    'export_comment': ExportMessageKeyword,
    'admin_anomaly': AnomalyKeyword,
    'admin_test': UserNodeKeyword,
    'https_certificate_expiration': CertificateExprKeyword,
    'https_certificate_renewal_failure': CertificateExprKeyword,
    'software_update_available': SoftwareUpdateKeyword,
    'admin_signup_alert': AdminPlatformSignupKeyword,
    'signup': PlatformSignupKeyword,
    'activation': PlatformSignupKeyword,
    'email_validation': EmailValidationKeyword,
    'account_activation': AccountActivationKeyword,
    'password_reset_validation': PasswordResetValidationKeyword,
    'user_credentials': UserCredentials,
    'identity_access_request': IdentityAccessRequestKeyword,
    'identity_access_authorized': TipKeyword,
    'identity_access_denied': TipKeyword,
    'signup_invite': TenantInviteKeyword
}


def mail_uses_smtp2(notification, mail_type):
    """
    Return True if emails of the given template type must be delivered via the

    :param notification: The notification configuration, either the tenant cache
    :param mail_type: The template type of the email being sent
    """
    return bool(notification.get('smtp2_enabled', False)) and \
        mail_type in notification.get('smtp2_template_types', [])


class Templating:
    def format_template(self, raw_template, data):
        keyword_converter = supported_template_types[data['type']](data)

        for kw in keyword_converter.keyword_list:
            if raw_template.count(kw):
                # if {SomeKeyword} matches, call keyword_converter.some_keyword function
                variable_content = getattr(keyword_converter, snake_case(kw[1:-1]))()
                variable_content = re.sub("{", "(", variable_content)
                variable_content = re.sub("}", ")", variable_content)
                raw_template = raw_template.replace(kw, variable_content)

        return raw_template.rstrip()


    def get_mail_subject_and_body(self, data):
        subject_template = ''
        body_template = ''

        if data['type'] == 'export_template':
            # this is currently the only template not used for mail notifications
            pass
        elif data['type'] in supported_template_types:
            subject_template = data['notification'].get(data['type'] + '_mail_title', '')
            body_template = data['notification'].get(data['type'] + '_mail_template', '')
        else:
            raise NotImplementedError('This data_type (%s) is not supported' % ['data.type'])

        if data['type'] in ['tip', 'tip_update']:
            subject_template = '{TipNum} - ' + subject_template

        subject = self.format_template(subject_template, data)
        body = self.format_template(body_template, data)

        if 'user' in data and data['user']['pgp_key_public']:
            try:
                body = PGPContext(data['user']['pgp_key_public']).encrypt_message(body)
            except Exception:
                # Security: if PGP encryption fails for ANY reason, drop the body.
                # Falling back to plaintext would defeat the recipient's PGP key.
                body = ""

        return subject, body
