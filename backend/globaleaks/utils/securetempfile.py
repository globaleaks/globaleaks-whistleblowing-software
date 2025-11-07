import os
import uuid
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import ChaCha20

CHUNK_SIZE = 64000


class SecureTemporaryFile:
    fd = enc = dec = None
    position = 0

    def __init__(self, filesdir, filename=None):
        """
        Initializes an ephemeral file with ChaCha20 encryption.
        Creates a new random file path and generates a unique encryption key and nonce.

        :param filesdir: The directory where the ephemeral file will be stored.
        :param filename: Optional filename. If not provided, a UUID4 is used.
        """
        filename = filename or str(uuid.uuid4())
        self.mode = None
        self.filepath = os.path.join(filesdir, filename)
        self.cipher = Cipher(ChaCha20(os.urandom(32), os.urandom(16)), mode=None, backend=default_backend())

    @property
    def size(self):
        """
        Returns the size of the encrypted file that is the same of the plaintext file
        """
        try:
            return os.stat(self.filepath).st_size
        except:
            return 0

    def open(self, mode='r'):
        """
        Opens the ephemeral file for reading or writing.

        :param mode: 'w' for writing, 'r' for reading.
        :return: The file object.
        """
        if not self.fd:
            self.fd = os.open(self.filepath, os.O_RDWR | os.O_CREAT | os.O_APPEND)
            os.lseek(self.fd, self.position, os.SEEK_SET)

        if (not self.enc and not self.dec) or self.mode != mode:
            self.mode = mode
            self.enc = self.cipher.encryptor()
            self.dec = self.cipher.decryptor()

            if mode == 'r':
                self.seek(0)
            else:
                self.seek(self.size)

        return self

    def write(self, data):
        """
        Writes encrypted data to the file.

        :param data: Data to write to the file, can be a string or bytes.
        """
        os.write(self.fd, self.enc.update(data))
        self.position += len(data)

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
            chunk_length = len(chunk)
            bytes_read += chunk_length
            self.position += chunk_length

            if size is not None and bytes_read >= size:
                break

        return data

    def seek(self, offset):
        """
        Sets the position for the next read operation.

        :param offset: The offset to seek to.
        """
        if offset < self.position:
            self.position = 0
            self.dec = self.cipher.decryptor()
            self.enc = self.cipher.encryptor()
            os.lseek(self.fd, 0, os.SEEK_SET)
            discard_size = offset
        else:
            discard_size = offset - self.position

        while discard_size > 0:
            to_read = min(CHUNK_SIZE, discard_size)
            self.enc.update(self.dec.update(os.read(self.fd, to_read)))
            discard_size -= to_read

        self.position = offset

    def tell(self):
        """
        Returns the current position in the file.

        :return: The current position in the file.
        """
        return self.position

    def close(self):
        """
        Closes the file descriptor.
        """
        if self.fd:
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
