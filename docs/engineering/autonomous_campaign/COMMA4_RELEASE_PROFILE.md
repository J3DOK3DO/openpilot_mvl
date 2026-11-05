# COMMA4_NON_ACTUATING_MVL release profile

Status: **PRODUCT_BUILD_INCOMPLETE**. This is an offline engineering profile, not an installable or activated release. Only a comma 4 device is required for physical qualification of this restricted profile; those tests have not run. The accepted MVL control, Panda and Honda OEM source boundary remains unchanged.

## Included in the candidate scope

Native MVL offroad UI and warning priority, read-only status panels, an explicitly enabled read-only local Galaxy service if its transport is qualified, read-only model catalog, health/status monitoring, safe visual themes, stock model/control architecture, offline research, passive Honda health diagnostics, reproducible packaging and documented owner-managed recovery. Each item remains HOLD until its own implementation and test evidence exists.

## Excluded from active release

Custom Bosch-C longitudinal or new steering/braking commands, Panda safety-policy changes, ECU firmware changes, radar/camera disable, new CAN/UDS transmitters, experimental AOL/MADS/FLM/SLC actuation, model switching/downloads, and unfinished StarPort/audio. Existing stock behavior is retained. No hidden flag, environment variable, setting or startup route may activate excluded work.

## Qualification boundary

G11 external CAN-FD/HIL and G12 Honda dynamic OEM validation are **NOT_APPLICABLE_TO_COMMA4_PROFILE** only while the release diff contains no new active control, Panda, ECU or CAN-transmit behavior. This is a scope exclusion, not a safety PASS. Panda firmware/safety identity and stock-process observation on the comma 4 remain part of device evidence; comma-only checks cannot establish Honda ACC, FCW, CMBS/AEB or braking safety. Supplemental passive Honda diagnostics are not an acceptance gate. Any active-behavior diff must be removed from this branch or trigger a separate vehicle qualification profile.

Full product build and exact artifact provenance, software regressions, comma 4 native UI/security/resource tests, independent exact-commit review and separate user authorization for installation remain required. C4-12 physical restoration is WAIVED_BY_OWNER / NOT_EXECUTED; automated rollback and rollback stress are NOT_REQUIRED. The owner manages a possible factory reset and previous-version reinstallation using the known-good reference. Unexecuted device checks are NOT_TESTED; no clean-install-ready claim is permitted while the product build is incomplete.
