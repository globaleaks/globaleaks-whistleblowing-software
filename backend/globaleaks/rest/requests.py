# -*- coding: utf-8
#   Requests
#   ********
#
# This file contains the specification of all the requests that can be made by a
# GLClient to a GLBackend.
# These specifications may be used with rest.validateMessage() inside each of the API
# handler in order to verify if the request is correct.

import copy

from globaleaks import models
from globaleaks.models.config_desc import ConfigL10NFilters

alphanumeric_str_regexp = r'^[^<>\/.{}\[\]]*$'
phone_regexp = r'^[+]?[0-9]*$'
key_regexp = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$|^[a-z_]{0,100}$'
key_regexp_or_empty = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$|^[a-z_]{0,100}$|^$'
uuid_regexp = r'^([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$'
uuid_regexp_or_empty = r'^([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$|^$'
user_role_regexp = r'^(admin|analyst|custodian|receiver)$'
email_regexp = r'^(([\w+-\.]){0,100}[\w]{1,100}@([\w+-\.]){0,100}[\w]{1,100})$'
email_regexp_or_empty = r'^(([\w+-\.]){0,100}[\w]{1,100}@([\w+-\.]){0,100}[\w]{1,100})$|^$'
hostname_regexp = r'^[0-9a-z\-\.]+$'
hostname_regexp_or_empty = r'^[0-9a-z\-\.]+$|^$'
subdomain_regexp = r'^[0-9a-z\-]+$'
subdomain_regexp_or_empty = r'^[0-9a-z\-]+$|^$'
url_regexp = r'^https?:\/\/([0-9a-z\-]+)\.([^\n])*$'
url_regexp_or_empty = r'^https?:\/\/([0-9a-z\-]+)\.([^\n])*$|^$'
tip_operation_regexp = r'^(postpone|set)$'
short_text_regexp = r'^.{1,255}$'
short_text_regexp_or_empty = r'^.{0,255}$'
languages_list_regexp = r'^([a-zA-Z-]+)?(,\s*[a-zA-Z-]+)*$'

field_instance_regexp = (r'^('
                         'instance|'
                         'reference|'
                         'template)$')

field_type_regexp = (r'^('
                     'inputbox|'
                     'textarea|'
                     'selectbox|'
                     'multichoice|'
                     'checkbox|'
                     'tos|'
                     'fileupload|'
                     'number|'
                     'email|'
                     'date|'
                     'daterange|'
                     'voice|'
                     'fieldgroup)$')

field_attr_type_regexp = (r'^('
                          'int|'
                          'bool|'
                          'unicode|'
                          'localized)$')

identityaccessreply_regexp = (r'^('
                              'pending|'
                              'authorized|'
                              'denied)$')


def get_multilang_request_format(request_format, localized_strings):
    ret = copy.deepcopy(request_format)

    for ls in localized_strings:
        ret[ls] = dict

    return ret


DateType = r'(.*)'

# ContentType = r'(application|audio|text|video|image)'
# via stackoverflow:
# /^(application|audio|example|image|message|model|multipart|text|video)\/[a-zA-Z0-9]+([+.-][a-zA-z0-9]+)*$/
ContentType = r'(.*)'

AdminTenantDesc = {
    'name': str,
    'mode': str,
    'active': bool,
    'subdomain': subdomain_regexp_or_empty
}

FileDesc = {
    'name': str,
    'description': str,
    'size': int,
    'type': ContentType,
    'date': DateType,
    'visibility': str
}


AuthDesc = {
    'tid': int,
    'username': str,
    'password': str,
    'authcode': str
}

ReceiptAuthDesc = {
    'receipt': str
}

TokenAuthDesc = {
    'authtoken': str
}

TokenAnswerDesc = {
    'answer': int
}

SubmissionDesc = {
    'context_id': uuid_regexp,
    'receivers': [uuid_regexp],
    'identity_provided': bool,
    'answers': dict,
    'score': int
}

AdminUserDesc = {
    'username': str,
    'name': str,
    'description': str,
    'public_name': str,
    'role': user_role_regexp,
    'password_change_needed': bool,
    'enabled': bool,
    'mail_address': email_regexp,
    'pgp_key_remove': bool,
    'pgp_key_fingerprint': str,
    'pgp_key_expiration': str,
    'pgp_key_public': str,
    'language': str,
    'notification': bool,
    'can_edit_general_settings': bool,
    'can_delete_submission': bool,
    'can_postpone_expiration': bool,
    'can_grant_access_to_reports': bool,
    'can_redact_information': bool,
    'can_mask_information': bool,
    'can_reopen_reports': bool,
    'can_transfer_access_to_reports': bool,
    'forcefully_selected': bool
}

UserUserDesc = {
    'username': str,
    'name': str,
    'description': str,
    'public_name': str,
    'role': user_role_regexp,
    'password_change_needed': bool,
    'mail_address': email_regexp,
    'pgp_key_remove': bool,
    'pgp_key_fingerprint': str,
    'pgp_key_expiration': str,
    'pgp_key_public': str,
    'language': str,
    'notification': bool
}

CommentDesc = {
    'content': str,
    'visibility': str
}

OpsDesc = {
    'operation': str,
    'args': dict,
}

TipOpsDesc = {
    'operation': tip_operation_regexp,
    'args': dict
}

AdditionalQuestionnaireAnswers = {
    'cmd': str,
    'answers': dict
}

WhisleblowerIdentityAnswers = {
    'identity_field_id': uuid_regexp,
    'identity_field_answers': dict
}

AdminNodeDesc = {
    'name': str,
    'description': str,
    'presentation': str,
    'footer': str,
    'footer_privacy_policy': str,
    'footer_whistleblowing_policy': str,
    'disclaimer_text': str,
    'rootdomain': hostname_regexp_or_empty,
    'whistleblowing_question': str,
    'whistleblowing_button': str,
    'languages_enabled': [str],
    'languages_supported': list,
    'timezone': int,
    'default_language': str,
    'default_questionnaire': str,
    'maximum_filesize': int,
    'allow_indexing': bool,
    'disable_privacy_badge': bool,
    'disable_submissions': bool,
    'simplified_login': bool,
    'enable_scoring_system': bool,
    'enable_signup': bool,
    'mode': str,
    'signup_tos1_enable': bool,
    'signup_tos1_title': str,
    'signup_tos1_text': str,
    'signup_tos1_checkbox_label': str,
    'signup_tos2_enable': bool,
    'signup_tos2_title': str,
    'signup_tos2_text': str,
    'signup_tos2_checkbox_label': str,
    'enable_custom_privacy_badge': bool,
    'custom_privacy_badge_text': str,
    'header_title_homepage': str,
    'contexts_clarification': str,
    'show_contexts_in_alphabetical_order': bool,
    'threshold_free_disk_megabytes_high': int,
    'threshold_free_disk_megabytes_low': int,
    'threshold_free_disk_percentage_high': int,
    'threshold_free_disk_percentage_low': int,
    'password_change_period': int,
    'unread_reminder_time': int,
    'enable_admin_exception_notification': bool,
    'enable_developers_exception_notification': bool,
    'log_level': str,
    'log_accesses_of_internal_users': bool,
    'two_factor': bool,
    'encryption': bool,
    'adminonly': bool,
    'custom_support_url': url_regexp_or_empty,
    'pgp': bool,
    'user_privacy_policy_text': str,
    'user_privacy_policy_url': str
}

AdminNetworkDesc = {
    'https_admin': bool,
    'https_analyst': bool,
    'https_custodian': bool,
    'https_whistleblower': bool,
    'https_receiver': bool,
    'reachable_via_web': bool,
    'anonymize_outgoing_connections': bool,
    'ip_filter_admin_enable': bool,
    'ip_filter_admin': str,
    'ip_filter_analyst_enable': bool,
    'ip_filter_analyst': str,
    'ip_filter_custodian_enable': bool,
    'ip_filter_custodian': str,
    'ip_filter_receiver_enable': bool,
    'ip_filter_receiver': str
}

AdminNotificationDesc = {
    'smtp_server': str,
    'smtp_port': int,
    'smtp_security': str,  # 'TLS' or 'SSL' only
    'smtp_authentication': bool,
    'smtp_username': str,
    'smtp_password': str,
    'smtp_source_email': email_regexp,
    'enable_admin_notification_emails': bool,
    'enable_analyst_notification_emails': bool,
    'enable_custodian_notification_emails': bool,
    'enable_receiver_notification_emails': bool,
    'tip_expiration_threshold': int
}

AdminNotificationDesc.update({k: str for k in ConfigL10NFilters['notification']})

AdminFieldOptionDesc = {
    'id': uuid_regexp_or_empty,
    'label': str,
    'hint1': str,
    'hint2': str,
    'block_submission': bool,
    'order': int,
    'score_type': str,
    'score_points': int,
    'trigger_receiver': list
}

AdminFieldOptionDescRaw = get_multilang_request_format(AdminFieldOptionDesc, models.FieldOption.localized_keys)

AdminFieldAttrDesc = {
    'id': uuid_regexp_or_empty,
    'name': str,
    'type': field_attr_type_regexp,
    'value': list
}

AdminFieldAttrDescRaw = get_multilang_request_format(AdminFieldAttrDesc, models.FieldAttr.localized_keys)

AdminFieldDesc = {
    'id': key_regexp_or_empty,
    'instance': field_instance_regexp,
    'template_id': key_regexp_or_empty,
    'template_override_id': key_regexp_or_empty,
    'step_id': uuid_regexp_or_empty,
    'fieldgroup_id': key_regexp_or_empty,
    'label': str,
    'description': str,
    'hint': str,
    'placeholder': str,
    'multi_entry': bool,
    'x': int,
    'y': int,
    'width': int,
    'required': bool,
    'type': field_type_regexp,
    'attrs': dict,
    'options': [AdminFieldOptionDesc],
    'children': list,
    'triggered_by_score': int,
    'triggered_by_options': list
}

AdminFieldDescRaw = get_multilang_request_format(AdminFieldDesc, models.Field.localized_keys)
AdminFieldDescRaw['options'] = [AdminFieldOptionDescRaw]
# AdminFieldDescRaw['attrs']; FIXME: we still miss a way for validating a hierarchy where
#                                    we have a variable dictionary like the attrs dictionary.

AdminStepDesc = {
    'id': uuid_regexp_or_empty,
    'label': str,
    'description': str,
    'children': [AdminFieldDesc],
    'questionnaire_id': key_regexp_or_empty,
    'order': int,
    'triggered_by_score': int,
    'triggered_by_options': list
}

AdminStepDescRaw = get_multilang_request_format(AdminStepDesc, models.Step.localized_keys)
AdminStepDescRaw['children'] = [AdminFieldDescRaw]

AdminQuestionnaireDesc = {
    'id': key_regexp_or_empty,
    'name': str,
    'steps': list
}

AdminQuestionnaireDescRaw = get_multilang_request_format(AdminQuestionnaireDesc, models.Questionnaire.localized_keys)
AdminQuestionnaireDescRaw['steps'] = list

AdminContextDesc = {
    'id': uuid_regexp_or_empty,
    'name': str,
    'hidden': bool,
    'description': str,
    'maximum_selectable_receivers': int,
    'tip_timetolive': int,
    'tip_reminder': int,
    'receivers': [uuid_regexp],
    'select_all_receivers': bool,
    'allow_recipients_selection': bool,
    'score_threshold_medium': int,
    'score_threshold_high': int,
    'order': int,
    'show_steps_navigation_interface': bool,
    'show_receivers_in_alphabetical_order': bool,
    'questionnaire_id': key_regexp_or_empty,
    'additional_questionnaire_id': key_regexp_or_empty
}

AdminTLSCertFilesConfigDesc = {
    'key': str,
    'chain': str,
    'cert': str,
}

AdminTLSCfgFileResourceDesc = {
    'name': str,
    'content': str,
}

AdminCSRDesc = {
    'country': r'^[A-Za-z]{2}$|^$',
    'province': short_text_regexp_or_empty,
    'city': short_text_regexp_or_empty,
    'company': short_text_regexp_or_empty,
    'email': email_regexp_or_empty
}

AdminRedirectDesc = {
    'path1': str,
    'path2': str
}

NodeDesc = {
    'adminonly': bool,
    'contexts_clarification': str,
    'custom_privacy_badge_text': str,
    'default_language': str,
    'default_questionnaire': str,
    'disable_privacy_badge': bool,
    'disable_submissions': bool,
    'disclaimer_text': str,
    'enable_custom_privacy_badge': bool,
    'enable_scoring_system': bool,
    'enable_signup': bool,
    'footer': str,
    'footer_privacy_policy': str,
    'footer_whistleblowing_policy': str,
    'header_title_homepage': str,
    'https_whistleblower': bool,
    'languages_enabled': [str],
    'languages_supported': list,
    'maximum_filesize': int,
    'name': str,
    'presentation': str,
    'rootdomain': hostname_regexp_or_empty,
    'show_contexts_in_alphabetical_order': bool,
    'signup_tos1_checkbox_label': str,
    'signup_tos1_enable': bool,
    'signup_tos1_text': str,
    'signup_tos1_title': str,
    'signup_tos2_checkbox_label': str,
    'signup_tos2_enable': bool,
    'signup_tos2_text': str,
    'signup_tos2_title': str,
    'simplified_login': bool,
    'start_time': DateType,
    'whistleblowing_button': str,
    'whistleblowing_question': str,
    'user_privacy_policy_text': str,
    'user_privacy_policy_url': str
}

ReceiverIdentityAccessRequestDesc = {
    'request_motivation': str
}

CustodianIdentityAccessRequestDesc = {
    'reply': identityaccessreply_regexp,
    'reply_motivation': str
}

ReceiverDesc = {
    'name': str,
    'description': str,
    'id': uuid_regexp,
}

ContextDesc = {
    'id': uuid_regexp,
    'name': str,
    'hidden': bool,
    'description': str,
    'order': int,
    'receivers': [uuid_regexp],
    'select_all_receivers': bool,
    'tip_timetolive': int,
    'tip_reminder': int,
    'allow_recipients_selection': bool,
    'maximum_selectable_receivers': int,
    'show_receivers_in_alphabetical_order': bool,
    'picture': bool
}

ContextCollectionDesc = [ContextDesc]

PublicResourcesDesc = {
    'node': NodeDesc,
    'contexts': [ContextDesc],
    'receivers': [ReceiverDesc]
}

InternalTipDesc = {
    'id': uuid_regexp,
    'new': bool,
    'context_id': uuid_regexp,
    'wb_steps': list,
    'receivers': [uuid_regexp],
    'files': [uuid_regexp],
    'creation_date': DateType,
    'expiration_date': DateType,
    'identity_provided': bool
}

WizardDesc = {
    'node_language': str,
    'node_name': str,
    'admin_username': str,
    'admin_name': str,
    'admin_password': str,
    'admin_mail_address': str,
    'admin_escrow': bool,
    'receiver_username': str,
    'receiver_name': str,
    'receiver_password': str,
    'receiver_mail_address': str,
    'profile': r'^(default)$',
    'skip_admin_account_creation': bool,
    'skip_recipient_account_creation': bool,
    'enable_developers_exception_notification': bool
}

SignupDesc = {
    'subdomain': subdomain_regexp,
    'name': alphanumeric_str_regexp,
    'surname': alphanumeric_str_regexp,
    'role': alphanumeric_str_regexp,
    'phone': phone_regexp,
    'email': email_regexp,
    'organization_name': str,
    'organization_tax_code': alphanumeric_str_regexp,
    'organization_vat_code': alphanumeric_str_regexp,
    'organization_location': str,
    'tos1': bool,
    'tos2': bool
}

SubmitAccreditation = {
    'organization_name': str,
    'organization_email': email_regexp,
    'organization_institutional_site': str,
    'admin_name': alphanumeric_str_regexp,
    'admin_surname': alphanumeric_str_regexp,
    'admin_email': email_regexp,
    'name': alphanumeric_str_regexp,
    'surname': alphanumeric_str_regexp,
    'recipient_fiscal_code': alphanumeric_str_regexp,
    'email': email_regexp,
    'tos1': bool,
    'tos2': bool
}

SupportDesc = {
    'mail_address': email_regexp,
    'url': url_regexp_or_empty,
    'text': str
}

PasswordReset1Desc = {
    'username': str
}

PasswordReset2Desc = {
    'reset_token': str,
    'recovery_key': str,
    'auth_code': str
}

SiteSettingsDesc = {
    'disclaimer_text': str,
    'header_title_homepage': str,
    'footer': str,
    'footer_privacy_policy': str,
    'footer_whistleblowing_policy': str,
    'name': str,
    'presentation': str,
}

QuestionnaireDuplicationDesc = {
    'questionnaire_id': str,
    'new_name': str
}

SubmissionStatusDesc = {
    'label': str,
    'order': int
}

SubmissionSubStatusDesc = {
    'label': str,
    'order': int,
    'tip_timetolive': int
}

SessionUpdateDesc = {
    'token': str
}
