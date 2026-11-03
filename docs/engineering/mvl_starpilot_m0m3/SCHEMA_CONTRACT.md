# M1 native-schema and compatibility contract

**Owner:** MVL-native Cereal and SubMaster. **Schema source:** pinned MVL `openpilot/cereal/log.capnp`, `opendbc_repo/opendbc/car/car.capnp`. No generated schema changes are proposed. **Bridge version:** 1, code-only, no serialized API.

| Topic / MVL field | Native schema type | Exposed immutable projection | Accepted range / rule | Ownership |
|---|---|---|---|---|
| `deviceState.started` | Bool | `device.started: bool` | Exact Python bool | MVL device service |
| `deviceState.freeSpacePercent` | Float32 | `device.free_space_percent: float` | finite 0–100 percent | MVL device service |
| `deviceState.maxTempC` | Float32 | `device.max_temp_c: float` | finite 0–150 °C conservative display range | MVL device service |
| `selfdriveState.enabled` | Bool | `selfdrive.enabled: bool` | Exact Python bool, informational only | MVL selfdrive |
| `selfdriveState.active` | Bool | `selfdrive.active: bool` | Exact Python bool, informational only | MVL selfdrive |
| `carState.vEgo` | Float32 | `car.v_ego_mps: float` | finite 0–100 m/s (display sanity gate, not calibration) | MVL carState |
| `carState.cruiseState.enabled` | Bool | `car.cruise_enabled: bool` | Exact Python bool, informational only | MVL carState |

Topic validity and freshness are checked from the caller-supplied SubMaster-like source: `source.alive[topic]`, `source.valid[topic]`, `source.logMonoTime[topic]`, `source[topic]`. A deliberately injected monotonic `now_ns` is required, enabling deterministic offline tests. The default maximum accepted age is **2,000,000,000 ns**; timestamp must be positive and <= now, and later accepted reads must advance per topic. Missing/invalid/future/stale/out-of-order/broken source => `None` plus a `TopicRejection`, not a fabricated default. No source object is mutated. A clock failure yields no accepted payload.

**Feature names:** `device_status` ↔ `deviceState`; `selfdrive_status` ↔ `selfdriveState`; `car_status` ↔ `carState`. All OFF in the empty `FeatureRegistry()`; a caller can construct an explicit immutable in-memory registry with exact boolean values. There are no persistent migration keys or reading existing Params at this stage.

**Vehicle identity:** The three projections are generic read-only information. They intentionally do **not** expose or claim an Accord 11G-specific feature, permission or safety state. No Honda fingerprint/CarParams is used for granting behavior because the bridge grants no behavior. Any future Accord-specific status should receive a separate exact-CP/safety identity contract and tests before introduction.

**Shared Params quarantine:** The original source assessment detected **254 literal key names** present in both trees. `SHARED_PARAMS_QUARANTINE_254.csv` enumerates each one and marks `ProposedImport=DENY`, `ReadEnabled=FALSE`, `WriteEnabled=FALSE`, type `UNVERIFIED` and `REQUIRES_EXACT_SCHEMA_SEMANTIC_REVIEW`. This is an *explicit reviewed-safe refusal to migrate*, not proof that all 254 keys have completed semantic review. Equal key spellings cannot establish equal type, defaults, authorization, lifetime or safety ownership.

**Native ABI limitation:** MVL Cython IPC libraries are not interchangeable with Dom's nanobind IPC. The bridge subscribes through native MVL messaging only; it carries no Dom native libraries, cereal schema, model artifacts or executable. The current x86-64 host tests cannot prove AGNOS 19.8.1 ARM64 runtime compatibility.
