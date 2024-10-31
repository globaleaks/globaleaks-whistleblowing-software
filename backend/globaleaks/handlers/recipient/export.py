# -*- coding: utf-8 -*-
#
# API handling export of submissions
import os
from io import BytesIO
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread

from globaleaks import models
from globaleaks.handlers.admin.context import admin_serialize_context
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.public import db_get_submission_statuses
from globaleaks.handlers.recipient.rtip import db_update_submission_status, redact_report
from globaleaks.handlers.whistleblower.submission import decrypt_tip
from globaleaks.handlers.user import user_serialize_user
from globaleaks.models import serializers
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.settings import Settings
from globaleaks.utils.crypto import Base64Encoder, GCE
from globaleaks.utils.fs import directory_traversal_check
from globaleaks.utils.securetempfile import SecureTemporaryFile
from globaleaks.utils.templating import Templating
from globaleaks.utils.utility import datetime_now, datetime_null, msdos_encode
from globaleaks.utils.zipstream import ZipStream


try:

    import fpdf

    class REPORTPDF(fpdf.FPDF):
        report_default_font = "Inter-Regular.ttf"
        report_fallback_fonts = ["GoNotoKurrent-Regular.ttf"]
        report_direction = 'ltr'
        report_line_height = 3
        report_margin = 10

        def __init__(self, *args, **kwargs):
            super(REPORTPDF, self).__init__(*args, **kwargs)

            fontspath = os.path.join(Settings.client_path, "fonts")
            self.add_font(family="Inter-Regular.ttf", style='', fname=os.path.join(fontspath, "Inter-Regular.ttf"))
            self.add_font(family="GoNotoKurrent-Regular.ttf", style='', fname=os.path.join(fontspath, "GoNotoKurrent-Regular.ttf"))

            self.set_font(self.report_default_font, "", 11)
            self.set_fallback_fonts(self.report_fallback_fonts)

            self.set_auto_page_break(auto=True, margin=15)

            self.set_author("GLOBALEAKS")
            self.set_creator("GLOBALEAKS")
            self.set_lang("EN")

            self.set_right_margin(self.report_margin)
            self.set_left_margin(self.report_margin)

            self.set_text_shaping(use_shaping_engine=False, direction="ltr")

        def header(self):
            self.cell(80)
            self.set_font("courier", "", 9)
            self.set_text_shaping(use_shaping_engine=False, direction="ltr")
            self.cell(30, 10, self.title, align="C")
            self.set_text_shaping(use_shaping_engine=False, direction=self.report_direction)
            self.set_font(self.report_default_font, "", 11)
            self.ln(20)

        def footer(self):
            self.set_y(-15)
            self.set_font("courier", "", 9)
            self.set_text_shaping(use_shaping_engine=False, direction="ltr")
            self.cell(0, 10, f"{self.page_no()}/{{nb}}", align="C")
            self.set_text_shaping(use_shaping_engine=False, direction=self.report_direction)
            self.set_font(self.report_default_font, "", 11)

except ImportError:
    REPORTPDF = None
    pass


def serialize_rtip_export(session, user, itip, rtip, context, language):
    rtip_dict = serializers.serialize_rtip(session, itip, rtip, language)

    return {
        'type': 'export_template',
        'node': db_admin_serialize_node(session, user.tid, language),
        'notification': db_get_notification(session, user.tid, language),
        'tip': rtip_dict,
        'crypto_tip_prv_key': Base64Encoder.decode(rtip.crypto_tip_prv_key),
        'deprecated_crypto_files_prv_key': Base64Encoder.decode(rtip.deprecated_crypto_files_prv_key),
        'user': user_serialize_user(session, user, language),
        'context': admin_serialize_context(session, context, language),
        'submission_statuses': db_get_submission_statuses(session, user.tid, language)
    }


@transact
def get_tip_export(session, tid, user_id, itip_id, language):
    user, context, itip, rtip = session.query(models.User, models.Context, models.InternalTip, models.ReceiverTip) \
                                       .filter(models.User.id == user_id,
                                               models.User.tid == tid,
                                               models.ReceiverTip.receiver_id == models.User.id,
                                               models.InternalTip.id == models.ReceiverTip.internaltip_id,
                                               models.InternalTip.id == itip_id,
                                               models.Context.id == models.InternalTip.context_id).one_or_none()

    if not user:
        raise errors.ResourceNotFound

    rtip.last_access = datetime_now()
    if rtip.access_date == datetime_null():
        rtip.access_date = rtip.last_access

    if itip.status == 'new':
        db_update_submission_status(session, tid, user_id, itip, 'opened', None)

    return user.pgp_key_public, serialize_rtip_export(session, user, itip, rtip, context, language)


def create_pdf_report(input_text, data):
    pdf = REPORTPDF(orientation='P', unit='mm', format='A4')

    pdf.set_title("REPORT " + str(data['tip']['progressive']) + " (" + str(data['tip']['id']) + ") [CONFIDENTIAL]")

    pdf.add_page()

    # Process each line
    for line in input_text.split('\n'):
        if any('\u0590' <= char <= '\u06FF' for char in line):  # Check for characters in Hebrew or Arabic blocks
            if pdf.report_direction == 'ltr':
                pdf.report_direction = 'rtl'
                pdf.set_text_shaping(use_shaping_engine=False, direction=pdf.report_direction)
        else:
            if pdf.report_direction == 'rtl':
                pdf.report_direction = 'ltr'
                pdf.set_text_shaping(use_shaping_engine=False, direction=pdf.report_direction)

        pdf.multi_cell(0, pdf.report_line_height, line.strip(), align='L')
        pdf.ln()

    return BytesIO(pdf.output())


@inlineCallbacks
def prepare_tip_export(user_session, tip_export):
    tip_export['tip']['rfiles'] = list(filter(lambda x: x['visibility'] != 'personal', tip_export['tip']['rfiles']))

    files = tip_export['tip']['wbfiles'] + tip_export['tip']['rfiles']

    if tip_export['crypto_tip_prv_key']:
        tip_export['tip'] = yield deferToThread(decrypt_tip, user_session.cc, tip_export['crypto_tip_prv_key'], tip_export['tip'])

        tip_export['tip'] = yield redact_report(user_session.user_id, tip_export['tip'], True)

        for file_dict in tip_export['tip']['wbfiles']:
            if tip_export['deprecated_crypto_files_prv_key']:
                files_prv_key = GCE.asymmetric_decrypt(user_session.cc, tip_export['deprecated_crypto_files_prv_key'])
            else:
                files_prv_key = GCE.asymmetric_decrypt(user_session.cc, tip_export['crypto_tip_prv_key'])

            filelocation = os.path.join(Settings.attachments_path, file_dict['id'])
            if not os.path.exists(filelocation):
                filelocation = os.path.join(Settings.attachments_path, file_dict['ifile_id'])

            directory_traversal_check(Settings.attachments_path, filelocation)
            file_dict['key'] = files_prv_key
            file_dict['path'] = filelocation
            del filelocation

        for file_dict in tip_export['tip']['rfiles']:
            tip_prv_key = GCE.asymmetric_decrypt(user_session.cc, tip_export['crypto_tip_prv_key'])
            filelocation = os.path.join(Settings.attachments_path, file_dict['id'])
            directory_traversal_check(Settings.attachments_path, filelocation)
            file_dict['key'] = tip_prv_key
            file_dict['path'] = filelocation
            del filelocation

    for file_dict in tip_export['tip'].pop('wbfiles'):
        file_dict['name'] = 'files/' + file_dict['name']
        if file_dict.get('status', '') == 'encrypted':
            file_dict['name'] += '.pgp'

    for file_dict in tip_export['tip'].pop('rfiles'):
        file_dict['name'] = 'files_attached_from_recipients/' + file_dict['name']

    tip_export['comments'] = tip_export['tip']['comments']

    export_template = Templating().format_template(tip_export['notification']['export_template'], tip_export).encode()
    export_template = msdos_encode(export_template.decode()).encode()

    if REPORTPDF:
        files.append({'fo': create_pdf_report(export_template.decode(), tip_export), 'name': 'report.pdf'})
    else:
        files.append({'fo': BytesIO(export_template), 'name': 'report.txt'})

    return files


class ExportHandler(BaseHandler):
    check_roles = 'receiver'
    handler_exec_time_threshold = 3600

    @inlineCallbacks
    def get(self, itip_id):
        pgp_key, tip_export = yield get_tip_export(self.request.tid,
                                                   self.session.user_id,
                                                   itip_id,
                                                   self.request.language)

        filename = "report-" + str(tip_export["tip"]["progressive"]) + ".zip"

        files = yield prepare_tip_export(self.session, tip_export)

        zipstream = ZipStream(files)

        stf = SecureTemporaryFile(self.state.settings.tmp_path)

        with stf.open('w') as f:
            for x in zipstream:
                f.write(x)
            f.finalize_write()

        with stf.open('r') as f:
            yield self.write_file_as_download(filename, f, pgp_key)
