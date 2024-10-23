# -*- coding: utf-8 -*-
#
# This filte contains routines dealing with texts templates and variables replacement used
# mainly in mail notifications.
import collections
import copy
import re

from datetime import datetime, timedelta

from globaleaks import __version__
from globaleaks.rest import errors
from globaleaks.utils.pgp import PGPContext
from globaleaks.utils.sock import isIPAddress
from globaleaks.utils.utility import \
    datetime_to_pretty_str, \
    datetime_to_day_str, \
    bytes_to_pretty_str, \
    ISO8601_to_day_str

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
    '{AnomalyDetailActivities}',
    '{ActivityAlarmLevel}',
    '{ActivityDump}',
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

platform_signup_keywords = [
    '{RecipientName}',
    '{ActivationUrl}',
    '{ExpirationDate}',
    '{Name}',
    '{Surname}',
    '{Email}',
    '{Language}',
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


class Keyword(object):
    keyword_list = []
    data_keys = []

    def __init__(self, data):
        for k in self.data_keys:
            if k not in data:
                raise errors.InternalServerError('Missing key \'%s\' while resolving template \'%s\'' % (k, type(self).__name__))

        self.data = data


class NodeKeyword(Keyword):
    keyword_list = node_keywords
    data_keys = ['node', 'notification']

    def NodeName(self):
        return self.data['node']['name']

    def TorSite(self):
        if self.data['node']['onionservice']:
            return 'http://' + self.data['node']['onionservice']

        return '[UNDEFINED]'

    def HTTPSSite(self):
        if self.data['node']['hostname']:
            if isIPAddress(self.data['node']['hostname']):
                return 'http://' + self.data['node']['hostname']
            else:
                return 'https://' + self.data['node']['hostname']

        return '[UNDEFINED]'

    def Site(self):
        if self.data['node']['hostname']:
            return self.HTTPSSite()

        elif self.data['node']['onionservice']:
            return self.TorSite()

        return ''

    def UrlPath(self):
        if self.data['node'].get('is_eo'):
            return f"/t/{self.data['node'].get('eo_uuid')}/"
        return '/'

    def Url(self):
        return self.Site() + self.UrlPath()

    def TorUrl(self):
        return self.TorSite() + self.UrlPath()

    def HTTPSUrl(self):
        return self.HTTPSSite() + self.UrlPath()

    def DocumentationUrl(self):
        return 'https://docs.globaleaks.org'

    def LoginUrl(self):
        return self.Site() + '/#/login'


class UserKeyword(Keyword):
    keyword_list = user_keywords
    data_keys = ['user']

    def RecipientName(self):
        return self.data['user']['name']

    def Username(self):
        return '%s' % self.data['user']['username']


class UserNodeKeyword(NodeKeyword, UserKeyword):
    keyword_list = NodeKeyword.keyword_list + UserKeyword.keyword_list
    data_keys = NodeKeyword.data_keys + UserKeyword.data_keys


class TipKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + tip_keywords
    data_keys = UserNodeKeyword.data_keys + ['tip']

    def dump_field_entry(self, output, field, entry, indent_n):
        field_type = field['type']

        if field_type == 'checkbox':
            for k, v in entry.items():
                for option in field['options']:
                    if k == option.get('id', '') and v is True:
                        output += indent(indent_n) + option['label'] + '\n'
        elif field_type in ['multichoice', 'selectbox']:
            for option in field['options']:
                if entry.get('value', '') == option['id']:
                    output += indent(indent_n) + option['label'] + '\n'
        elif field_type == 'date':
            date = entry.get('value')
            if date is not None:
                output += indent(indent_n) + ISO8601_to_day_str(date) + '\n'
        elif field_type == 'daterange':
            daterange = entry.get('value')
            if daterange is not None:
                daterange = daterange.split(':')
                output += indent(indent_n) + datetime_to_day_str(datetime.fromtimestamp(int(daterange[0])/1000)) + '\n'
                output += indent(indent_n) + datetime_to_day_str(datetime.fromtimestamp(int(daterange[1])/1000)) + '\n'
        elif field_type == 'tos':
            answer = '☑' if entry.get('value', '') is True else '☐'
            output += indent(indent_n) + answer + '\n'
        elif field_type == 'fieldgroup':
            output = self.dump_fields(output, field['children'], entry, indent_n)
        else:
            output += indent_text(entry.get('value', ''), indent_n) + '\n'

        return output + '\n'

    def dump_fields(self, output, fields, answers, indent_n):
        rows = {}
        for f in fields:
            y = f['y']
            if y not in rows:
                rows[y] = []
            rows[y].append(f)

        rows = collections.OrderedDict(sorted(rows.items()))

        for r in rows:
            rows[r] = sorted(rows[r], key=lambda k: k['x'])

        for _, row in rows.items():
            for field in row:
                if field['id'] not in answers or \
                   field['type'] == 'fileupload' or \
                   field['template_id'] == 'whistleblower_identity':
                    continue

                if field['id'] in answers:
                    output += indent(indent_n) + field['label'] + '\n'
                    entries = answers[field['id']]
                    if len(entries) == 1:
                        output = self.dump_field_entry(output, field, entries[0], indent_n + 1)
                    else:
                        i = 1
                        for entry in entries:
                            output += indent(indent_n) + '#' + str(i) + '\n'
                            output = self.dump_field_entry(output, field, entry, indent_n + 2)
                            i += 1

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

    def TipID(self):
        return self.data['tip']['id']

    def UrlPath(self):
        return '/#/reports/' + self.data['tip']['id']

    def TipNum(self):
        return str(self.data['tip']['progressive'])

    def TipLabel(self):
        return self.data['tip']['label']

    def TipStatus(self):
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

    def EventTime(self):
        return datetime_to_pretty_str(self.data['tip']['creation_date'])

    def SubmissionDate(self):
        return self.EventTime()

    def QuestionnaireAnswers(self):
        return self.dump_questionnaire_answers(self.data['tip']['questionnaires'][0]['steps'], self.data['tip']['questionnaires'][0]['answers'])

    def Comments(self):
        comments = self.data.get('comments', [])
        comments = self.dump_comments(comments)
        return 'Comments\n' + comments + '\n' if comments else ''


class ExportMessageKeyword(TipKeyword):
    keyword_list = TipKeyword.keyword_list + export_comment_keywords
    data_keys = TipKeyword.data_keys + ['comment']

    def Author(self):
        return 'Recipient' if self.data['comment']['author_id'] else 'Whistleblower'

    def Content(self):
        return self.data['comment']['content']

    def EventTime(self):
        return datetime_to_pretty_str(self.data['comment']['creation_date'])


class ExpirationSummaryKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + expiration_summary_keywords
    data_keys = UserNodeKeyword.data_keys + ['expiring_submission_count', 'earliest_expiration_date']

    def ExpiringSubmissionCount(self):
        return str(self.data['expiring_submission_count'])

    def EarliestExpirationDate(self):
        return datetime_to_pretty_str(self.data['earliest_expiration_date'])

    def UrlPath(self):
        return '/#/recipient/reports'


class AdminPGPAlertKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + admin_pgp_alert_keywords
    data_keys = UserNodeKeyword.data_keys + ['users']

    def PGPKeyInfoList(self):
        ret = ''
        for r in self.data['users']:
            fingerprint = r['pgp_key_fingerprint']
            key = fingerprint[:7] if fingerprint is not None else ''

            ret += '\t%s, %s (%s)\n' % (r['name'],
                                        key,
                                        datetime_to_day_str(r['pgp_key_expiration']))
        return ret


class PGPAlertKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + user_pgp_alert_keywords

    def PGPKeyInfo(self):
        fingerprint = self.data['user']['pgp_key_fingerprint']
        key = fingerprint[:7] if fingerprint is not None else ''

        return '\t0x%s (%s)' % (key, datetime_to_day_str(self.data['user']['pgp_key_expiration']))


class AnomalyKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + admin_anomaly_keywords
    data_keys = UserNodeKeyword.data_keys + ['alert']

    def AnomalyDetailDisk(self):
        # This happens all the time anomalies are present but disk is ok
        if self.data['alert']['alarm_levels']['disk_space'] == 0:
            return ''

        if self.data['alert']['alarm_levels']['disk_space'] == 1:
            return self.data['notification']['admin_anomaly_disk_low']
        else:
            return self.data['notification']['admin_anomaly_disk_high']

    def AnomalyDetailActivities(self):
        # This happens all the time there is not anomalous traffic
        if self.data['alert']['alarm_levels']['activity'] == 0:
            return ''

        return self.data['notification']['admin_anomaly_activities']

    def ActivityAlarmLevel(self):
        return '%s' % self.data['alert']['alarm_levels']['activity']

    def ActivityDump(self):
        retstr = ''

        for event, count in self.data['alert']['event_matrix'].items():
            if not count:
                continue
            retstr = '%s%s%d\n%s' % (event, (25 - len(event)) * ' ', count, retstr)

        return retstr

    def FreeMemory(self):
        return '%s' % bytes_to_pretty_str(self.data['alert']['measured_freespace'])

    def TotalMemory(self):
        return '%s' % bytes_to_pretty_str(self.data['alert']['measured_totalspace'])


class CertificateExprKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + https_expr_keywords
    data_keys = UserNodeKeyword.data_keys + ['expiration_date']

    def ExpirationDate(self):
        return datetime_to_pretty_str(self.data['expiration_date'])

    def UrlPath(self):
        return '/#/admin/network'


class SoftwareUpdateKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + software_update_keywords
    data_keys = UserNodeKeyword.data_keys + ['latest_version']

    def LatestVersion(self):
        return '%s' % self.data['latest_version']

    def InstalledVersion(self):
        return '%s' % __version__

    def ChangeLogUrl(self):
        return 'https://github.com/globaleaks/whistleblowing-software/blob/main/CHANGELOG'

    def UpdateGuideUrl(self):
        return 'https://docs.globaleaks.org/en/main/user/admin/UpgradeGuide.html'


class UserCredentials(Keyword):
    keyword_list = user_credentials_keywords
    data_keys = ['role', 'username', 'password']

    def Role(self):
        return '%s' % self.data['role']

    def Username(self):
        return '%s' % self.data['username']

    def Password(self):
        return '%s' % self.data['password']


class PlatformSignupKeyword(NodeKeyword):
    keyword_list = NodeKeyword.keyword_list + platform_signup_keywords
    data_keys = NodeKeyword.data_keys + ['signup']

    def TorSite(self):
        return 'http://' + self.data['signup']['subdomain'] + '.' + self.data['node']['onionservice']

    def HTTPSSite(self):
        if self.data['node'].get('is_eo'):
            return f"https://{self.data['node']['hostname']}"
        return 'https://' + self.data['signup']['subdomain'] + '.' + self.data['node']['rootdomain']

    def Site(self):
        if self.data['node']['hostname']:
            return self.HTTPSSite()

        elif self.data['node']['onionservice']:
            return self.TorSite()

        return ''

    def RecipientName(self):
        return self.data['signup']['name'] + ' ' + self.data['signup']['surname']

    def ActivationUrl(self):
        if self.data['node']['hostname']:
            site = 'https://' + self.data['node']['hostname']
            if self.data['node'].get('is_eo'):
                site = f"{site}/t/{self.data['node'].get('eo_uuid')}"
        elif self.data['node']['onionservice']:
            site = 'http://' + self.data['node']['onionservice']
        else:
            site = ''

        return site + '/#/activation?token=' + self.data['signup']['activation_token']

    def LoginUrl(self):
        site = self.Site()
        if self.data['node'].get('is_eo'):
            site = f"{site}/t/{self.data['node'].get('eo_uuid')}"
        return f"{site}/#/login"

    def ExpirationDate(self):
        date = self.data['signup']['registration_date'] + timedelta(30)
        return datetime_to_pretty_str(date)

    def Name(self):
        return self.data['signup']['name'] + ' ' + self.data['signup']['surname']

    def Email(self):
        return self.data['signup']['email']

    def Language(self):
        return self.data['signup']['language']

    def AdminCredentials(self):
        if not self.data['password_admin']:
            return ''

        data = {
            'type': 'user_credentials',
            'role': 'admin',
            'username': 'admin',
            'password': self.data['password_admin']
        }

        return Templating().format_template(self.data['notification']['user_credentials'], data) + "\n"

    def RecipientCredentials(self):
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
    def RecipientName(self):
        return self.data['user']['name']


class EmailValidationKeyword(UserNodeKeyword):
    keyword_list = NodeKeyword.keyword_list + email_validation_keywords
    data_keys = NodeKeyword.data_keys + \
        ['new_email_address', 'validation_token']

    def NewEmailAddress(self):
        return self.data['new_email_address']

    def UrlPath(self):
        return '/api/user/validate/email/' + self.data['validation_token']


class AccountActivationKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + account_activation_keywords

    def UrlPath(self):
        return '/#/password/reset' + '?token=' + self.data['reset_token']

    def AccountRecoveryKeyInstructions(self):
        if not self.data['node']['encryption']:
            return ''

        data = {'type': 'null'}

        return Templating().format_template(self.data['notification']['account_recovery_key_instructions'], data) + "\n"


class PasswordResetValidationKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list

    data_keys = UserNodeKeyword.data_keys + ['reset_token']

    def UrlPath(self):
        return '/#/password/reset?token=' + self.data['reset_token']


class IdentityAccessRequestKeyword(UserNodeKeyword):
    keyword_list = UserNodeKeyword.keyword_list + identity_access_request_keywords
    data_keys = UserNodeKeyword.data_keys + ['iar', 'tip', 'user']

    def TipNum(self):
        return str(self.data['tip']['progressive'])

    def UrlPath(self):
        return '/#/custodian/requests/'


supported_template_types = {
    'null': Keyword,
    'tip': TipKeyword,
    'tip_access': UserNodeKeyword,
    'tip_reminder': UserNodeKeyword,
    'tip_update': TipKeyword,
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
    'identity_access_denied': TipKeyword
}


class Templating(object):
    def format_template(self, raw_template, data):
        keyword_converter = supported_template_types[data['type']](data)

        for kw in keyword_converter.keyword_list:
            if raw_template.count(kw):
                # if {SomeKeyword} matches, call keyword_converter.SomeKeyword function
                variable_content = getattr(keyword_converter, kw[1:-1])()
                variable_content = re.sub("{", "(", variable_content)
                variable_content = re.sub("}", ")", variable_content)
                raw_template = raw_template.replace(kw, variable_content)

        raw_template = raw_template.rstrip()

        return raw_template

    def get_mail_subject_and_body(self, data):
        subject_template = ''
        body_template = ''

        if data['type'] == 'export_template':
            # this is currently the only template not used for mail notifications
            pass
        elif data['type'] in supported_template_types:
            subject_template = data['notification'][data['type'] + '_mail_title']
            body_template = data['notification'][data['type'] + '_mail_template']
        else:
            raise NotImplementedError('This data_type (%s) is not supported' % ['data.type'])

        if data['type'] in ['tip', 'tip_update']:
            subject_template = '{TipNum} - ' + subject_template

        subject = self.format_template(subject_template, data)
        body = self.format_template(body_template, data)

        if 'user' in data and data['user']['pgp_key_public']:
            try:
                body = PGPContext(data['user']['pgp_key_public']).encrypt_message(body)
            except:
                body = ""

        return subject, body
