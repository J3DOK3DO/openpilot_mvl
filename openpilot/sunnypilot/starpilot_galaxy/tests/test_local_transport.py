"""Host-only negative coverage for the opt-in Unix Galaxy adapter."""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import struct
import threading

import pytest

from openpilot.sunnypilot.starpilot_bridge.models import BridgeSnapshot, DeviceStatus
from openpilot.sunnypilot.starpilot_galaxy import GalaxyHandler, GalaxySettings
from openpilot.sunnypilot.starpilot_galaxy.local_transport import LocalGalaxySocket, LocalTransportError, MAX_REQUEST_BYTES

NOW = 10_000_000_000
TOKEN = "local-test-secret"


def _handler(provider=None, *, enabled=True):
  if provider is None:
    provider = lambda: BridgeSnapshot(NOW, device=DeviceStatus(False, 50.0, 40.0, NOW - 1))
  return GalaxyHandler(GalaxySettings(enabled=enabled, token=TOKEN), provider, lambda: NOW)


def _request(*, method="GET", path="/api/v1/status", token=TOKEN, body="", headers=None) -> bytes:
  if headers is None:
    headers = {"X-Galaxy-Token": token}
  return json.dumps({"method": method, "path": path, "headers": headers, "body": body}).encode()


def _exchange(server: LocalGalaxySocket, raw: bytes, *, announced_size: int | None = None,
              shutdown_write: bool = False) -> dict:
  worker = threading.Thread(target=server.serve_once)
  worker.start()
  with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
    client.settimeout(3)
    client.connect(str(server.path))
    client.sendall(struct.pack(">I", len(raw) if announced_size is None else announced_size) + raw)
    if shutdown_write:
      client.shutdown(socket.SHUT_WR)
    try:
      prefix = client.recv(4)
    except ConnectionResetError:
      prefix = b""
    if not prefix:
      result = {}
    else:
      size = struct.unpack(">I", prefix)[0]
      chunks = []
      while sum(map(len, chunks)) < size:
        chunk = client.recv(size - sum(map(len, chunks)))
        if not chunk:
          break
        chunks.append(chunk)
      result = json.loads(b"".join(chunks))
  worker.join(timeout=3)
  assert not worker.is_alive()
  return result


@pytest.fixture
def private_directory(tmp_path: Path) -> Path:
  directory = tmp_path / "private"
  directory.mkdir(mode=0o700)
  return directory


def test_explicit_opt_in_private_directory_and_cleanup(private_directory, tmp_path):
  with pytest.raises(LocalTransportError):
    LocalGalaxySocket(_handler(), private_directory)
  with pytest.raises(LocalTransportError):
    LocalGalaxySocket(_handler(enabled=False), private_directory, enable=True)
  unsafe_directory = tmp_path / "unsafe"
  unsafe_directory.mkdir(mode=0o755)
  with pytest.raises(LocalTransportError):
    LocalGalaxySocket(_handler(), unsafe_directory, enable=True)
  with LocalGalaxySocket(_handler(), private_directory, enable=True) as server:
    assert server.path.stat().st_mode & 0o777 == 0o600
    response = _exchange(server, _request())
    assert response["status"] == 200
    assert response["body"].startswith('{"snapshot_time_ns":')
    assert TOKEN not in str(response)
  assert not (private_directory / "galaxy.sock").exists()
  assert server.serve_once() is False


@pytest.mark.parametrize("raw,expected_status", [
  (_request(token="wrong"), 401),
  (_request(method="POST"), 405),
  (_request(path="/unknown"), 404),
  (_request(body="not empty"), 400),
  (_request(headers={"x-galaxy-token": TOKEN}), 400),
  (_request(headers={"X-Galaxy-Token": TOKEN, "x-galaxy-token": TOKEN}), 400),
  (_request(path="/" + "x" * 256), 400),
  (_request(headers={"X-Galaxy-Token": "x" * 4096}), 400),
  (b'{"method":"GET","method":"POST","path":"/api/v1/status","headers":{},"body":""}', 400),
  (b'{"method":"GET","path":"/api/v1/status","headers":{"X-Galaxy-Token":"a","X-Galaxy-Token":"b"},"body":""}', 400),
  (b'\xff', 400),
])
def test_negative_request_shapes(private_directory, raw, expected_status):
  with LocalGalaxySocket(_handler(), private_directory, enable=True) as server:
    response = _exchange(server, raw)
  assert response["status"] == expected_status
  assert TOKEN not in str(response)


def test_oversize_and_truncated_request(private_directory):
  with LocalGalaxySocket(_handler(), private_directory, enable=True) as server:
    oversized = _exchange(server, b"", announced_size=MAX_REQUEST_BYTES + 1)
    truncated = _exchange(server, b"x", announced_size=20, shutdown_write=True)
  assert oversized["status"] == 413
  assert truncated["status"] == 400


def test_slow_request_deadline_and_single_active_client(private_directory, monkeypatch):
  import openpilot.sunnypilot.starpilot_galaxy.local_transport as transport
  monkeypatch.setattr(transport, "TOTAL_REQUEST_SECONDS", 0.1)
  with LocalGalaxySocket(_handler(), private_directory, enable=True) as server:
    worker = threading.Thread(target=server.serve_once)
    worker.start()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
      client.settimeout(2)
      client.connect(str(server.path))
      client.sendall(struct.pack(">I", 10))
      for _ in range(100):
        if server._active is not None:
          break
        threading.Event().wait(0.001)
      assert server._active is not None
      with pytest.raises(LocalTransportError, match="one active"):
        server.serve_once()
      prefix = client.recv(4)
      size = struct.unpack(">I", prefix)[0]
      response = json.loads(client.recv(size))
    worker.join(timeout=2)
    assert not worker.is_alive()
  assert response["status"] == 408


def test_peer_rejected_before_provider_or_request_read(private_directory):
  calls = []
  with LocalGalaxySocket(_handler(lambda: calls.append(True)), private_directory,
                         enable=True, allowed_uid=os.geteuid() + 1) as server:
    assert _exchange(server, _request()) == {}
  assert calls == []


def test_provider_failure_is_generic_and_no_reuse(private_directory):
  def failed():
    raise RuntimeError("private provider path")
  with LocalGalaxySocket(_handler(failed), private_directory, enable=True) as server:
    response = _exchange(server, _request())
  assert response["status"] == 503
  assert "private provider path" not in str(response)


def test_no_production_registration_or_vehicle_control_imports():
  source = (Path(__file__).parents[1] / "local_transport.py").read_text()
  for forbidden in ("Params", "sendcan", "PubMaster", "pandad", "modeld", "selfdrived", "AF_INET", "SOCK_DGRAM"):
    assert forbidden not in source


def test_failed_bind_never_removes_existing_socket_path(private_directory, monkeypatch):
  import openpilot.sunnypilot.starpilot_galaxy.local_transport as transport
  existing = private_directory / 'galaxy.sock'
  class RacingSocket:
    def bind(self, address):
      existing.write_bytes(b'other-owner')
      raise OSError('simulated competing creator')

    def close(self):
      pass

  monkeypatch.setattr(transport.socket, 'socket', lambda *_: RacingSocket())
  with pytest.raises(OSError, match='competing creator'):
    LocalGalaxySocket(_handler(), private_directory, enable=True)
  assert existing.read_bytes() == b'other-owner'
