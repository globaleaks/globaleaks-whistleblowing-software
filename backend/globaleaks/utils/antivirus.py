import csv
from datetime import datetime, timedelta, timezone
from io import StringIO

import pyclamd

from twisted.internet import defer, threads

from globaleaks.models import EnumStateFile
from globaleaks.state import State
from globaleaks.utils.sock import parse_endpoint
from globaleaks.utils.log import log

ANTIVIRUS_RECHECK_DAYS = 90


def needs_antivirus_recheck(state, verification_date):
    """A file must be (re)scanned if it is still pending or if its last
    verification is older than ANTIVIRUS_RECHECK_DAYS."""
    if state == EnumStateFile.pending.name:
        return True

    if verification_date and verification_date.tzinfo is None:
        verification_date = verification_date.replace(tzinfo=timezone.utc)

    cutoff = datetime.now(timezone.utc) - timedelta(days=ANTIVIRUS_RECHECK_DAYS)

    return not verification_date or verification_date < cutoff


def prepare_file_download(file_obj, antivirus_enabled):
    if antivirus_enabled and needs_antivirus_recheck(file_obj.state, file_obj.verification_date):
        file_obj.state = EnumStateFile.pending.name
        return True

    return False


def enqueue_antivirus_scan(file_id, tip_prv_key):
    if not tip_prv_key:
        return

    if file_id in State.antivirus_file_ids:
        return

    State.antivirus_files.append((file_id, tip_prv_key))
    State.antivirus_file_ids.add(file_id)


def get_av_result(state):
    if state == EnumStateFile.infected.name:
        return 'UNSAFE'

    if state == EnumStateFile.pending.name:
        return 'PENDING'

    return 'SAFE'


def csv_sanitize_cell(value):
    """
    Neutralize spreadsheet formula injection: a cell whose text starts with
    """
    value = '' if value is None else str(value)
    if value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value


def serialize_files_metadata_csv(files):
    """
    Render a metadata.csv manifest from a list of file descriptor dicts,
    """
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(['Filename', 'Type', 'Size', 'Antivirus result'])

    for f in files:
        writer.writerow([csv_sanitize_cell(f.get('name', '')),
                         csv_sanitize_cell(f.get('type', '')),
                         f.get('size', ''),
                         csv_sanitize_cell(f.get('av_result', ''))])

    return buf.getvalue().encode()


def enqueue_tip_files_for_rescan(tip, tip_prv_key):
    """Queue for scanning every tip file that is still pending or whose last
    scan is older than ANTIVIRUS_RECHECK_DAYS, when the report is accessed."""
    if not tip_prv_key:
        return

    for file_obj in tip.get('wbfiles', []) + tip.get('rfiles', []):
        state = (file_obj.get('status') or '').lower()
        if needs_antivirus_recheck(state, file_obj.get('verification_date')):
            # For wbfiles the scannable, on-disk file is the InternalFile
            # (ifile_id); rfiles are addressed directly by their own id.
            enqueue_antivirus_scan(file_obj.get('ifile_id') or file_obj.get('id'), tip_prv_key)


def get_configured_clamd_connection():
    clamd_ip = 'localhost'
    clamd_port = 3310

    try:
        tenant = State.tenants.get(1)
        tenant_cache = getattr(tenant, 'cache', None)

        if tenant_cache is not None:
            clamd_ip = (getattr(tenant_cache, 'antivirus_clamd_ip', clamd_ip) or clamd_ip).strip()
            clamd_port = getattr(tenant_cache, 'antivirus_clamd_port', clamd_port) or clamd_port
    except (AttributeError, TypeError):
        # A value of the wrong type in the configuration leaves the defaults
        pass

    return clamd_ip, clamd_port


def get_clamd_endpoint(clamd_ip=None, clamd_port=None):
    if clamd_ip is None or clamd_port is None:
        configured_ip, configured_port = get_configured_clamd_connection()
        clamd_ip = configured_ip if clamd_ip is None else clamd_ip
        clamd_port = configured_port if clamd_port in [None, 0] else clamd_port

    return f"tcp://{clamd_ip}:{clamd_port}"


class FileAnalysis:
    def __init__(self, endpoint=None):
        if endpoint is None:
            endpoint = get_clamd_endpoint()
        self._endpoint = parse_endpoint(endpoint)
        self._scan_error_logged = False

    def _scan_file_blocking(self, file_obj) -> str:
        try:
            if self._endpoint['type'] != 'tcp':
                return 'error'

            cd = pyclamd.ClamdNetworkSocket(self._endpoint['host'], self._endpoint['port'])
            result = cd.scan_stream(file_obj)
            return 'unsafe' if result else 'safe'
        except Exception as e:
            if not self._scan_error_logged:
                log.err("ClamAV scan failed: %s", e)
                self._scan_error_logged = True
            return 'error'

    def scan_file(self, file_obj) -> defer.Deferred:
        return threads.deferToThread(self._scan_file_blocking, file_obj)
