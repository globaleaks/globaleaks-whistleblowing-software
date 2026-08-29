import json

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import db_del, transact, tw


@transact
def get(session, tid, lang):
    """
    Transaction for retrieving the texts customization of a tenant

    :param session: An ORM session
    :param tid: A tenant ID
    :param lang: The language to be used for the lookup
    :return: The sequence of customizations
    """
    texts = session.query(models.CustomTexts).filter(models.CustomTexts.tid == tid,
                                                     models.CustomTexts.lang == lang).one_or_none()
    return texts.texts if texts is not None else {}


@transact
def update(session, tid, lang, request):
    """
    Transaction for updating the texts customizations of a tenant

    :param session: An ORM session
    :param tid: A tentant ID
    :param lang: The language to be used for the update
    :param request: The customization data
    """
    session.merge(models.CustomTexts({'tid': tid, 'lang': lang, 'texts': request}))


class AdminL10NHandler(BaseHandler):
    check_roles = 'admin'
    require_permission = 'can_manage_settings'
    invalidate_cache = True

    def get(self, lang):
        return get(self.request.tid, lang)

    def put(self, lang):
        return update(self.request.tid, lang, json.loads(self.request.content.read()))

    def delete(self, lang):
        return tw(db_del,
                  models.CustomTexts,
                  (models.CustomTexts.tid == self.request.tid, models.CustomTexts.lang == lang))
