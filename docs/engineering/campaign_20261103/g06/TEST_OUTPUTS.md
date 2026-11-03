# G06 verification outputs

This file is updated only from the commands in `GALAXY_API_CORE.md`; it is not evidence of device, AGNOS, Panda, CAN, ECU, or vehicle qualification.

Executed from `/mnt/commadrive/MVL_CAMPAIGN_G03_G10_20261103/g06` on 2026-11-03:

```text
$ python3.12 -m pytest -q openpilot/sunnypilot/starpilot_galaxy/tests
.....................                                                    [100%]
21 passed in 0.02s
```

```text
$ python3.12 -m compileall -q openpilot/sunnypilot/starpilot_galaxy
$
```

The combined command exited 0. An earlier local test expectation mismatch was
corrected before this final run: a non-text header is a malformed request and
correctly returns 400, rather than 401. The final suite additionally includes
an explicit unexpected provider object case.
