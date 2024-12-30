import argparse
import atexit
import errno
import os
import re
import stat
import sys
import subprocess
import uuid
import threading
from tempfile import mkdtemp
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import ChaCha20

# Import fusepy as fuse when installed with pip
import importlib
fuse = importlib.import_module('fuse' if importlib.util.find_spec('fuse') else 'fusepy')

CHUNK_SIZE = 4096

UUID4_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.IGNORECASE)

def is_valid_uuid4(filename):
    """
    Validates if the given filename follows the UUIDv4 format.

    :param filename: The name of the file.
    :return: True if the filename is a valid UUIDv4, otherwise False.
    """
    return bool(UUID4_PATTERN.match(filename))

def is_mount_point(path):
    """
    Checks if the given path is a mount point.

    A mount point is a directory where a filesystem is attached. This function checks
    if the provided path is currently being used as a mount point by querying the
    system's mount information.

    :param path: The directory path to check if it is a mount point.
    :return: True if the given path is a mount point, otherwise False.
    :raises Exception: If there is an error while running the 'mount' command or parsing the result.
    """
    result = subprocess.run(['mount'], capture_output=True, text=True)
    return any(os.path.abspath(path) in line for line in result.stdout.splitlines())

def unmount_if_mounted(path):
    """
    Checks if the given path is a mount point and attempts to unmount it.

    :param path: The path to check and unmount if it is a mount point.
    """
    if is_mount_point(path):
        subprocess.run(['fusermount', '-u', path])

class EphemeralFile:
    def __init__(self, filesdir, filename=None):
        """
        Initializes an ephemeral file with ChaCha20 encryption.
        Creates a new random file path and generates a unique encryption key and nonce.

        :param filesdir: The directory where the ephemeral file will be stored.
        :param filenames: Optional filename. If not provided, a UUID4 is used.
        """
        filename = filename or str(uuid.uuid4())  # If filenames is None, generate a random UUID as a string
        self.filepath = os.path.join(filesdir, filename)
        self.cipher = Cipher(ChaCha20(os.urandom(32), uuid.UUID(filename).bytes[:16]), mode=None)
        self.enc = self.cipher.encryptor()
        self.dec = self.cipher.decryptor()

        self.fd = None

    def __getattribute__(self, name):
        """
        Intercepts attribute access for the `EphemeralFile` class.

        If the attribute being accessed is 'size', it returns the size of the file
        by checking the file's attributes using os.stat. For all other attributes,
        it defers to the default behavior of `__getattribute__`, allowing normal
        attribute access.

        :param name: The name of the attribute being accessed.
        :return: The value of the requested attribute. If 'size' is requested,
                 the size of the file is returned. Otherwise, the default
                 behavior for attribute access is used.
        """
        if name == "size":
            try:
                return os.stat(self.filepath).st_size
            except:
                return 0

        # For everything else, defer to the default behavior
        return super().__getattribute__(name)

    def open(self, flags, mode=0o660):
        """
        Opens the ephemeral file for reading or writing.

        :param mode: 'w' for writing, 'r' for reading.
        :return: The file object.
        """
        self.fd = os.open(self.filepath, os.O_RDWR | os.O_CREAT | os.O_APPEND, mode)
        os.chmod(self.filepath, mode)
        return self

    def write(self, data):
        """
        Writes encrypted data to the file.

        :param data: Data to write to the file, can be a string or bytes.
        """
        os.write(self.fd, self.enc.update(data))

    def read(self, size=None):
        """
        Reads data from the current position in the file.

        :param size: The number of bytes to read. If None, reads until the end of the file.
        :return: The decrypted data read from the file.
        """
        data = b""
        bytes_read = 0

        while True:
            # Determine how much to read in this chunk
            chunk_size = min(CHUNK_SIZE, size - bytes_read) if size is not None else CHUNK_SIZE

            chunk = os.read(self.fd, chunk_size)
            if not chunk:  # End of file
                break

            data += self.dec.update(chunk)
            bytes_read += len(chunk)

            if size is not None and bytes_read >= size:
                break

        return data

    def seek(self, offset):
        """
        Sets the position for the next read operation.

        :param offset: The offset to seek to.
        """
        position = 0
        self.dec = self.cipher.decryptor()
        self.enc = self.cipher.encryptor()
        os.lseek(self.fd, 0, os.SEEK_SET)
        discard_size = offset - position
        while discard_size > 0:
            to_read = min(CHUNK_SIZE, discard_size)
            data = self.dec.update(os.read(self.fd, to_read))
            data = self.enc.update(data)
            discard_size -= to_read

    def tell(self):
        """
        Returns the current position in the file.

        :return: The current position in the file.
        """
        return os.lseek(self.fd, 0, os.SEEK_CUR)

    def close(self):
        """
        Closes the file descriptor.
        """
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        """
        Allows the use of the file in a 'with' statement.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Ensures the file is closed when exiting a 'with' statement.
        """
        self.close()

    def __del__(self):
        """
        Ensures the file is cleaned up by closing it and removing the file.
        """
        self.close()
        try:
            os.unlink(self.filepath)
        except FileNotFoundError:
            pass

class EphemeralOperations(fuse.Operations):
    use_ns = True
    def __init__(self, storage_directory=None):
        """
        Initializes the operations for the ephemeral filesystem.

        :param storage_directory: The directory to store the files. Defaults to a temporary directory.
        """
        self.storage_directory = storage_directory if storage_directory is not None else mkdtemp()
        self.files = {}  # Track open files and their secure temporary file handlers
        self.mutex = threading.Lock()

    def get_file(self, path):
        file = self.files.get(path)
        if file is None:
            raise fuse.FuseOSError(errno.ENOENT)
        return file

    def getattr(self, path, fh=None):
        """
        Retrieves file or directory attributes.

        :param path: The file or directory path.
        :param fh: File handle (not used here).
        :return: A dictionary of file attributes.
        """
        with self.mutex:
            if path == '/':
                return {'st_mode': (stat.S_IFDIR | 0o750), 'st_nlink': 2}

            file = self.get_file(path)

            file_stat = os.stat(file.filepath)

            st = {key: getattr(file_stat, key) for key in dir(file_stat) if not key.startswith('__')}

            st['st_mode'] |= stat.S_IFDIR if stat.S_ISDIR(file_stat.st_mode) else 0
            st['st_mode'] |= stat.S_IFREG if stat.S_ISREG(file_stat.st_mode) else 0
            st['st_mode'] |= stat.S_IFLNK if stat.S_ISLNK(file_stat.st_mode) else 0

            return st

    def readdir(self, path, fh=None):
        """
        Lists the contents of a directory.

        :param path: The directory path.
        :param fh: File handle (not used here).
        :return: A list of directory contents.
        """
        with self.mutex:
            return ['.', '..'] + [os.path.basename(f) for f in self.files]

    def create(self, path, mode):
        """
        Creates a new file.

        :param path: The path where the file will be created.
        :param mode: The mode in which the file will be opened.
        :return: The file descriptor.
        """
        filename = os.path.basename(path)
        if not is_valid_uuid4(filename):
            raise fuse.FuseOSError(errno.ENOENT)

        with self.mutex:
            file = EphemeralFile(self.storage_directory, filename)
            file.open('w', mode)
            self.files[path] = file
            return file.fd

    def open(self, path, flags):
        """
        Opens an existing file.

        :param path: The file path.
        :param flags: The flags with which the file is opened.
        :return: The file descriptor.
        """
        with self.mutex:
            file = self.get_file(path)
            file.open('w' if (flags & os.O_RDWR or flags & os.O_WRONLY) else 'r')
            return file.fd

    def read(self, path, size, offset, fh=None):
        """
        Reads data from the file at a given offset.

        :param path: The file path.
        :param size: The number of bytes to read.
        :param offset: The offset from which to start reading.
        :param fh: File handle (not used here).
        :return: The data read from the file.
        """
        with self.mutex:
            file = self.get_file(path)
            file.seek(offset)
            return file.read(size)

    def write(self, path, data, offset, fh=None):
        """
        Writes data to the file at a given offset.

        :param path: The file path.
        :param data: The data to write.
        :param offset: The offset to start writing from.
        :param fh: File handle (not used here).
        :return: The number of bytes written.
        """
        with self.mutex:
            file = self.get_file(path)
            file.write(data)
            return len(data)

    def unlink(self, path):
        """
        Removes a file.

        :param path: The file path to remove.
        """
        with self.mutex:
            file = self.files.pop(path, None)
            if file:
                file.close()
                os.unlink(file.filepath)

    def release(self, path, fh=None):
        """
        Releases a file (closes it).

        :param path: The file path.
        :param fh: File handle (not used here).
        """
        with self.mutex:
            self.get_file(path).close()

    def truncate(self, path, length, fh=None):
        """
        Truncates the file to a specified length. If the new size is smaller,
        the existing file is streamed into a new file up to `length`. If larger,
        the file is extended with encrypted `\0`. The file properties are swapped
        and the original file is unlinked.

        :param path: The file path to truncate.
        :param length: The new size of the file.
        """
        with self.mutex:
            file = self.get_file(path)

            if length < file.size:
                os.truncate(file.filepath, length)

            file.seek(length)

            if length > file.size:
                length = length - file.size
                bytes_written = 0
                while bytes_written < length:
                    to_write = min(CHUNK_SIZE, length - bytes_written)
                    file.write(b'\0' * to_write)
                    bytes_written += to_write

    def chmod(self, path, mode):
        """
        Changes the permissions of the file at the specified path.

        :param path: The file path whose permissions will be changed.
        :param mode: The new permissions mode (e.g., 0o777 for full permissions).
        :raises FuseOSError: If the file does not exist.
        """
        file = self.get_file(path)
        return os.chmod(file.filepath, mode)

    def chown(self, path, uid, gid):
        """
        Changes the ownership of the file at the specified path.

        :param path: The file path whose ownership will be changed.
        :param uid: The user ID (uid) to set as the new owner.
        :param gid: The group ID (gid) to set as the new group owner.
        :raises FuseOSError: If the file does not exist.
        """
        file = self.get_file(path)
        return os.chown(file.filepath, uid, gid)

def mount(mount_point, storage_directory=None, foreground=False):
    """
    Initializes and mounts the ephemeral filesystem.

    :param mount_point: The path where the filesystem will be mounted.
    :param storage_directory: The directory to store the files (optional).
    :return: A `FUSE` object that represents the mounted filesystem.
    """
    def _mount(mount_point, storage_directory=None, foreground=False):
        # Create the mount point directory if it does not exist
        os.makedirs(mount_point, exist_ok=True)

        # If a storage directory is specified, create it as well
        if storage_directory:
            os.makedirs(storage_directory, exist_ok=True)

        return fuse.FUSE(EphemeralOperations(storage_directory), mount_point, foreground=foreground)

    thread = threading.Thread(target=_mount, args=(mount_point, storage_directory, foreground))
    thread.start()

    atexit.register(unmount_if_mounted, mount_point)

    return thread

def main():
    """
    The main function that parses arguments and starts the filesystem.
    """
    parser = argparse.ArgumentParser(description="GLOBALEAKS EPH FS")
    parser.add_argument('mount_point', help="Path to mount the filesystem")
    parser.add_argument('--storage_directory', '-s', help="Optional storage directory. Defaults to a temporary directory.")
    args = parser.parse_args()

    unmount_if_mounted(args.mount_point)

    try:
       print(f"Mounting GLOBALEAKS EPH FS at {args.mount_point}")
       mount(args.mount_point, args.storage_directory, True).join()

    except KeyboardInterrupt:
        sys.exit(0)
    except:
        sys.exit(1)
