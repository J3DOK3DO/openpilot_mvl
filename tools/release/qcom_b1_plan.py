#!/usr/bin/env python3
"""Print a preparation-only, conditional QCOM handoff plan. No execution path."""
import json

if __package__:
    from tools.release.qcom_b1_preflight import OUTPUTS, SOURCE_SHA, TINYGRAD_SHA, MANIFEST_SHA, TAR_SHA
else:
    from qcom_b1_preflight import OUTPUTS, SOURCE_SHA, TINYGRAD_SHA, MANIFEST_SHA, TAR_SHA


def plan() -> dict:
    targets = ' '.join('openpilot/selfdrive/modeld/models/' + name for name in OUTPUTS)
    return {
        'mode': 'PREPARATION_ONLY_NO_EXECUTE_FUNCTION',
        'authorization': 'Separate explicit authorization required for device transfer and compilation; separate later authorization for installation.',
        'source_commit': SOURCE_SHA,
        'tinygrad_gitlink': TINYGRAD_SHA,
        'external_manifest_sha256': MANIFEST_SHA,
        'source_tar_sha256': TAR_SHA,
        'required_gates': [
            'Authenticated fresh read-only model/AGNOS/driver/userspace/actual CPU+GPU thermal/resource observation',
            'Exact source, seven gitlinks, 283 selected LFS and two ONNX hashes verified',
            'AGNOS 19.9 image/component contract and matching Python/SCons/capnp/numpy verified',
            'Actual GPU scratch, output, TMPDIR, cache and peak RSS measured; available /data exceeds all peak allocations plus >=2 GiB reserve',
            'Taskset CPUs 0-7 available; isolated destination outside /data/openpilot and installed cache',
            'Separate owner authorization recorded before any transfer, mkdir, compile or output export',
        ],
        'conditional_commands_for_later_authorized_isolated_checkout': [
            'sha256sum <trusted-source-package>/manifest.json <trusted-source-package>/source.tar  # compare to external anchors',
            'git -C <isolated-exact-source-checkout> rev-parse HEAD  # must match source_commit',
            'git -C <isolated-exact-source-checkout> submodule status  # all seven exact gitlinks',
            'unset SKIP_TINYGRAD_COMPILE && env PATH=/usr/local/venv/bin:/usr/bin:/bin TMPDIR=<isolated-data-tmp> HOME=<isolated-data-home> PYTHONDONTWRITEBYTECODE=1 python3 -m SCons -j1 --minimal cache_dir=<isolated-cache> ' + targets,
        ],
        'environment_contract': 'TMPDIR and HOME must be inside an authorized isolated /data workspace; SKIP_TINYGRAD_COMPILE unset; capture exit status, hashes, RAM/storage/thermal peaks; never use installed /data/openpilot or /data/scons_cache.',
        'stop_if': ['identity mismatch', 'unknown capacity peak', 'free /data below 2 GiB',
                    'actual GPU sensor unavailable or hot', 'OOM/GPU fault', 'unexpected installed-path touch'],
        'device_write_performed': False,
    }


if __name__ == '__main__':
    print(json.dumps(plan(), indent=2, sort_keys=True))
