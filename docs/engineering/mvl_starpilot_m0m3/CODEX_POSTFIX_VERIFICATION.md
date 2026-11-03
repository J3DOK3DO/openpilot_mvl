Both reproduced findings are fixed.

- Forged topics: factory and adapter require `type(registry) is FeatureRegistry`, rejecting subclasses that override `active_topics()`. `FeatureRegistry.active_topics()` itself maps only the three fixed status topics, so `sendcan` cannot reach `SubMaster`.
- All-OFF: `ReadOnlyStatusAdapter.read()` returns before calling `now_ns` or accessing the source. The test directly verifies the clock is untouched; the opaque `object()` source would also fail if read.

No publish path appears in these files: factory creates only `messaging.SubMaster`; adapter is source-read/projection only. No remaining directly demonstrated issue in the inspected scope.