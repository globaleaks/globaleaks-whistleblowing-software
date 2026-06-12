#  zipstream
#  *********
#
# ZipStream Utility is derived from https://github.com/SpiderOak/ZipStream
# that is initially derived from zipfile.py and then changed heavily for
# our purpose (that's the reason why is not in third party)
import binascii
import os
import struct
import time
import zlib

from twisted.internet import abstract
from twisted.internet.defer import Deferred

from globaleaks.utils.crypto import GCE

__all__ = ["ZipStream"]

ZIP64_LIMIT = (1 << 31) - 1
ZIP_DEFLATED = 8

# Here are some struct module formats for reading headers
structEndArchive = b"<4s4H2lH"     # 9 items, end of archive, 22 bytes
stringEndArchive = b"PK\005\006"   # magic number for end of archive record
structCentralDir = b"<4s4B4HLLL5HLl"  # 19 items, central directory, 46 bytes
stringCentralDir = b"PK\001\002"   # magic number for central directory
structFileHeader = b"<4s2B4HlLL2H"  # 12 items, file header record, 30 bytes
stringFileHeader = b"PK\003\004"   # magic number for file header
structEndArchive64Locator = b"<4slql"  # 4 items, locate Zip64 header, 20 bytes
stringEndArchive64Locator = b"PK\x06\x07"  # magic token for locator header
# 10 items, end of archive (Zip64), 56 bytes
structEndArchive64 = b"<4sqhhllqqqq"
stringEndArchive64 = b"PK\x06\x06"  # magic token for Zip64 header
stringDataDescriptor = b"PK\x07\x08"  # magic number for data descriptor


class ZipInfo(object):
    """Class with attributes describing each file in the ZIP archive."""

    def __init__(self, filename="NoName", date_time=(1980, 1, 1, 0, 0, 0), compression=ZIP_DEFLATED):
        # Convert filename to bytes before we work with it
        self.orig_filename = filename   # Original file name in archive

        # Terminate the file name at the first null byte.  Null bytes in file
        # names are used as tricks by viruses in archives.
        null_byte = filename.find(chr(0))
        if null_byte >= 0:
            filename = filename[0:null_byte]
        # Normalize all path separators to forward slash and strip
        # directory-traversal sequences to prevent Zip Slip attacks.
        filename = filename.replace('\\', '/')
        filename = '/'.join(p for p in filename.split('/') if p not in ('', '.', '..'))

        self.filename = filename         # Normalized file name
        self.date_time = date_time       # year, month, day, hour, min, sec
        # Standard values:
        self.compress_type = compression  # Type of compression for the file
        self.comment = b""                # Comment for each file
        self.extra = b""                  # ZIP extra data

        # System which created ZIP archive
        #
        # evilaliv3:
        #   To avoid a particular leak on the real OS
        #   we declare always Windows.
        #
        # And probably this zip file would be
        #   also more compatible for some fucking
        #   Windows's reason!
        self.create_system = 0

        self.create_version = 20         # Version which created ZIP archive
        self.extract_version = 20        # Version needed to extract archive
        self.reserved = 0                # Must be zero
        self.flag_bits = 0x08            # ZIP flag bits, bit 3 indicates presence of data descriptor
        self.volume = 0                  # Volume number of file header
        self.internal_attr = 0           # Internal attributes

        self.external_attr = 0o600 << 16  # Security: Forced File Attributes

        # Other attributes set by class ZipFile:
        self.header_offset = 0           # Byte offset to the file header
        self.CRC = 0
        self.compress_size = 0
        self.file_size = 0

    def _encodeFilenameFlags(self):
        if isinstance(self.filename, str):
            try:
                return self.filename.encode('ascii'), self.flag_bits
            except UnicodeEncodeError:
                return self.filename.encode(), self.flag_bits | 0x800
        else:
            return self.filename, self.flag_bits

    def DataDescriptor(self):
        if self.compress_size > ZIP64_LIMIT or self.file_size > ZIP64_LIMIT:
            fmt = "<4sLQQ"
        else:
            fmt = "<4sLLL"

        return struct.pack(fmt, stringDataDescriptor, self.CRC, self.compress_size, self.file_size)

    def FileHeader(self):
        """Return the per-file header as a string."""
        dt = self.date_time
        dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
        dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
        if self.flag_bits & 0x08:
            # Set these to zero because we write them after the file data
            CRC = compress_size = file_size = 0
        else:
            CRC = self.CRC
            compress_size = self.compress_size
            file_size = self.file_size

        extra = self.extra

        if file_size > ZIP64_LIMIT or compress_size > ZIP64_LIMIT:
            # File is larger than what fits into a 4 byte integer,
            # fall back to the ZIP64 extension
            fmt = b'<hhqq'
            extra = extra + struct.pack(fmt, 1, struct.calcsize(fmt)-4, file_size, compress_size)
            file_size = 0xffffffff  # -1
            compress_size = 0xffffffff  # -1
            self.extract_version = max(45, self.extract_version)
            self.create_version = max(45, self.extract_version)

        filename, flag_bits = self._encodeFilenameFlags()

        header = struct.pack(structFileHeader, stringFileHeader,
                             self.extract_version, self.reserved, flag_bits,
                             self.compress_type, dostime, dosdate, CRC,
                             compress_size, file_size,
                             len(filename), len(extra))

        return header + filename + extra


class ZipStream(object):
    def __init__(self, files):
        self.files = files

        self.filelist = []  # List of ZipInfo instances for archive
        self.data_ptr = 0   # Keep track of location inside archive

        self.time = time.gmtime()[0:6]  # Security: Forced Time

    def update_data_ptr(self, data):
        """
        As data is added to the archive, update a pointer so we can determine
        the location of various structures as they are generated.

        data -- data to be added to archive

        Returns data
        """
        self.data_ptr += len(data)
        return data

    def zipinfo_open(self, arcname):
        zinfo = ZipInfo(arcname, self.time, ZIP_DEFLATED)
        zinfo.header_offset = self.data_ptr

        cmpr = zlib.compressobj(zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, -15)

        header = zinfo.FileHeader()

        self.update_data_ptr(header)

        self.filelist.append(zinfo)

        return zinfo, cmpr, header

    def zipinfo_update(self, zinfo, cmpr, chunk):
        zinfo.file_size += len(chunk)
        zinfo.CRC = binascii.crc32(chunk, zinfo.CRC) & 0xffffffff

        chunk = cmpr.compress(chunk)
        zinfo.compress_size += len(chunk)

        self.update_data_ptr(chunk)

        return chunk

    def zipinfo_close(self, zinfo, cmpr):
        buf = cmpr.flush()
        zinfo.compress_size += len(buf)
        self.update_data_ptr(buf)

        trailer = zinfo.DataDescriptor()
        self.update_data_ptr(trailer)

        return buf + trailer

    def zip_fo(self, fo, arcname):
        zipinfo, cmpr, header = self.zipinfo_open(arcname)

        yield header

        while True:
             buf = fo.read(8 * 1024)
             if not buf:
               break

             yield self.zipinfo_update(zipinfo, cmpr, buf)

        yield self.zipinfo_close(zipinfo, cmpr)

    def archive_footer(self):
        """
        Returns data to finish off an archive based on the files already
        added via zip_file(...).  The data returned corresponds to the fields:

        [archive decryption header]
        [archive extra data record]
        [central directory]
        [zip64 end of central directory record]
        [zip64 end of central directory locator]
        [end of central directory record]

        as described in section V. of the PKZIP Application Note:
        http://www.pkware.com/business_and_developers/developer/appnote/
        """
        data = []
        count = 0
        pos1 = self.data_ptr
        for zinfo in self.filelist:  # write central directory
            count += 1
            dt = zinfo.date_time
            dosdate = (dt[0] - 1980) << 9 | dt[1] << 5 | dt[2]
            dostime = dt[3] << 11 | dt[4] << 5 | (dt[5] // 2)
            extra = []
            if zinfo.file_size > ZIP64_LIMIT or zinfo.compress_size > ZIP64_LIMIT:
                extra.append(zinfo.file_size)
                extra.append(zinfo.compress_size)
                file_size = 0xffffffff  # -1
                compress_size = 0xffffffff  # -1
            else:
                file_size = zinfo.file_size
                compress_size = zinfo.compress_size

            if zinfo.header_offset > ZIP64_LIMIT:
                extra.append(zinfo.header_offset)
                header_offset = -1  # struct "l" format:  32 one bits
            else:
                header_offset = zinfo.header_offset

            extra_data = zinfo.extra
            if extra:
                # Append a ZIP64 field to the extra's
                extra_data = struct.pack('<hh' + 'q'*len(extra), 1, 8*len(extra), *extra) + extra_data
                extract_version = max(45, zinfo.extract_version)
                create_version = max(45, zinfo.create_version)
            else:
                extract_version = zinfo.extract_version
                create_version = zinfo.create_version

            filename, flag_bits = zinfo._encodeFilenameFlags()

            centdir = struct.pack(structCentralDir,
                                  stringCentralDir, create_version,
                                  zinfo.create_system, extract_version, zinfo.reserved,
                                  flag_bits, zinfo.compress_type, dostime, dosdate,
                                  zinfo.CRC, compress_size, file_size,
                                  len(filename), len(extra_data), len(zinfo.comment),
                                  0, zinfo.internal_attr, zinfo.external_attr,
                                  header_offset)

            data.append(self.update_data_ptr(centdir))
            data.append(self.update_data_ptr(filename))
            data.append(self.update_data_ptr(extra_data))
            data.append(self.update_data_ptr(zinfo.comment))

        pos2 = self.data_ptr
        # Write end-of-zip-archive record
        if pos1 > ZIP64_LIMIT:
            # Need to write the ZIP64 end-of-archive records
            zip64endrec = struct.pack(structEndArchive64, stringEndArchive64,
                                      44, 45, 45, 0, 0, count, count, pos2 - pos1, pos1)
            data.append(self.update_data_ptr(zip64endrec))

            zip64locrec = struct.pack(structEndArchive64Locator,
                                      stringEndArchive64Locator, 0, pos2, 1)
            data.append(self.update_data_ptr(zip64locrec))

            endrec = struct.pack(structEndArchive, stringEndArchive,
                                 0, 0, count, count, pos2 - pos1, -1, 0)
            data.append(self.update_data_ptr(endrec))

        else:
            endrec = struct.pack(structEndArchive, stringEndArchive,
                                 0, 0, count, count, pos2 - pos1, pos1, 0)
            data.append(self.update_data_ptr(endrec))

        return b''.join(data)

    def __iter__(self):
        for f in self.files:
            try:
                if 'key' in f:
                    with GCE.streaming_encryption_open('DECRYPT', f['key'], f['path']) as fo:
                        for data in self.zip_fo(fo, f['name']):
                            yield data
                elif 'fo' in f:
                    with f['fo']:
                        for data in self.zip_fo(f['fo'], f['name']):
                            yield data
                else:
                    with open(f['path'], "rb") as fo:
                        for data in self.zip_fo(fo, f['name']):
                            yield data
            except Exception:
                # Per-entry resilience: skip a single unreadable/corrupt file
                # rather than aborting the whole archive download.
                pass

        yield self.archive_footer()


class ZipStreamProducer(object):
    """Streaming producter for ZipStream"""

    def __init__(self, handler, zipstreamObject):
        self.finish = Deferred()
        self.handler = handler
        # Hold a single iterator so that successive resumeProducing() calls
        # resume the archive where the previous chunk left off. Iterating the
        # ZipStream object directly would create a fresh generator each call,
        # restarting from the first file and never terminating.
        self.zipstreamIterator = iter(zipstreamObject)

    def start(self):
        self.handler.request.registerProducer(self, False)
        return self.finish

    def resumeProducing(self):
        if not self.handler:
            return

        data = self.zip_chunk()
        if data:
            self.handler.request.write(data)
        else:
            self.stopProducing()

    def stopProducing(self):
        self.handler.request.unregisterProducer()
        self.handler.request.finish()
        self.handler = None
        self.finish.callback(None)

    def zip_chunk(self):
        chunk = []
        chunk_size = 0

        for data in self.zipstreamIterator:
            if data:
                chunk_size += len(data)
                chunk.append(data)
                if chunk_size >= abstract.FileDescriptor.bufferSize:
                    break

        return b''.join(chunk)
