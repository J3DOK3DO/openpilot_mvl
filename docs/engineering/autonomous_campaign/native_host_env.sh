#!/usr/bin/env bash
set -euo pipefail
N1_ROOT="$(git rev-parse --show-toplevel)"
N1_CACHE=/home/jdkd/.cache/uv/archive-v0
N1_OPENDDBC=/home/jdkd/MVL_ARM64_STARPILOT_AUDIT_20261103/opendbc_repo
N1_MSGQ=/mnt/commadrive/MVL_NATIVE_LATEST_20261103/msgq_repo
test "$(git -C "$N1_OPENDDBC" rev-parse HEAD)" = 3fec9a418a659de31d7b1f494193161697a35071
test "$(git -C "$N1_MSGQ" rev-parse HEAD)" = e7396e76dadbb49e374d4b664ff6bbb43a39bcb0
test "$(sha256sum /mnt/commadrive/MVL_NATIVE_LATEST_20261103/openpilot/common/libparams_c.so | cut -d' ' -f1)" = e2697e7059c49213af2f3a77531c1e106095b341125b222d4d5dcb247c367ee2
N1_DEPS=""
for archive in HJ8IvN0WGY_5gp30 JBlb5ZaBDzzUJqx- L3-mW9Oqfz1zoGci LeThXFTEEz7bPc27 PmV2nLbh8AyKYaQz UH-a24BMXOkcNuXT Ygx3jUN9Qjb0-K5a Ynk3y7FHWtqKft7X _TdaHMDTHLMQHAmG c1vnjLhmjN518CFM i7wuLLr-rrR7DuZ2 k3LRoVSvwv89_ziQ lnGPQslxJ-4Eh_Li my2o4q-92WVATYjh u4q6xrLuYWQGD--R u8AcTYoFC6uArKy3; do
  test -d "$N1_CACHE/$archive"
  N1_DEPS="$N1_DEPS:$N1_CACHE/$archive"
done
export PYTHONPATH="$N1_ROOT:$N1_MSGQ:$N1_OPENDDBC:$N1_CACHE/k3LRoVSvwv89_ziQ/comma_deps_raylib-6.0.0.1.post106.data/purelib$N1_DEPS:/usr/lib/python3/dist-packages:$N1_ROOT/docs/engineering/campaign_20261103/g10"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
