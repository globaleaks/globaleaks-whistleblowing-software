import io
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
        length = len(pattern)

        with open(absolutefpath, 'wb+') as f:
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
        with io.open(p, 'r', encoding='utf-8') as f:
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
