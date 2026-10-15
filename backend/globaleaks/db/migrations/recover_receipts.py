# Recovery of the whistleblower receipts invalidated by 5.0.96-5.0.99
#
# At every start those releases replaced with random values the server-hashed
# receipts of the tenants also holding longer hashes. Replaying the audit log,
# this marks the reports that were server-hashed at the first start of such a
# release, so that the login can recover them from the receipt.
import re
from datetime import datetime

from globaleaks import models
from globaleaks.utils.crypto import generateRandomKey
from globaleaks.utils.log import log


def version(v):
    return tuple(int(x) for x in re.findall(r'\d+', v or '0.0.0')[:3])


def db_mark_invalidated_receipts(session, original_version):
    from globaleaks.handlers.auth import RECOVERY_PREFIX

    if version(original_version) > (5, 0, 99):
        return

    entries = session.query(models.AuditLog.date, models.AuditLog.type, models.AuditLog.tid,
                            models.AuditLog.object_id, models.AuditLog.user_id, models.AuditLog.data) \
                     .filter(models.AuditLog.type.in_(['version_update', 'whistleblower_new_report',
                                                       'whistleblower_login', 'delete_report', 'reset_reports'])) \
                     .order_by(models.AuditLog.date).all()

    updates = [(e.date, version((e.data or {}).get('from')), version((e.data or {}).get('to')))
               for e in entries if e.type == 'version_update']
    initial = updates[0][1] if updates else version(original_version)

    def since(low, high=(9999,)):
        if low <= initial <= high:
            return datetime.min
        return next((date for date, _, to in updates if low <= to <= high), None)

    boot = since((5, 0, 96), (5, 0, 99))
    if boot is None:
        return

    # Reports created up to 5.0.43 are server-hashed; up to 5.0.93 the receipt
    # change requested by the access of an operator was server-hashed too.
    key_adoption, client_change = since((5, 0, 44)), since((5, 0, 94))

    live = {id: (tid, date, len(h)) for id, tid, date, h in
            session.query(models.InternalTip.id, models.InternalTip.tid,
                          models.InternalTip.creation_date, models.InternalTip.receipt_hash)}

    # (date, kind, tid, id) with kind 0: creation, 1: receipt change, 2: deletion
    events = [(date, 0, tid, id) for id, (tid, date, _) in live.items()]
    known, operator_reports, verified = set(live), set(), set()
    for e in entries:
        if e.type == 'whistleblower_new_report' and e.object_id:
            if e.user_id:
                operator_reports.add(e.object_id)
            if e.object_id not in known:
                known.add(e.object_id)
                events.append((e.date, 0, e.tid, e.object_id))
        elif e.type == 'whistleblower_login':
            if e.date > boot:
                verified.add(e.object_id)
            elif key_adoption <= e.date < client_change and (e.user_id or e.object_id in operator_reports):
                events.append((e.date, 1, e.tid, e.object_id))
        elif e.type == 'delete_report' and e.object_id:
            if e.object_id not in known:
                # The creation entry expired with the audit log retention
                known.add(e.object_id)
                events.append((datetime.min, 0, e.tid, e.object_id))
            events.append((e.date, 2, e.tid, e.object_id))
        elif e.type == 'reset_reports':
            events.append((e.date, 2, e.tid, None))

    # A report is created server-hashed while its tenant holds another one;
    # hashes longer than 64 characters never made a tenant server-hashed.
    alive, legacy = {}, {}
    for date, kind, tid, id in sorted(events, key=lambda e: e[:2]):
        if date >= boot:
            break

        a, l = alive.setdefault(tid, set()), legacy.setdefault(tid, set())
        if kind == 0:
            a.add(id)
            if live.get(id, (0, 0, 0))[2] <= 64 and (date < key_adoption or l):
                l.add(id)
        elif kind == 1 and id in a:
            l.add(id)
        elif kind == 2:
            for r in [id] if id else list(a):
                a.discard(r)
                l.discard(r)

    for itip in session.query(models.InternalTip) \
                       .filter(models.InternalTip.id.in_(set().union(*legacy.values()) - verified)):
        if len(itip.receipt_hash) != 64:
            continue

        if not itip.crypto_prv_key:
            log.err('Unrecoverable receipt of unencrypted report: tid=%d id=%s', itip.tid, itip.id)
            continue

        log.err('Marking receipt for recovery: tid=%d id=%s', itip.tid, itip.id)
        # Shorter than 64 characters, the mark makes the tenant request the receipt
        itip.receipt_hash = RECOVERY_PREFIX + generateRandomKey()[:32]
