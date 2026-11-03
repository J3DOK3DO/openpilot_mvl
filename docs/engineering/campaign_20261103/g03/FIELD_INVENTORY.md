# Source-backed message field inventory

Generated conceptually by the `inventory` command from local source only.
IPC registration evidence is `openpilot/cereal/services.py`: `deviceState`
(2 Hz), `selfdriveState` (100 Hz), and `carState` (100 Hz). Frequency is a
service declaration, not an ABI or freshness guarantee. Cap'n Proto mappings
below are field name, ordinal, and declared type.

| Topic | Source | Status | Fields |
|---|---|---|---|
| `deviceState` | `openpilot/cereal/log.capnp`, `DeviceState` | source-backed | `deviceType@45:InitData.DeviceType`; `chestnutPresent@51:Bool`; `usbState@52:UsbState`; `networkType@22:NetworkType`; `networkInfo@31:NetworkInfo`; `networkStrength@24:NetworkStrength`; `networkStats@43:NetworkStats`; `networkMetered@41:Bool`; `lastAthenaPingTime@32:UInt64`; `started@11:Bool`; `startedMonoTime@13:UInt64`; `freeSpacePercent@7:Float32`; `memoryUsagePercent@19:Int8`; `gpuUsagePercent@33:Int8`; `cpuUsagePercent@34:List(Int8)`; `offroadPowerUsageUwh@23:UInt32`; `carBatteryCapacityUwh@25:UInt32`; `powerDrawW@40:Float32`; `somPowerDrawW@42:Float32`; `cpuTempC@26:List(Float32)`; `gpuTempC@27:List(Float32)`; `dspTempC@49:Float32`; `memoryTempC@28:Float32`; `modemTempC@36:List(Float32)`; `pmicTempC@39:List(Float32)`; `intakeTempC@46:Float32`; `exhaustTempC@47:Float32`; `gnssTempC@48:Float32`; `bottomSocTempC@50:Float32`; `maxTempC@44:Float32`; `thermalZones@38:List(ThermalZone)`; `thermalStatus@14:ThermalStatus`; `fanSpeedPercentDesired@10:UInt16`; `screenBrightnessPercent@37:Int8` |
| `selfdriveState` | `openpilot/cereal/log.capnp`, `SelfdriveState` | source-backed | `state@0:OpenpilotState`; `enabled@1:Bool`; `active@2:Bool`; `engageable@9:Bool`; `alertText1@3:Text`; `alertText2@4:Text`; `alertStatus@5:AlertStatus`; `alertSize@6:AlertSize`; `alertType@7:Text`; `alertSound@13:AudibleAlert`; `alertHudVisual@12:Car.CarControl.HUDControl.VisualAlert`; `personality@11:LongitudinalPersonality` |
| `carState` | required `opendbc_repo/opendbc/car/car.capnp`, `CarState` | **SOURCE_UNAVAILABLE_REJECTED** | No field ordinal, type, nested type, or ABI mapping is claimed. The required local schema is absent. |

Nested structures/enums are named exactly as declared but are not expanded here;
doing so would claim a deeper mapping than this direct-field inventory verified.
No Python Cython/nanobind IPC binding compatibility is claimed or inferred.
