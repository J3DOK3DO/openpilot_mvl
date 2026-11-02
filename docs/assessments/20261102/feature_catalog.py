import ast,csv,json,re
from pathlib import Path
from collections import Counter,defaultdict
DOM=Path(r"D:\Dom 7.0\StarPilot-Dom-Assessment-20261102")
OUT=Path(r"D:\Dom 7.0\_StarPilot_Assessment_20261102")
SHA="cbd6e1eb52e8a46f9837a750d675b877d5ac8762"
root=DOM/"openpilot"/"starpilot"
# Every first-party feature family has a deliberate source-level disposition and a clear MVL owner.
F={
"analytics":("DEFER_TELEMETRY","Offroad usage and location reporting to external server; require explicit privacy policy, opt-in, disable/egress tests.","MVL has its own device and usage lifecycle","privacy/egress isolation and opt-in tests","L"),
"aol":("OFFLINE_COMPARE_NO_LIVE_PORT","Independent axis mode changes native permission, Honda stock mode and safety receipts; keep MVL MADS and Bosch-C owner.","openpilot/sunnypilot/mads/mads.py","exact CP/safety/axis/stock-ACC tests","H"),
"audio":("ADAPT_BEHIND_MVL_SOUND","Sound packs, seven alert families and audio volume controls; preserve immediate warning and native soundd timing.","openpilot/selfdrive/ui and system soundd","audible urgent alerts, volume limits, device tests","M"),
"bluetooth":("BENCH_ISOLATED","Bluetooth owner with resource conflicts and pairing; device services must be isolated.","MVL system Bluetooth services","pair/unpair, process recovery, no onroad disruption","M"),
"car":("NO_CAR_PORT","Car adapters are safety and topology specific; other brands excluded and Honda owner stays MVL.","mvl-boston/opendbc honda controllers","vehicle authority/stock brake/harness tests; no direct import","H"),
"companion":("OPTIONAL_EXTERNAL_APP","Android/iOS apps and BLE pairing; separate signing/store/privacy and host tests.","MVL sunnylink unrelated transport","app builds, pairing auth, optional rollout","M"),
"conditional_mode":("OFFLINE_SIM_ONLY","Conditional Experimental/Chill policy tied to longitudinal axis and fresh planner, some live support Ioniq 6 only.","MVL cruise planner and experimental state","state/clock/source freshness, vehicle gates, no live Honda","H"),
"connect":("DEFER_REMOTE","Remote connections require separate credentials, transport and security review.","MVL sunnylink/connection services","auth, external egress, secret handling","H"),
"controllers":("OFFLINE_COMPARE","Cruise wheel, coast, owner arbitration and control actions; MVL's Honda stock ACC must own target.","openpilot/sunnypilot/selfdrive/car/cruise_ext.py","button provenance, no unintended SET/RES, override tests","H"),
"curve_speed":("PORT_READONLY_POLICY_OFFLINE","Learned comfort and future curve geometry can be offline advisory; planner/ACC adoption is vehicle-gated.","MVL smart_cruise_control map_controller","replay geometry + bounds, no live speed writes","H"),
"drive_state":("PORT_READONLY","Trip/engagement state analytics can be non-actuating with live messages only.","MVL live-state and trip UI","freshness and recorder isolation tests","L"),
"favorites":("ADAPT_UI","Favorites, shortcuts and settings drafts must map to MVL UI navigation.","MVL UI home and nav preferences","settings persistence, no owner mutation surprises","L"),
"flm":("OFFLINE_RESEARCH_ONLY","Steering learning and Ioniq torque surface; no Honda live torque promotion.","MVL latcontrol_torque_ext and NNLC","native steering limit and replay model validation","H"),
"galaxy":("PORT_AUTHENTICATED_LOCAL_READONLY_FIRST","Vue local web companion, many device and settings APIs; preserve auth and parked authority, defer mutations.","MVL settings and SunnyLink APIs","local bind/auth, read-only endpoints, CSRF and parked gating","M"),
"galaxy_bluetooth":("BENCH_ISOLATED","Paired phone bridge, GATT proxy, LAN discovery and key storage require threat model.","MVL existing Bluetooth/connection owners","pairing key and replay/ble test with device","M"),
"gps":("COMPARE_AND_ADAPT","GPS formatting/freshness only where native MVL location sources exist.","MVL mapd and locationd","timestamp coherence and null sensor tests","M"),
"lateral":("OFFLINE_ONLY","Lane centering/torque/clearance source gating is vehicle-specific; runtime is not Honda qualified.","MVL torque extension, NNLC, lane-change pipeline","replay synthetic, limiter and manual override tests","H"),
"longitudinal":("OFFLINE_ONLY","Profiles, controllers, plan shaping and speed targets may affect brake/ACC ownership.","MVL longitudinal planner and Bosch-C carcontroller","stop/start, OEM ACC, lead/AEB, safety tests","H"),
"maps":("ADAPT_UI_AND_STATUS","Maps regions/cache operations overlap MVL mapd; avoid replacing map database owner.","openpilot/sunnypilot/mapd","download checksum/cache, offline and drive continuity","M"),
"models":("DEFER_RUNNER_PORT;_UI_FIRST","Model catalog, downloads, status, JetLink and lab require artifact ABI and AGNOS GPU proof; lab not in modeld.","openpilot/sunnypilot/modeld_v2 and models","SHA256/ABI/compiler/AGNOS/modeld freshness tests","H"),
"navigation":("ADAPT_UI","Navigation and favorites should reuse MVL navd and mapd topology.","openpilot/sunnypilot/navd and mapd","route/speed coordinate integrity and offline fallback","M"),
"power":("COMPARE_NO_SYSTEM_POLICY_REPLACE","Power and shutdown policies can affect parked service, memory and device recoverability.","MVL system hardware/manager policies","voltage, thermal, battery and offroad tests","H"),
"replay":("PORT_DEV_TOOLING_ONLY","Recorded-log readers and replay adapters offline, no runtime control grants.","MVL log/replay tools","reproducible no-transmit test harness","L"),
"sentry_mode":("BENCH_READONLY_FIRST","Parked motion/event capture and push notification not physically qualified; camera privacy and power risk.","MVL camera and process lifecycle","parked-only, consent, power, privacy, sensor tests","M"),
"software":("STATUS_READONLY_MUTATIONS_DEFER","Version/status, branch update, install and rollback operations must retain MVL recovery.","MVL updater/manager","offroad-only, rollback, integrity and signed update tests","H"),
"soloist":("BENCH_ISOLATED","Spotify Connect and paired-phone A2DP/PCM audio share audio owners.","MVL soundd and Bluetooth","audio priority, Bluetooth recovery, alert preemption","M"),
"speed_limits":("UI_ADVISORY_ONLY;_CONTROL_OFFLINE","SLC updates vCruise in Card, not a planner ceiling; Honda stock ACC adoption unqualified.","MVL smart_cruise_control and speed_limit_assist","source/offset/SET/RES, OEM cruise ownership","H"),
"spot_monitor":("UI_READONLY_ONLY","Visual spot warnings from V-ASM must not qualify adjacent lane as clear or alter lane-change.","MVL side-camera/BSM UI","false-positive, GPU/latency and no-actuation tests","M"),
"system":("BENCH_STARPORT_AND_JETLINK","StarPort GPU projection/USB and JetLink need device ownership and hardware qualification.","MVL manager/system resources","C4 encoder/thermal, USB, no-onroad resource starvation","H"),
"ui":("PORT_SELECTIVE_VISUALS","Native UI, layouts and widgets require layout and Params adapters; preserve MVL camera/UI lifecycle.","MVL C3/C4 UI and sunnypilot layouts","snapshot, touch, performance, warning overlays","M"),
"validation":("PORT_TOOLING","Recorded control mode schemas/validators are offline evidence, not a safety release.","MVL native/pytest and Panda tests","trace identity, matrix reject negatives","L"),
"tests":("PORT_RELEVANT_TESTS_ONLY","Test fixtures cannot grant deployment permissions.","MVL test suites","native tests and independent regressions","L")
}
overlap_examples={
"lateral":["openpilot/sunnypilot/selfdrive/controls/lib/latcontrol_torque_ext.py","openpilot/sunnypilot/selfdrive/controls/lib/auto_lane_change.py"],
"longitudinal":["openpilot/sunnypilot/selfdrive/controls/lib/longitudinal_planner.py","openpilot/sunnypilot/selfdrive/controls/lib/smart_cruise_control/smart_cruise_control.py"],
"speed_limits":["openpilot/sunnypilot/selfdrive/controls/lib/smart_cruise_control/vision_controller.py","openpilot/selfdrive/ui/sunnypilot/onroad/speed_limit.py"],
"models":["openpilot/sunnypilot/models/manager.py","openpilot/sunnypilot/modeld_v2/modeld.py"],
"maps":["openpilot/sunnypilot/mapd/mapd_manager.py"],
"navigation":["openpilot/sunnypilot/navd/helpers.py"],
"aol":["openpilot/sunnypilot/mads/mads.py"],
"ui":["openpilot/selfdrive/ui/sunnypilot/layouts/settings/steering_sub_layouts/lane_change_settings.py"]}
def src(p):return "https://github.com/StarPilotHQ/StarPilot/blob/"+SHA+"/"+p
def mv(p):return "https://github.com/mvl-boston/openpilot/blob/a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1/"+p
catalog=[];components=[]
for name,d in sorted((p.name,p) for p in root.iterdir() if p.is_dir()):
 cfg=F.get(name,("MANUAL_REVIEW","Unmapped package; retain MVL until source-qualified.","MVL baseline","offline/source review","M"))
 files=sorted(p for p in d.rglob("*") if p.is_file())
 py_files=[p for p in files if p.suffix==".py"]
 test_count=sum("test_" in p.name or "tests" in p.parts for p in files)
 source_files=[p for p in files if p.suffix.lower() in (".py",".cpp",".cc",".c",".h",".hpp",".kt",".swift",".ts",".tsx",".vue",".js",".sh") and not any(x in p.parts for x in ("tests","vendor","node_modules")) and not p.name.startswith("test_")]
 readme=d/"README.md";entry=readme if readme.exists() else (source_files[0] if source_files else files[0])
 ref=entry.relative_to(DOM).as_posix()
 overlap=overlap_examples.get(name,[])
 catalog.append({"Family":name,"TotalFiles":len(files),"TestOrFixtureFiles":test_count,"ExecutableSourceComponents":len(source_files),"DomFeatureDecision":cfg[0],"ReviewRationale":cfg[1],"MVLInterface":cfg[2],"SafetyOrSecurityAcceptance":cfg[3],"Risk":cfg[4],"DomEvidence":src(ref),"MVLEvidence":"; ".join(mv(s) for s in overlap),"ReviewType":"Source-informed provisional integration disposition; no physical qualification","SourceSHA":SHA})
 for f in source_files:
  rel=f.relative_to(DOM).as_posix()
  try:
   body=f.read_text(encoding="utf-8",errors="replace")
  except OSError:body=""
  doc=""; symbols=[]; imports=[]
  if f.suffix==".py" and len(body)<1500000:
   try:
    tree=ast.parse(body);doc=(ast.get_docstring(tree) or "").split("\n")[0][:170]
    symbols=[n.name for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))][:7]
    for n in tree.body:
     if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith(("openpilot","opendbc")):imports.append(n.module)
     if isinstance(n,ast.Import):
      imports += [a.name for a in n.names if a.name.startswith(("openpilot","opendbc"))]
   except SyntaxError:pass
  if not doc:doc="Filename represents source component; behavior requires targeted code review"
  components.append({"Family":name,"Component":f.stem,"Path":rel,"DescriptionFromModuleDocstring":doc,"TopSymbols":"; ".join(symbols),"Imports":"; ".join(imports[:14]),"ProposedDisposition":cfg[0],"Risk":cfg[4],"Evidence":src(rel),"ReviewStatus":"AST or source text inspected; not individually executed"})
def write(name,items):
 with (OUT/name).open("w",encoding="utf-8-sig",newline="") as fp:
  w=csv.DictWriter(fp,fieldnames=list(items[0]));w.writeheader();w.writerows(items)
write("feature_family_review.csv",catalog)
write("source_component_review.csv",components)
stats={"family_count":len(catalog),"source_components":len(components),"test_or_fixture_files":sum(int(r["TestOrFixtureFiles"]) for r in catalog),"unmapped_families":[r["Family"] for r in catalog if r["DomFeatureDecision"]=="MANUAL_REVIEW"],"decision_counts":dict(Counter(r["DomFeatureDecision"] for r in catalog))}
(OUT/"feature_catalog_summary.json").write_text(json.dumps(stats,indent=2),encoding="utf-8")
print(json.dumps(stats,indent=2))
