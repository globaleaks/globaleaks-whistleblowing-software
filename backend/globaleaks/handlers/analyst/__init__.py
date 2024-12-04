# -*- coding: utf-8 -*-
#
# Handlers dealing with analyst user functionalities
import base64
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy.sql.expression import func, and_, distinct

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.models.config import ConfigFactory
from globaleaks.orm import transact, db_get
from globaleaks.rest import requests
from globaleaks.utils.crypto import GCE


@transact
def get_stats(session, tid):
    """
    Transaction for retrieving analyst statistics

    :param session: An ORM session
    :param tid: A tenant ID
    """
    reports_count = session.query(func.count(models.InternalTip.id)) \
                           .filter(models.InternalTip.tid == tid).one()[0]

    num_tips_no_access = session.query(func.count(models.InternalTip.id)) \
                                .filter(models.InternalTip.tid == tid,
                                        models.InternalTip.access_count == 0).one()[0]

    num_tips_mobile = session.query(func.count(models.InternalTip.id)) \
                             .filter(models.InternalTip.tid == tid,
                                     models.InternalTip.mobile == True).one()[0]

    num_tips_tor = session.query(func.count(models.InternalTip.id)) \
                             .filter(models.InternalTip.tid == tid,
                                     models.InternalTip.tor == True).one()[0]

    num_subscribed_tips = session.query(func.count(models.InternalTip.id)) \
                                 .filter(models.InternalTip.tid == tid) \
                                 .join(models.InternalTipData,
                                       and_(models.InternalTipData.internaltip_id == models.InternalTip.id,
                                            models.InternalTipData.key == 'whistleblower_identity',
                                            models.InternalTipData.creation_date == models.InternalTip.creation_date)).one()[0]

    num_initially_anonymous_tips = session.query(func.count(models.InternalTip.id)) \
                                       .filter(models.InternalTip.tid == tid) \
                                       .join(models.InternalTipData,
                                             and_(models.InternalTipData.internaltip_id == models.InternalTip.id,
                                                  models.InternalTipData.key == 'whistleblower_identity',
                                                  models.InternalTipData.creation_date != models.InternalTip.creation_date)).one()[0]

    num_anonymous_tips = reports_count - num_subscribed_tips - num_initially_anonymous_tips

    return {
        "reports_count": reports_count,
        "reports_with_no_access": num_tips_no_access,
        "reports_anonymous": num_anonymous_tips,
        "reports_subscribed": num_subscribed_tips,
        "reports_initially_anonymous": num_initially_anonymous_tips,
        "reports_mobile": num_tips_mobile,
        "reports_tor": num_tips_tor
    }

@transact
def get_stats_fields(session, tid):
    tid_lang = ConfigFactory(session, tid).get_val('default_language')
    fields = session.query(models.Field).filter(
        models.Field.statistical == True,
        models.Field.tid == tid
    ).all()
    fields_dict = [{'id': x.id, 'label': x.label.get(tid_lang)} for x in fields]

    aux = ['internal_tip_id', 'internal_tip_status', 'internal_tip_creation_date','internal_tip_update_date',
           'internal_tip_expiration_date', 'internal_tip_receiver_count', 'last_access',
           'internal_tip_creation_date_month', 'internal_tip_creation_date_years', 'internal_tip_file_count',
           'internal_tip_comment_count'
           ]
    for i in aux:
        fields_dict.append(
            {
                'id': i,
                'label': i
            }
        )
    return fields_dict

def get_month_safe(date_value):
    if isinstance(date_value, datetime):
        return date_value.month
    return 0

def get_year_safe(date_value):
    if isinstance(date_value, datetime):
        return date_value.year
    return 0

def get_base_stats(session, internal_tip_id):
    internal_tip = session.query(models.InternalTip).filter(
        models.InternalTip.id == internal_tip_id
    ).one_or_none()
    is_fw_tip = session.query(models.InternalTipForwarding).filter(
        models.InternalTipForwarding.forwarding_internaltip_id == internal_tip_id
    ).one_or_none()
    if is_fw_tip is not None:
        sub = session.query(models.Subscriber).filter(
            models.Subscriber.tid == internal_tip.tid
        ).one_or_none()
    else:
        sub = None
    count_fw_tip = session.query(func.count(distinct(models.InternalTipForwarding.internaltip_id))).filter(
        models.InternalTipForwarding.internaltip_id == internal_tip_id
    ).scalar()
    count_comment = session.query(
        func.count(distinct(models.Comment.id))).filter(
        models.Comment.internaltip_id == internal_tip_id,
        models.Comment.visibility == models.EnumVisibility.public.value
    ).scalar()
    count_files = session.query(func.count(distinct(models.InternalFile.id))).filter(
        models.InternalFile.internaltip_id == internal_tip_id
    ).scalar()
    count_receivers = session.query(func.count(distinct(models.ReceiverTip.id))).filter(
        models.ReceiverTip.internaltip_id == internal_tip_id
    ).scalar()
    return {
        'internal_tip_id': is_fw_tip.internaltip_id if is_fw_tip is not None else internal_tip.id,
        'internal_tip_status': internal_tip.status,
        'internal_tip_creation_date': internal_tip.creation_date,
        'internal_tip_creation_date_month': get_month_safe(internal_tip.creation_date),
        'internal_tip_creation_date_years': get_year_safe(internal_tip.creation_date),
        'internal_tip_update_date': internal_tip.update_date,
        'internal_tip_expiration_date': internal_tip.expiration_date,
        'last_access': internal_tip.last_access,
        'internal_tip_file_count': count_files,
        'internal_tip_comment_count': count_comment,
        'internal_tip_receiver_count': count_receivers,
        'is_fw_tip': is_fw_tip is not None,
        'fw_id': internal_tip.id if is_fw_tip is not None else None,
        'fw_tip_count': count_fw_tip,
        'eo_name': sub.organization_name if sub is not None else None
    }

def transform_base_tip_into_statistical(base_tip: dict) -> list:
    base_list = []
    for k, v in base_tip.items():
        base_list.append(
            {
                'id': k,
                'label': k,
                'value': v
            }
        )
    return base_list


def parse_dates(request):
    date_to = datetime.strptime(request.get('date_to', datetime.now()), "%Y-%m-%d") + timedelta(days=1)
    date_from = datetime.strptime(request.get('date_from', date_to - timedelta(weeks=1)), "%Y-%m-%d")
    return date_to, date_from

def get_model_and_field(is_external_organization):
    if is_external_organization:
        return models.InternalTipForwarding, 'stat_data'
    return models.InternalTipAnswers, 'stat_answers'

def add_result_in_summary(results, summary):
    for group in results:
        for entry in group:
            entry_id = entry["id"]
            entry_value = entry["value"]
            if type(entry_value) in [str, int, float, bool]:
                summary[entry_id][entry_value] += 1
    return summary

@transact
def get_all_element(session, param_session, request):
    date_to, date_from = parse_dates(request)
    is_eo = request.get('is_eo', False)
    model, stat_field = get_model_and_field(is_eo)

    answers = session.query(getattr(model, stat_field), model.internaltip_id).filter(
        model.creation_date > date_from,
        model.creation_date <= date_to
    ).all()

    results = []

    user = db_get(session, models.User, models.User.id == param_session['user_id'])
    sts_prv_key = base64.b64decode(user.crypto_global_stat_prv_key)
    sts_key = GCE.asymmetric_decrypt(param_session['key_user_prv'], sts_prv_key)
    forwarding_enabled = ConfigFactory(session, 1).get_val('forwarding_enabled')
    for answer in answers:
        base_dict = get_base_stats(session, answer[1])
        if forwarding_enabled or (not forwarding_enabled and not base_dict.get('is_fw_tip')):
            row = transform_base_tip_into_statistical(base_dict)
            try:
                for k, v in json.loads(GCE.asymmetric_decrypt(sts_key, base64.b64decode(answer[0].encode())).decode()).items():
                    label = session.query(models.Field.label).filter(
                        models.Field.id == k,
                        models.Field.tid == param_session['tid']
                    ).one_or_none()
                    if label:
                        row.append(
                            {
                                'id': k,
                                'label':label[0][param_session['default_language']],
                                'value': v
                            }
                        )
            except Exception as e:
                logging.debug(e)
            finally:
                results.append(row)

    summary = defaultdict(Counter)
    summary = add_result_in_summary(results=results, summary=summary)
    summary = {k: dict(v) for k, v in summary.items()}

    return {
        "results": results,
        "summary": summary
    }



class Statistics(BaseHandler):
    """
    Handler for statistics fetch
    """
    check_roles = 'analyst'

    def get(self):
        return get_stats(self.session.tid)


class StatisticalInterest(BaseHandler):
    """
    Handler for statistics fetch
    """
    check_roles = 'analyst'

    def get(self):
        return get_stats_fields(self.session.tid)

    def post(self):
        request = self.validate_request(self.request.content.read(), requests.StatisticalInterestTable)
        parm_session = {
            'tid': self.session.tid,
            'key_user_prv': self.session.cc,
            'user_id': self.session.attrs.get('user_id'),
            'default_language': self.state.tenants.get(self.session.tid).cache.get('languages_enabled', ['en'])[0]
        }
        return get_all_element(parm_session, request)