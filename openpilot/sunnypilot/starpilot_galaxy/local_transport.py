"""Explicit, single-client Unix socket adapter for the read-only Galaxy core.

This module never constructs a listener on import or starts a background task.
A caller must opt in, provide a private directory, and drive ``serve_once``.
The local JSON protocol uses one 4-byte big-endian length and one request per
connection. No HTTP, TCP, device registration, or persistent connections exist.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import stat
import struct
import threading
import time
from typing import Any

from .core import GalaxyHandler, GalaxyRequest, GalaxyResponse

MAX_REQUEST_BYTES = 8192
MAX_RESPONSE_BYTES = 16384
MAX_HEADER_BYTES = 4096
MAX_PATH_BYTES = 256
TOTAL_REQUEST_SECONDS = 2.0
ACCEPT_POLL_SECONDS = 0.2
_SOCKET_NAME = "galaxy.sock"


class LocalTransportError(ValueError):
  """The explicit local listener cannot be safely constructed."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
  result: dict[str, Any] = {}
  for key, value in pairs:
    if key in result:
      raise ValueError("duplicate JSON key")
    result[key] = value
  return result


def _parse_request(raw: bytes) -> GalaxyRequest:
  try:
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
  except (UnicodeDecodeError, ValueError, RecursionError) as exc:
    raise ValueError("invalid request encoding") from exc
  if type(data) is not dict or set(data) != {"method", "path", "headers", "body"}:
    raise ValueError("invalid request fields")
  method, path, headers, body = (data[key] for key in ("method", "path", "headers", "body"))
  if (type(method) is not str or not method.isascii() or len(method) > 8 or
      type(path) is not str or not path.isascii() or not path.startswith("/") or
      len(path.encode("ascii")) > MAX_PATH_BYTES or type(body) is not str or body):
    raise ValueError("invalid method, path or body")
  if type(headers) is not dict or len(headers) > 8:
    raise ValueError("invalid headers")
  seen: set[str] = set()
  normalized: dict[str, str] = {}
  total = 0
  for name, value in headers.items():
    if type(name) is not str or type(value) is not str or not name.isascii() or not value.isascii():
      raise ValueError("invalid header encoding")
    folded = name.lower()
    if folded in seen or name != "X-Galaxy-Token":
      raise ValueError("duplicate or unsupported header")
    seen.add(folded)
    total += len(name) + len(value)
    if total > MAX_HEADER_BYTES:
      raise ValueError("headers too large")
    normalized[name] = value
  return GalaxyRequest(method, path, normalized)


def _encode_response(response: GalaxyResponse) -> bytes:
  payload = json.dumps({"status": response.status, "headers": dict(response.headers),
                        "body": response.body.decode("utf-8")}, separators=(",", ":")).encode("utf-8")
  if len(payload) > MAX_RESPONSE_BYTES:
    raise ValueError("response too large")
  return struct.pack(">I", len(payload)) + payload


def _error(status: int, code: str) -> bytes:
  return _encode_response(GalaxyResponse(status, {"Cache-Control": "no-cache, no-store",
                                                 "Content-Type": "application/json; charset=utf-8",
                                                 "X-Content-Type-Options": "nosniff"},
                                         json.dumps({"error": code}).encode("utf-8")))


def _recv_exact(connection: socket.socket, count: int, deadline: float) -> bytes:
  chunks: list[bytes] = []
  remaining = count
  while remaining:
    timeout = deadline - time.monotonic()
    if timeout <= 0:
      raise TimeoutError
    connection.settimeout(timeout)
    chunk = connection.recv(remaining)
    if not chunk:
      raise ValueError("truncated request")
    chunks.append(chunk)
    remaining -= len(chunk)
  return b"".join(chunks)


class LocalGalaxySocket:
  """Opt-in local listener with one active request and one request per client.

  I/O has a total two-second read deadline. The injected core providers must
  separately be bounded; this adapter cannot interrupt an arbitrary callback.
  """

  def __init__(self, handler: GalaxyHandler, private_directory: Path, *, enable: bool = False,
               allowed_uid: int | None = None) -> None:
    if enable is not True or type(handler) is not GalaxyHandler or not handler.enabled:
      raise LocalTransportError("explicit enabled Galaxy handler required")
    if not isinstance(private_directory, Path):
      raise LocalTransportError("private directory must be a Path")
    uid = os.geteuid()
    if allowed_uid is None:
      allowed_uid = uid
    if type(allowed_uid) is not int or allowed_uid < 0:
      raise LocalTransportError("allowed UID is invalid")
    try:
      info = private_directory.lstat()
    except OSError as exc:
      raise LocalTransportError("private directory unavailable") from exc
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_mode & 0o077:
      raise LocalTransportError("private directory must be owned and mode 0700")
    path = private_directory / _SOCKET_NAME
    if len(os.fsencode(path)) > 100 or path.exists() or path.is_symlink():
      raise LocalTransportError("socket path unavailable")
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    bound_inode: int | None = None
    try:
      listener.bind(str(path))
      bound_inode = path.lstat().st_ino
      os.chmod(path, 0o600)
      listener.listen(1)
      listener.settimeout(ACCEPT_POLL_SECONDS)
    except Exception:
      listener.close()
      try:
        if bound_inode is not None and path.lstat().st_ino == bound_inode:
          path.unlink()
      except OSError:
        pass
      raise
    self.path = path
    self._listener = listener
    self._inode = bound_inode
    self._allowed_uid = allowed_uid
    self._handler = handler
    self._serve_lock = threading.Lock()
    self._active: socket.socket | None = None
    self._closed = False

  def serve_once(self) -> bool:
    """Handle at most one local client; False means idle or closed."""
    if not self._serve_lock.acquire(blocking=False):
      raise LocalTransportError("only one active request is allowed")
    try:
      if self._closed:
        return False
      try:
        connection, _ = self._listener.accept()
      except socket.timeout:
        return False
      except OSError:
        if self._closed:
          return False
        raise
      self._active = connection
      with connection:
        self._handle_connection(connection)
      return True
    finally:
      self._active = None
      self._serve_lock.release()

  def _handle_connection(self, connection: socket.socket) -> None:
    try:
      credentials = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
      _, uid, _ = struct.unpack("3i", credentials)
      if uid != self._allowed_uid:
        return  # Reject the peer before reading any request bytes.
      deadline = time.monotonic() + TOTAL_REQUEST_SECONDS
      size = struct.unpack(">I", _recv_exact(connection, 4, deadline))[0]
      if not 0 < size <= MAX_REQUEST_BYTES:
        response = _error(413, "request_too_large")
      else:
        request = _parse_request(_recv_exact(connection, size, deadline))
        response = _encode_response(self._handler.handle(request))
    except TimeoutError:
      response = _error(408, "request_timeout")
    except ValueError:
      response = _error(400, "invalid_request")
    except (OSError, struct.error):
      return
    except Exception:
      response = _error(503, "service_unavailable")
    try:
      connection.settimeout(TOTAL_REQUEST_SECONDS)
      connection.sendall(response)
    except OSError:
      pass

  def close(self) -> None:
    if self._closed:
      return
    self._closed = True
    self._listener.close()
    if self._active is not None:
      try:
        self._active.shutdown(socket.SHUT_RDWR)
      except OSError:
        pass
    try:
      if self.path.lstat().st_ino == self._inode:
        self.path.unlink()
    except FileNotFoundError:
      pass

  def __enter__(self) -> LocalGalaxySocket:
    return self

  def __exit__(self, *_: object) -> None:
    self.close()
