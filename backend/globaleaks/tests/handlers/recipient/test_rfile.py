from twisted.internet.defer import inlineCallbacks

from globaleaks import models
from globaleaks.handlers.recipient import rtip
from globaleaks.handlers.whistleblower import wbtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.models.config import db_set_config_variable
from globaleaks.orm import transact
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.utils.utility import datetime_now
import io
import zipfile

file_content = b'Hello World'


class TestWBFileWorkFlow(helpers.TestHandlerWithPopulatedDB):
    _handler = None

    @inlineCallbacks
    def test_get(self):
        yield self.perform_full_submission_actions()

        self._handler = rtip.ReceiverFileUpload
        rtips_desc = yield self.get_rtips()
        for rtip_desc in rtips_desc:
            attachment = self.get_dummy_attachment(content=file_content)
            handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'], attachment=attachment)
            yield handler.post(rtip_desc['id'])

        yield Delivery().run()

        self._handler = wbtip.ReceiverFileDownload
        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            rfiles_desc = yield self.get_rfiles(wbtip_desc['id'])
            for rfile_desc in rfiles_desc:
                handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
                yield handler.get(rfile_desc['id'])
                body = handler.request.getResponseBody()
                if body.startswith(b'PK\x03\x04'):
                    z = zipfile.ZipFile(io.BytesIO(body))
                    content = None
                    for info in z.infolist():
                        if info.filename.upper() != 'README.TXT':
                            content = z.read(info)
                            break
                    if content is None and z.infolist():
                        content = z.read(z.infolist()[0])
                else:
                    content = body
                self.assertEqual(content, file_content)

        self._handler = rtip.ReceiverFileDownload
        rtips_desc = yield self.get_rtips()
        deleted_rfiles_ids = []
        for rtip_desc in rtips_desc:
            for rfile_desc in rtip_desc['rfiles']:
                if rfile_desc['id'] not in deleted_rfiles_ids:
                    handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
                    yield handler.delete(rfile_desc['id'])
                    deleted_rfiles_ids.append(rfile_desc['id'])

        # check that the files are effectively gone from the db
        rtips_desc = yield self.get_rtips()
        for rtip_desc in rtips_desc:
            self.assertEqual(len(rtip_desc['rfiles']), 0)


class TestReceiverFileDownloadAntivirus(helpers.TestHandlerWithPopulatedDB):
    _handler = rtip.ReceiverFileDownload

    @transact
    def set_antivirus_enabled(self, session, enabled):
        db_set_config_variable(session, 1, 'antivirus_enabled', enabled)

    @transact
    def set_rfile_antivirus_state(self, session, file_id, state):
        db_set_config_variable(session, 1, 'antivirus_enabled', True)
        rfile = session.query(models.ReceiverFile).filter_by(id=file_id).one()
        rfile.state = state
        rfile.verification_date = datetime_now()

    @inlineCallbacks
    def create_receiver_file(self):
        yield self.perform_full_submission_actions()

        rtip_desc = (yield self.get_rtips())[0]
        attachment = self.get_dummy_attachment(content=file_content)
        handler = self.request(role='receiver',
                               user_id=rtip_desc['receiver_id'],
                               attachment=attachment,
                               handler_cls=rtip.ReceiverFileUpload)
        yield handler.post(rtip_desc['id'])
        yield Delivery().run()

        rtip_desc = (yield self.get_rtips())[0]
        return rtip_desc['receiver_id'], rtip_desc['rfiles'][0]['id']


class TestWhistleblowerReceiverFileDownloadAntivirus(helpers.TestHandlerWithPopulatedDB):
    _handler = wbtip.ReceiverFileDownload

    @transact
    def set_rfile_antivirus_state(self, session, file_id, state):
        db_set_config_variable(session, 1, 'antivirus_enabled', True)
        rfile = session.query(models.ReceiverFile).filter_by(id=file_id).one()
        rfile.state = state
        rfile.verification_date = datetime_now()

    @inlineCallbacks
    def create_receiver_file(self):
        yield self.perform_full_submission_actions()

        rtip_desc = (yield self.get_rtips())[0]
        attachment = self.get_dummy_attachment(content=file_content)
        handler = self.request(role='receiver',
                               user_id=rtip_desc['receiver_id'],
                               attachment=attachment,
                               handler_cls=rtip.ReceiverFileUpload)
        yield handler.post(rtip_desc['id'])
        yield Delivery().run()

        rfile_id = (yield self.get_rfiles(rtip_desc['id']))[0]['id']
        return rtip_desc['id'], rfile_id

    @inlineCallbacks
    def test_get_allows_infected_file(self):
        wbtip_id, rfile_id = yield self.create_receiver_file()

        yield self.set_rfile_antivirus_state(rfile_id, models.EnumStateFile.infected.name)

        handler = self.request(role='whistleblower', user_id=wbtip_id)
        yield handler.get(rfile_id)
        self.assertNotEqual(handler.request.getResponseBody(), '')

    @inlineCallbacks
    def test_get_allows_pending_file(self):
        wbtip_id, rfile_id = yield self.create_receiver_file()

        yield self.set_rfile_antivirus_state(rfile_id, models.EnumStateFile.pending.name)

        handler = self.request(role='whistleblower', user_id=wbtip_id)
        yield handler.get(rfile_id)
        self.assertNotEqual(handler.request.getResponseBody(), '')
