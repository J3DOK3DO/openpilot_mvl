# R3 read-only MVL-StarPilot dashboard

This payload is a clean-installable, disconnected display application for a
Comma 4 MICI running AGNOS 19.9. It has native compact (536x240) and host-test
large (2160x1080) layouts, matching the dimensions defined by the frozen MVL
`GuiApplication`. Production selects compact and cannot enable demo mode.

It intentionally has no manager, cereal/msgq, Params, Panda, CAN, model,
camera, telemetry, publisher, updater, controls, or actuation dependency. The
screen always says DISPLAY ONLY, DISCONNECTED / NO VEHICLE DATA, and ACTUATION
DISABLED. The optional static route preview is qualification-only, disabled by
the production launcher, and watermarked DEMO / OFFLINE.

Offline rendering does not qualify the physical Qualcomm GPU, DRM/EGL,
display ownership, boot behavior, power, thermal behavior, or recovery.
