#!/usr/bin/env python3
"""Create/verify a source-only MVL Qualcomm handoff. Never builds or installs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile

ONNX = {
  'openpilot/selfdrive/modeld/models/dmonitoring_model.onnx': 'dee5a294e8afaacc9295ac5d100e00733ecac278e79264b96331e40a3ede1b04',
  'openpilot/selfdrive/modeld/models/driving_supercombo.onnx': '65a08adc31d5c456219687d99b7bf5e44d61dae2d49ea67850e76105c7248cce',
}
AGNOS_SHA256 = '98e15de07c39a19b5fa17c96a67e66d4362f9ebaf7827b640f4127e3b6417da8'
SIX = ('dmonitoring_model_tinygrad.pkl','driving_tinygrad.pkl','driving_warp_1344x760_tinygrad.pkl','driving_warp_1928x1208_tinygrad.pkl','dm_warp_1344x760_tinygrad.pkl','dm_warp_1928x1208_tinygrad.pkl')

def run(*args, cwd=None):
  return subprocess.check_output(args, cwd=cwd, stderr=subprocess.PIPE).decode().strip()

def digest(path):
  h=hashlib.sha256()
  with path.open('rb') as f:
    for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
  return h.hexdigest()

def create(source, out, expected):
  source=source.resolve(); out=out.resolve()
  if out.exists() or out == source or source in out.parents:
    raise ValueError('output must be a new directory outside source')
  head=run('git','rev-parse','HEAD',cwd=source)
  if head != expected:raise ValueError(f'source HEAD {head} differs from expected {expected}')
  status=run('git','-c','filter.lfs.process=','-c','filter.lfs.required=false','status','--porcelain=v1',cwd=source)
  if status:raise ValueError('source worktree is dirty')
  gitlinks={}
  for line in run('git','ls-files','--stage',cwd=source).splitlines():
    fields=line.split(None,3)
    if fields[0]=='160000':
      path=fields[3]
      if run('git','rev-parse','HEAD',cwd=source/path)!=fields[1]:raise ValueError(f'unpinned submodule {path}')
      if run('git','-c','filter.lfs.process=','-c','filter.lfs.required=false','status','--porcelain=v1',cwd=source/path):raise ValueError(f'dirty submodule {path}')
      gitlinks[path]=fields[1]
  if len(gitlinks)!=7:raise ValueError(f'expected seven pinned submodules; got {len(gitlinks)}')
  raw=subprocess.check_output(['python3',str(source/'tools/release/release_files.py')],cwd=source)
  paths=sorted({os.fsdecode(x) for x in raw.split(b'\0') if x})
  paths.append('.gitmodules')
  paths=sorted(set(paths))
  if any(rel == 'openpilot/selfdrive/modeld/models/'+name for rel in paths for name in SIX):raise ValueError('generated stock QCOM output selected as source input')
  for p,sha in ONNX.items():
    if p not in paths or digest(source/p)!=sha:raise ValueError(f'ONNX identity failure: {p}')
  rows=[];out.mkdir(parents=True)
  tar_path=out/'source.tar'
  try:
    with tarfile.open(tar_path,'w',format=tarfile.PAX_FORMAT) as archive:
      for rel in paths:
        if rel.startswith('/') or '..' in Path(rel).parts or rel.startswith('.git/'):
          raise ValueError(f'unsafe source path {rel}')
        path=source/rel
        if not path.resolve().is_relative_to(source):raise ValueError(f'escaping source path {rel}')
        mode=path.lstat().st_mode
        entry=tarfile.TarInfo(rel);entry.mtime=0;entry.uid=0;entry.gid=0;entry.uname='';entry.gname=''
        if stat.S_ISLNK(mode):
          target=os.readlink(path)
          if not (path.parent/target).resolve().is_relative_to(source):raise ValueError(f'escaping symlink {rel}')
          entry.type=tarfile.SYMTYPE;entry.linkname=target;entry.mode=0o777
          archive.addfile(entry)
          rows.append({'path':rel,'kind':'symlink','target':target})
        elif stat.S_ISREG(mode):
          size=path.stat().st_size
          if size<256 and path.read_bytes().startswith(b'version https://git-lfs.github.com/spec/v1'):
            raise ValueError(f'unhydrated selected LFS pointer {rel}')
          entry.size=size;entry.mode=0o755 if mode&stat.S_IXUSR else 0o644
          with path.open('rb') as f:archive.addfile(entry,f)
          rows.append({'path':rel,'kind':'file','size':size,'sha256':digest(path)})
        else:raise ValueError(f'unsupported file kind {rel}')
    manifest={'schema_version':1,'package_kind':'SOURCE_ONLY_QCOM_HANDOFF_NOT_INSTALLABLE','source_commit':head,'prior_tested_source':'b39410908b15a27ff29f07b451ade468764bb148','gitlinks':gitlinks,'onnx_sha256':ONNX,'agnos_19_8_1_image_sha256':AGNOS_SHA256,'required_qcom_outputs':SIX,'files':rows,'source_tar_sha256':digest(tar_path),'no_qcom_outputs_included':True}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    shutil.copy2(Path(__file__),out/'verify_handoff.py')
    shutil.copy2(Path(__file__).with_name('monitor_qcom_handoff.sh'),out/'monitor_qcom_handoff.sh')
    (out/'README.md').write_text('''# MVL QCOM source-only handoff — NOT INSTALLABLE\n\nThis archive contains the exact source files, seven pinned submodule trees, hydrated selected LFS assets and both verified ONNX model inputs. It contains no valid QCOM outputs, complete product build or installation approval. Verify with `python3 verify_handoff.py verify --package .`. The manifest records every archived path and SHA-256. Preserve the external SHA-256 of `manifest.json` when transferring.\n\nDevice-side source copying or compilation requires separate owner authorization. The known-good installation, `/data/openpilot`, AGNOS reference and vehicle must remain untouched. Before any separately authorized action, use an isolated empty source checkout at the manifest source commit with its seven pinned submodules; overlay this verified archive there, then verify Git HEAD, gitlinks, all file hashes, AGNOS 19.8.1, `uname -m=aarch64`, `/AGNOS`, `/dev/kgsl-3d0`, disk/power/thermal limits and absence of vehicle connection. Do not use this tar alone as a Git checkout: SCons and Panda versioning require Git metadata. Do not set `SKIP_TINYGRAD_COMPILE`.\n\nNative six-target command (only after authorization and preflight):\n\n`python3 -m SCons -j4 --minimal cache_dir=<new-isolated-cache> openpilot/selfdrive/modeld/models/dmonitoring_model_tinygrad.pkl openpilot/selfdrive/modeld/models/driving_tinygrad.pkl openpilot/selfdrive/modeld/models/driving_warp_1344x760_tinygrad.pkl openpilot/selfdrive/modeld/models/driving_warp_1928x1208_tinygrad.pkl openpilot/selfdrive/modeld/models/dm_warp_1344x760_tinygrad.pkl openpilot/selfdrive/modeld/models/dm_warp_1928x1208_tinygrad.pkl`\n\nBound the command with an operator-approved timeout and run `sh monitor_qcom_handoff.sh 180` in a separate terminal and record supported GPU/power telemetry; stop on low space, thermal fault or GPU error. Preserve stdout, stderr, exit status, device/AGNOS identity and all six output hashes. Copy outputs to a separate private artifact directory, then run `tools/release/mvl_model_artifacts.py record` and `verify` with the exact source, ONNX, pinned AGNOS image/root and artifact directory. A static PASS remains insufficient for full product/device qualification. Do not install or activate.\n''')
    verify(out)
    print(json.dumps({'package':str(out),'source_commit':head,'file_count':len(rows),'tar_sha256':manifest['source_tar_sha256'],'manifest_sha256':digest(out/'manifest.json'),'gitlinks':len(gitlinks)}))
  except Exception:
    shutil.rmtree(out)
    raise

def verify(package):
  package=package.resolve()
  def unique_pairs(pairs):
    result={}
    for key,value in pairs:
      if key in result:raise ValueError(f'duplicate manifest key {key}')
      result[key]=value
    return result
  manifest=json.loads((package/'manifest.json').read_text(),object_pairs_hook=unique_pairs)
  if manifest['package_kind']!='SOURCE_ONLY_QCOM_HANDOFF_NOT_INSTALLABLE' or manifest['source_tar_sha256']!=digest(package/'source.tar'):
    raise ValueError('package kind or tar hash mismatch')
  expected=manifest['files']; actual=[]
  with tarfile.open(package/'source.tar','r') as archive:
    for member in archive:
      if member.name.startswith('/') or '..' in Path(member.name).parts:raise ValueError('unsafe tar path')
      if member.issym():actual.append({'path':member.name,'kind':'symlink','target':member.linkname})
      elif member.isfile():
        h=hashlib.sha256();stream=archive.extractfile(member)
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
        actual.append({'path':member.name,'kind':'file','size':member.size,'sha256':h.hexdigest()})
      else:raise ValueError('unsupported tar member')
  if actual!=expected:raise ValueError('archived path/contents differ from manifest')
  if len(manifest['gitlinks'])!=7 or manifest['onnx_sha256']!=ONNX or manifest['agnos_19_8_1_image_sha256']!=AGNOS_SHA256 or tuple(manifest['required_qcom_outputs'])!=SIX:raise ValueError('build contract mismatch')
  print(json.dumps({'verification':'PASS','files':len(actual),'source_commit':manifest['source_commit'],'tar_sha256':manifest['source_tar_sha256']}))

if __name__=='__main__':
  p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
  c=s.add_parser('create');c.add_argument('--source',type=Path,required=True);c.add_argument('--out',type=Path,required=True);c.add_argument('--expected-commit',required=True)
  v=s.add_parser('verify');v.add_argument('--package',type=Path,required=True)
  a=p.parse_args()
  if a.command=='create':create(a.source,a.out,a.expected_commit)
  else:verify(a.package)
