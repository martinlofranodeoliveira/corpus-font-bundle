"""Linux no-follow admission and same-filesystem no-replace publication."""
import ctypes
import errno
import os
import secrets
import stat

from .errors import BundleError
from .validation import FONT_LIMIT, path

ARTIFACTS = {"bundle.ttf", "bundle.woff2", "manifest.json"}
PREFIX = ".cfb-stage-"
MARKER = ".owned"


def directory_fd(value):
    absolute = os.path.abspath(path(value))
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in absolute.split("/"):
            if part:
                nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                os.close(fd)
                fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_in(fd, name, limit=FONT_LIMIT):
    before = os.stat(name, dir_fd=fd, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise BundleError("NOT_REGULAR_FILE")
    if before.st_size > limit:
        raise BundleError("INPUT_LIMIT")
    opened = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
    try:
        info = os.fstat(opened)
        if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino):
            raise BundleError("INPUT_CHANGED")
        chunks = []
        size = 0
        while True:
            block = os.read(opened, min(65536, limit + 1 - size))
            if not block:
                break
            chunks.append(block)
            size += len(block)
            if size > limit:
                raise BundleError("INPUT_LIMIT")
        after = os.fstat(opened)
        if (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise BundleError("INPUT_CHANGED")
        return b"".join(chunks)
    finally:
        os.close(opened)


def read_regular(value, limit=FONT_LIMIT):
    value = path(value)
    parent, name = os.path.split(value)
    fd = directory_fd(parent or ".")
    try:
        return read_in(fd, name, limit)
    finally:
        os.close(fd)


def _write(fd, name, data):
    out = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=fd)
    try:
        view = memoryview(data)
        while view:
            count = os.write(out, view)
            if count <= 0:
                raise OSError("write")
            view = view[count:]
        os.fsync(out)
    finally:
        os.close(out)


def _marker(name):
    token = name.removeprefix(PREFIX)
    if not name.startswith(PREFIX) or len(token) != 32 or any(c not in "0123456789abcdef" for c in token):
        raise BundleError("UNOWNED_STAGE")
    return ("corpus-font-bundle/1 " + token + "\n").encode("ascii")


def _cleanup(parent, name, fd):
    expected = _marker(name)
    linked = os.stat(name, dir_fd=parent, follow_symlinks=False)
    current = os.fstat(fd)
    if (linked.st_dev, linked.st_ino) != (current.st_dev, current.st_ino):
        raise BundleError("UNOWNED_STAGE")
    if read_in(fd, MARKER, 128) != expected:
        raise BundleError("UNOWNED_STAGE")
    names = set(os.listdir(fd))
    if not names <= ARTIFACTS | {MARKER}:
        raise BundleError("UNOWNED_STAGE")
    for item in names:
        if not stat.S_ISREG(os.stat(item, dir_fd=fd, follow_symlinks=False).st_mode):
            raise BundleError("UNOWNED_STAGE")
    for item in sorted(names - {MARKER}):
        os.unlink(item, dir_fd=fd)
    os.unlink(MARKER, dir_fd=fd)
    os.rmdir(name, dir_fd=parent)
    os.fsync(parent)


class Stage:
    def __init__(self, destination):
        destination = path(destination)
        parent, self.destination = os.path.split(destination)
        if not self.destination or self.destination in (".", ".."):
            raise BundleError("INVALID_PATH")
        self.parent = directory_fd(parent or ".")
        self.fd = None
        self.published = False
        self.name = PREFIX + secrets.token_hex(16)
        try:
            try:
                os.stat(self.destination, dir_fd=self.parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise BundleError("DESTINATION_EXISTS")
            os.mkdir(self.name, 0o700, dir_fd=self.parent)
            self.fd = os.open(self.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.parent)
            _write(self.fd, MARKER, _marker(self.name))
        except BaseException:
            if self.fd is not None:
                os.close(self.fd)
            os.close(self.parent)
            raise

    def write(self, name, data):
        if name not in ARTIFACTS or len(data) > FONT_LIMIT:
            raise BundleError("OUTPUT_LIMIT")
        _write(self.fd, name, data)

    def publish(self):
        if set(os.listdir(self.fd)) != ARTIFACTS | {MARKER}:
            raise BundleError("INCOMPLETE_STAGE")
        libc = ctypes.CDLL(None, use_errno=True)
        try:
            rename = libc.renameat2
        except AttributeError:
            raise BundleError("ATOMIC_PUBLICATION_UNAVAILABLE") from None
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        os.unlink(MARKER, dir_fd=self.fd)
        os.fsync(self.fd)
        result = rename(self.parent, os.fsencode(self.name), self.parent, os.fsencode(self.destination), 1)
        if result:
            error = ctypes.get_errno()
            _write(self.fd, MARKER, _marker(self.name))
            if error in (errno.EEXIST, errno.ENOTEMPTY):
                raise BundleError("DESTINATION_EXISTS")
            raise BundleError("ATOMIC_PUBLICATION_FAILED")
        self.published = True
        os.fsync(self.parent)

    def close(self):
        try:
            if not self.published:
                _cleanup(self.parent, self.name, self.fd)
        finally:
            os.close(self.fd)
            os.close(self.parent)


def recoverStage(stage):
    """Remove only an explicitly addressed, marked, flat staging directory."""
    try:
        parent, name = os.path.split(path(stage))
        _marker(name)
        parent_fd = directory_fd(parent or ".")
        try:
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
            try:
                _cleanup(parent_fd, name, fd)
            finally:
                os.close(fd)
        finally:
            os.close(parent_fd)
        return {"removed": True}
    except BundleError:
        raise
    except OSError:
        raise BundleError("RECOVERY_FAILED") from None
