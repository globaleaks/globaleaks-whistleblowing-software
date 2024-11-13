# -*- coding: utf-8 -*-
from twisted.internet.defer import inlineCallbacks

from globaleaks.handlers.recipient import rtip
from globaleaks.handlers.whistleblower import wbtip
from globaleaks.jobs.delivery import Delivery
from globaleaks.tests import helpers

attachment = b'hello world'


class TestWBFileWorkFlow(helpers.TestHandlerWithPopulatedDB):
    _handler = None

    @inlineCallbacks
    def test_get(self):
        # yield self.perform_full_submission_actions()

        self._handler = rtip.ReceiverFileUpload
        rtips_desc = yield self.get_rtips()
        for rtip_desc in rtips_desc:
            handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'], attached_file=attachment)
            yield handler.post(rtip_desc['id'])

        yield Delivery().run()
        
        self._handler = wbtip.ReceiverFileDownload
        wbtips_desc = yield self.get_wbtips()
        for wbtip_desc in wbtips_desc:
            rfiles_desc = yield self.get_rfiles(wbtip_desc['id'])
            for rfile_desc in rfiles_desc:
                handler = self.request(role='whistleblower', user_id=wbtip_desc['id'])
                yield handler.get(rfile_desc['id'])
                self.assertEqual(handler.request.getResponseBody(), attachment)

        self._handler = rtip.ReceiverFileDownload
        rtips_desc = yield self.get_rtips()
        deleted_rfiles_ids = []
        for rtip_desc in rtips_desc:
            for rfile_desc in rtip_desc['rfiles']:
                if rfile_desc['id'] in deleted_rfiles_ids:
                    continue

                handler = self.request(role='receiver', user_id=rtip_desc['receiver_id'])
                yield handler.delete(rfile_desc['id'])

                deleted_rfiles_ids.append(rfile_desc['id'])

        # check that the files are effectively gone from the db
        rtips_desc = yield self.get_rtips()
        for rtip_desc in rtips_desc:
            self.assertEqual(len(rtip_desc['rfiles']), 0)
