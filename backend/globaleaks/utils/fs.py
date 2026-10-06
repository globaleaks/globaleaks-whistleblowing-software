import json
import os
import secrets

from globaleaks.rest import errors
from globaleaks.utils.log import log


def srm(absolutefpath, iterations_number=1):
    """
    Overwrite the file with all_zeros, all_ones, random patterns

    This feature is a legacy security measure known to has important
    drawbacks and to not be effective on all the situations as it
    depends on specific filesystems and storage devices.

    the effective solution on which the system does relies is encryption
    and this feature is maintained just as additional countermeasure
    and for educational and historical reasons.

    :param absolutefpath: the absolute path of the file to overwrite
    :param iterations_number: the number of overwrite operations
    """
    log.debug("Starting secure deletion of file %s", absolutefpath)

    def _overwrite(absolutefpath, pattern):
        count = 0
        length = os.path.getsize(absolutefpath)

        # 'r+b' (not 'wb+') so the file is not truncated on open: truncation
        # would release the original data blocks unoverwritten. Overwrite the
        # whole content, in pattern-sized chunks, up to the original size.
        with open(absolutefpath, 'r+b') as f:
            f.seek(0)
            while count < length:
                f.write(pattern)
                count += len(pattern)

    if not os.path.exists(absolutefpath):
        return

    try:
        # in the following loop, the file is open and closed on purpose, to trigger flush operations
        all_0 = b"\x00" * 4096  # 4kb of zeros
        all_1 = b"\xFF" * 4096  # 4kb of ones

        for iteration in range(iterations_number):
            random_pattern = secrets.token_bytes(4096)
            log.debug("Excecuting rewrite iteration (%d out of %d)",
                      iteration, iterations_number)

            _overwrite(absolutefpath, all_0)
            _overwrite(absolutefpath, all_1)
            _overwrite(absolutefpath, random_pattern)

    except Exception as excep:
        log.err("Unable to perform secure overwrite for file %s: %s",
                absolutefpath, excep)

    finally:
        try:
            os.remove(absolutefpath)
        except OSError as excep:
            log.err("Unable to perform unlink operation on file %s: %s",
                    absolutefpath, excep)

    log.debug("Performed deletion of file: %s", absolutefpath)


def directory_traversal_check(trusted_absolute_prefix, untrusted_path):
    """
    Ensure that ``untrusted_path`` is contained within ``trusted_absolute_prefix``.

    :param trusted_absolute_prefix: absolute path of the sandbox root
    :param untrusted_path: path derived (directly or indirectly) from user input
    :raises errors.DirectoryTraversalError: if ``untrusted_path`` escapes the sandbox
    """
    trusted_absolute_prefix = os.path.realpath(trusted_absolute_prefix)
    untrusted_path = os.path.realpath(untrusted_path)

    if os.path.commonpath([trusted_absolute_prefix, untrusted_path]) != trusted_absolute_prefix:
        log.err("Blocked file operation for: (prefix, attempted_path) : ('%s', '%s')",
                trusted_absolute_prefix, untrusted_path)
        raise errors.DirectoryTraversalError


def get_disk_space(path):
    statvfs = os.statvfs(path)
    free_bytes = statvfs.f_frsize * statvfs.f_bavail
    total_bytes = statvfs.f_frsize * statvfs.f_blocks
    return free_bytes, total_bytes


def read_file(p):
    try:
        with open(p, encoding='utf-8') as f:
            return f.read().rstrip("\n")
    except (OSError, UnicodeDecodeError):
        # OSError: missing/unreadable file. UnicodeDecodeError: invalid UTF-8 bytes.
        return ""


def read_json_file(p):
    try:
        return json.loads(read_file(p))
    except (ValueError, TypeError):
        # ValueError covers json.JSONDecodeError (its parent class).
        return {}


def get_storage_path(tid, kind, file_id=None, create=False, tenants_path=None):
    """
    Resolve a path inside a tenant's storage

    :param tid: The tenant ID
    :param kind: The storage directory
    :param file_id: An optional file ID
    :param create: Whether to create the storage directory
    :param tenants_path: An optional tenant root for backup snapshots
    :return: The validated storage path
    """
    from globaleaks.settings import Settings

    if isinstance(tid, bool) or not str(tid).isdigit() or int(tid) < 1:
        raise errors.DirectoryTraversalError
    if kind not in ('files', 'attachments', 'log'):
        raise errors.DirectoryTraversalError

    tenants_path = Settings.tenants_path if tenants_path is None else tenants_path
    tenant_root = os.path.join(tenants_path, str(int(tid)))
    if os.path.islink(tenant_root):
        raise errors.DirectoryTraversalError
    directory_traversal_check(tenants_path, tenant_root)
    root = os.path.join(tenant_root, kind)
    directory_traversal_check(tenant_root, root)
    path = root if file_id is None else os.path.join(root, file_id)
    if file_id is not None and (not file_id or os.path.basename(file_id) != file_id or file_id in ('.', '..')):
        raise errors.DirectoryTraversalError
    directory_traversal_check(root, path)
    if create:
        os.makedirs(tenant_root, mode=0o700, exist_ok=True)
        os.makedirs(root, mode=0o700, exist_ok=True)
    return path
