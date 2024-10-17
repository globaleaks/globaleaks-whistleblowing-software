# -*- coding: utf-8 -*-
#
# Handlers dealing with analyst user functionalities
import base64
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy.sql.expression import func, and_

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
    return [{'id': x.id, 'label': x.label.get(tid_lang)} for x in fields]

@transact
def get_all_element(session, param_session, request):
    date_to = datetime.strptime(request.get('date_to', datetime.now()), "%Y-%m-%d") + timedelta(days=1)
    date_from = datetime.strptime(request.get('date_from', date_to - timedelta(weeks=1)), "%Y-%m-%d")
    pg_num = max(request.get('pg_num', 0), 0)
    pg_size = max(request.get('pg_size', 10), 1)
    offset = max((pg_num - 1) * pg_size, 0)
    is_oe = request.get('is_oe', False)
    model = models.InternalTipForwarding if is_oe else models.InternalTipAnswers
    stat_field = 'stat_data' if is_oe else 'stat_answers'

    total_count = session.query(model).filter(
        model.creation_date > date_from,
        model.creation_date <= date_to,
        getattr(model, stat_field) != '{}'
    ).count()

    answers = session.query( getattr(model, stat_field), model.internaltip_id).filter(
        model.creation_date > date_from,
        model.creation_date <= date_to,
        getattr(model, stat_field) != '{}'
    ).limit(pg_size).offset(offset).all()

    total_pages = (total_count + pg_size - 1) // pg_size

    results = []

    user = db_get(session, models.User, models.User.id == param_session['user_id'])
    sts_prv_key = base64.b64decode(user.crypto_global_stat_prv_key)
    sts_key = GCE.asymmetric_decrypt(param_session['key_user_prv'], sts_prv_key)
    for answer in answers:
        row = []
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
        results.append(row)

    summary = defaultdict(Counter)

    for group in results:
        for entry in group:
            entry_id = entry["id"]
            entry_value = entry["value"]
            summary[entry_id][entry_value] += 1
    summary = {k: dict(v) for k, v in summary.items()}

    return {
        "results": results,
        "summary": summary,
        "pagination":{
            "total_count": total_count,
            "total_pages": total_pages,
            "current_page": pg_num,
            "page_size": pg_size
        }
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