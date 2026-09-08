"""
Migration 69 -> 70: reconcile the divergences of the ANAC fork.

At 69 the databases of the stable branch and the ones of the ANAC fork share
the same schema, but the fork developed a few of its features differently from
the way the new-stable branch consolidated them. The migration expresses the
data of the fork in the conventions of new-stable, feature by feature:

- Statistical reports: the fork names the statistical keys of a tenant
  global_stat_pub_key (the fork) or crypto_global_stat_pub_key /
  crypto_global_stat_prv_key (migration 69); new-stable names them
  crypto_stat_pub_key / crypto_stat_prv_key.
- OIDC authentication: the fork configures the client as idp_clientId,
  new-stable as idp_client_id.
- Signup accreditation: the fork stored the state of a subscriber by name for
  a while (e.g. "requested") before settling on the numeric value.
- Report answers: the fork stores the answers as raw text, the stable branch
  and new-stable JSON-encoded (a ciphertext string, or the object of the
  answers of a report created before the encryption).
- Visibility of the comments and of the evidences: the fork holds two values
  of its own beside the ones of new-stable, and each is expressed by the value
  of new-stable that reaches the same readers.

Whatever the fork added and new-stable did not retain (the identity of the
users on the identity provider, the antivirus state of the files, the
affiliation and the externality of the tenants, the questionnaire of a
forward, content_transmission, the configuration variables of its own) is not
carried over: the columns are left behind by the models, the configuration
variables by migration 71.
"""
import json

from sqlalchemy import text

from globaleaks.db.migrations.update import MigrationBase
from globaleaks.models import Model
from globaleaks.models.enums import EnumSubscriberStatus
from globaleaks.models.properties import *
from globaleaks.utils.utility import datetime_now, datetime_null


class InternalTipAnswersV69(Model):
    __tablename__ = 'internaltipanswers'

    internaltip_id = Column(UnicodeText(36), primary_key=True)
    questionnaire_hash = Column(UnicodeText(64), primary_key=True)
    creation_date = Column(DateTime, default=datetime_now, nullable=False)
    answers = Column(UnicodeText, default='{}', nullable=False)
    stat_answers = Column(UnicodeText, default='{}', nullable=False)


class InternalTipTransmissionV69(Model):
    __tablename__ = 'internaltip_forwarding'

    internaltip_id = Column(UnicodeText(36), nullable=False, primary_key=True)
    forwarding_internaltip_id = Column(UnicodeText(36), nullable=False, primary_key=True)


def normalize_answers(text):
    """
    Read a value stored by the fork as raw text: the text of an object is the
    object itself, anything else is a ciphertext kept as a string.
    """
    return json.loads(text) if text.startswith('{') else text


# The visibility of a comment or of an evidence, as the ANAC fork wrote it,
# expressed by the value of new-stable that reaches the same readers: what the
# fork exchanged with the hosting body ('eo') was read by the recipients of the
# report and never by the whistleblower, as the internal visibility is; what it
# addressed to the whistleblower was read by the whistleblower, as the public
# visibility is.
FORK_VISIBILITY = {
    3: 1,  # eo -> internal
    4: 0   # whistleblower -> public
}


class MigrationScript(MigrationBase):
    renamed_config = {
        'global_stat_pub_key': 'crypto_stat_pub_key',
        'crypto_global_stat_pub_key': 'crypto_stat_pub_key',
        'crypto_global_stat_prv_key': 'crypto_stat_prv_key',
        'idp_clientId': 'idp_client_id'
    }

    converted_attrs = {
        'Subscriber': {
            'state': lambda o: EnumSubscriberStatus[o.state].value if isinstance(o.state, str) else o.state
        },
        'InternalTipAnswers': {
            'answers': lambda o: normalize_answers(o.answers),
            'stat_answers': lambda o: normalize_answers(o.stat_answers)
        }
    }

    def prologue(self):
        """
        Express in the values of new-stable the visibility the fork wrote

        The conversion is performed on the database being read and not on the
        objects, because the value the fork wrote is outside the ones the
        models declare and no object carrying it can be read at all.
        """
        for table in ['comment', 'receiverfile']:
            for old, new in FORK_VISIBILITY.items():
                self.session_old.execute(text(f'UPDATE {table} SET visibility = :new WHERE visibility = :old'),
                                         {'new': new, 'old': old})

        self.session_old.commit()
