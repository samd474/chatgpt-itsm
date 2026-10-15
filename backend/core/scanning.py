"""Malware scanning through a clamd daemon (ClamAV) using the INSTREAM protocol.

No extra Python dependency: clamd speaks a tiny TCP protocol. When CLAMAV_HOST is
unset the scanner is "not configured"; whether that blocks uploads is controlled by
ATTACHMENT_SCAN_REQUIRED (on by default when DEBUG is off, i.e. fail closed).
"""
import logging
import socket
import struct

from django.conf import settings

logger = logging.getLogger(__name__)
CHUNK = 64 * 1024


class ScanUnavailable(Exception):
    pass


class ScanResult:
    def __init__(self, clean, detail=""):
        self.clean = clean
        self.detail = detail


def _instream(uploaded_file):
    host, port = settings.CLAMAV_HOST, settings.CLAMAV_PORT
    try:
        with socket.create_connection((host, port), timeout=settings.CLAMAV_TIMEOUT) as sock:
            sock.sendall(b"zINSTREAM\0")
            uploaded_file.seek(0)
            for chunk in iter(lambda: uploaded_file.read(CHUNK), b""):
                sock.sendall(struct.pack("!L", len(chunk)) + chunk)
            sock.sendall(struct.pack("!L", 0))
            response = b""
            while not response.endswith(b"\0"):
                data = sock.recv(4096)
                if not data:
                    break
                response += data
    except OSError as exc:
        raise ScanUnavailable(str(exc)) from exc
    finally:
        uploaded_file.seek(0)
    text = response.rstrip(b"\0").decode(errors="replace")
    # "stream: OK" or "stream: Eicar-Signature FOUND"
    if text.endswith("OK"):
        return ScanResult(True)
    if text.endswith("FOUND"):
        return ScanResult(False, text.split(":", 1)[-1].replace("FOUND", "").strip())
    raise ScanUnavailable(f"unexpected clamd response: {text[:200]}")


def scan_file(uploaded_file):
    """Return a ScanResult. Raises ScanUnavailable if scanning is required but impossible."""
    if not settings.CLAMAV_HOST:
        if settings.ATTACHMENT_SCAN_REQUIRED:
            raise ScanUnavailable("No malware scanner is configured.")
        logger.warning("Malware scanning skipped: CLAMAV_HOST is not set")
        return ScanResult(True, "not scanned")
    try:
        return _instream(uploaded_file)
    except ScanUnavailable:
        if settings.ATTACHMENT_SCAN_REQUIRED:
            raise
        logger.warning("Malware scanner unreachable; accepting upload because scanning is optional", exc_info=True)
        return ScanResult(True, "scanner unavailable")
