"""G10 passive AGNOS inventory safety tests; no target hardware."""
from __future__ import annotations

import json
import struct
from pathlib import Path
from unittest.mock import patch

import pytest
import agnos_passive_check as c

def test_missing_image_is_explicit_hold(tmp_path):
  assert c.report(tmp_path/"absent.ext4",tmp_path,tmp_path)["status"]=="HOLD_MISSING_IMAGE"

@pytest.mark.parametrize("cmd", [
  ["debugfs","-w","cat /VERSION","/tmp/foo"],
  ["debugfs","-R","rm /VERSION","/tmp/foo"],
  ["sh","-c","true"],
  ["git","-C","/tmp","reset","--hard"],
])
def test_command_allowlist_denies_mutations(cmd):
  with pytest.raises(AssertionError):
    c.run_readonly(cmd)

def test_elf_machine_detects_host_and_target(tmp_path):
  for machine,expected in ((62,"x86_64"),(183,"aarch64")):
    p=tmp_path/f"{machine}.so"
    header=bytearray(24)
    header[:4]=b"\x7fELF";header[4]=2;header[5]=1
    header[18:20]=struct.pack("<H",machine)
    p.write_bytes(header)
    assert c.elf_machine(p)["architecture"] == expected

def test_random_non_elf_rejected(tmp_path):
  p=tmp_path/"not_elf.bin";p.write_bytes(b"not-elf-content")
  assert c.elf_machine(p)["status"] == "NOT_ELF"

def test_readonly_hash_is_deterministic(tmp_path):
  p=tmp_path/"x.img";p.write_bytes(b"abcdef")
  assert c.bounded_hash(p) == c.bounded_hash(p)

def test_report_cannot_mislabel_host_binary_as_agnos_pass(tmp_path):
  f=tmp_path/"img";f.write_bytes(b"image-placeholder")
  path=tmp_path/"checkout";path.mkdir()
  (path/"openpilot/common").mkdir(parents=True)
  (path/"msgq_repo/msgq").mkdir(parents=True)
  lib=path/"openpilot/common/libparams_c.so"
  hdr=bytearray(24);hdr[:4]=b"\x7fELF";hdr[4]=2;hdr[5]=1;hdr[18:20]=struct.pack("<H",62)
  lib.write_bytes(hdr)
  def fake_run(cmd,*_):
    return {"git":c.FROZEN_MVL,"debugfs":"19.8.1"}.get(cmd[0],"")
  with patch.object(c,"bounded_hash",return_value=c.FROZEN_IMAGE_SHA256),patch.object(c,"run_readonly",side_effect=fake_run):
    res=c.report(f,path,tmp_path)
  assert res["status"] == "HOLD_FOR_ARM64_BUILD_AND_DEVICE"
  assert "HOST_X86_BINARIES_NOT_TARGET" in res["open_gates"]
  assert res["no_device_contact"] is True
