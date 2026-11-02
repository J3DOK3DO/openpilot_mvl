import csv, json, re, subprocess
from pathlib import Path
from collections import Counter,defaultdict
from urllib.parse import quote
D=Path(r"D:\Dom 7.0\StarPilot-Dom-Assessment-20261102")
M=Path(r"D:\Dom 7.0\MVL-StarPilot-SelectivePort-20261102")
O=Path(r"D:\Dom 7.0\_StarPilot_Assessment_20261102")
O.mkdir(exist_ok=True)
DS="cbd6e1eb52e8a46f9837a750d675b877d5ac8762"
MS="a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1"
EXT={".py",".pyx",".pyi",".h",".hpp",".c",".cpp",".cc",".qml",".qrc",".js",".jsx",".ts",".tsx",".vue",".go",".rs",".kt",".java",".swift",".sh",".ps1",".json",".toml",".yaml",".yml",".ini",".md",".txt",".xml",".html",".css",".proto",".capnp",".scons",".cfg"}
MATCH=re.compile(r"starpilot|starport|galaxy|lane.center|speed.limit|conditional.mode|always.on.lateral|smart.cruise|torque|alpha.long|mads|sentry|radar|model.manager|curve.speed|navigation|vehicle.interface|Honda",re.I)
PARAM=re.compile(r"\b(?:get_bool|get|put_bool|put|put_nonblocking)\s*\(\s*['\"]([A-Za-z][A-Za-z0-9_]{2,})['\"]")
def git(repo,*args):
 r=subprocess.run(["git","-C",str(repo)]+list(args),capture_output=True,text=True,encoding="utf-8",errors="replace")
 if r.returncode:raise RuntimeError(r.stderr[:700])
 return r.stdout.strip()
def tree(repo,sha):
 out={}
 for s in git(repo,"ls-tree","-r",sha).splitlines():
  a,p=s.split("\t",1);mode,typ,h=a.split();out[p]=(mode,typ,h)
 return out
DT=tree(D,DS);MT=tree(M,MS)
def family(p):
 s=p.split("/")
 if p.startswith("openpilot/starpilot/"):
  if s[2] in ("car","ui","system","galaxy","companion","models"):
   return "starpilot/"+s[2]+"/"+(s[3] if len(s)>3 else "_root")
  return "starpilot/"+s[2]
 if p.startswith("opendbc_repo/car/"):return "opendbc_car/"+(s[2] if len(s)>2 else "_root")
 if p.startswith("panda/"):return "panda/"+s[1]
 if p.startswith("openpilot/selfdrive/"):return "selfdrive/"+s[2]
 if p.startswith("openpilot/system/"):return "system/"+s[2]
 if p.startswith("openpilot/common/"):return "common/"+s[2]
 return "/".join(s[:2]) if len(s)>1 else s[0]
def decision(p,delta):
 if p.startswith(("opendbc_repo/car/honda/","panda/board/","openpilot/selfdrive/car/","openpilot/selfdrive/controls/","openpilot/selfdrive/monitoring/","openpilot/cereal/")):
  return "PROTECT_MVL_MANUAL_DIFF" if delta!="identical" else "KEEP_MVL"
 if p.startswith(("tinygrad_repo/","tinygrad_model_runtime/","sentry_sdk_repo/","rednose_repo/","teleoprtc_repo/","msgq_repo/","jetlink_repo/","mapd_repo/")):return "UPSTREAM_DEPENDENCY_PIN"
 if p.startswith("openpilot/starpilot/car/") and not p.startswith("openpilot/starpilot/car/honda/"):return "EXCLUDE_NON_HONDA_RUNTIME"
 if delta=="identical":return "KEEP_MVL_IDENTICAL"
 if "/tests/" in p or re.search(r"/test_[^/]+\.py$",p):return "PORT_TEST_ONLY_IF_OWNING_FEATURE"
 if "/assets/" in p or Path(p).suffix.lower() in (".png",".jpg",".jpeg",".svg",".ttf",".otf",".webp",".mp4",".bin"):return "BUNDLE_WITH_FEATURE"
 if p.startswith("openpilot/starpilot/"):return "CANDIDATE_SELECTIVE_PORT"
 if p.startswith(("openpilot/selfdrive/","openpilot/system/","openpilot/common/","system/","scripts/","selfdrive/","common/")):return "MVL_INTEGRATION_REVIEW"
 if p.startswith(("opendbc_repo/","panda/")):return "PROTECT_MVL_SAFETY_POLICY"
 return "REVIEW_BUILD_TOOLING_OR_CONTENT"
def url(p,repo,sha):return "https://github.com/"+repo+"/blob/"+sha+"/"+quote(p,safe="/")
cols=["Path","Family","Delta","Decision","DomBlobSHA","MVLBlobSHA","LocalTextInspected","Lines","EvidenceLines","ParamKeys","DomSource","MVLSource"]
rows=[];integration=[];params=[];protected=[];groups=defaultdict(list)
for p,(mode,typ,h) in sorted(DT.items()):
 delta="dom_only" if p not in MT else ("identical" if MT[p]==(mode,typ,h) else "modified_against_mvl")
 choice=decision(p,delta);f=family(p)
 inspected="no";n=0;evid=[];keys=[]
 q=D.joinpath(*p.split("/"))
 try:
  if q.is_file() and q.stat().st_size<1200000 and (q.suffix.lower() in EXT or q.name in ("SConstruct","Makefile","Dockerfile","README","launch")):
   lines=q.read_text(encoding="utf-8",errors="replace").splitlines();inspected="yes";n=len(lines)
   for i,line in enumerate(lines,1):
    if MATCH.search(line) and len(evid)<5:evid.append(str(i)+":"+line.strip()[:125])
    if "starpilot" in line.lower() and not p.startswith("openpilot/starpilot/") and len(integration)<25000:
     integration.append({"Path":p,"Line":i,"Text":line.strip()[:270],"Family":f,"Evidence":url(p,"StarPilotHQ/StarPilot",DS)+"#L"+str(i)})
    for key in PARAM.findall(line):
     if key not in keys:keys.append(key)
   for key in keys:params.append({"Path":p,"Key":key,"Family":f,"Evidence":url(p,"StarPilotHQ/StarPilot",DS)})
 except (OSError,UnicodeError):pass
 rec={"Path":p,"Family":f,"Delta":delta,"Decision":choice,"DomBlobSHA":h,"MVLBlobSHA":MT[p][2] if p in MT else "","LocalTextInspected":inspected,"Lines":n,"EvidenceLines":" || ".join(evid),"ParamKeys":";".join(keys),"DomSource":url(p,"StarPilotHQ/StarPilot",DS),"MVLSource":url(p,"mvl-boston/openpilot",MS) if p in MT else ""}
 rows.append(rec);groups[f].append(rec)
 if choice in ("PROTECT_MVL_MANUAL_DIFF","PROTECT_MVL_SAFETY_POLICY","MVL_INTEGRATION_REVIEW") and delta!="identical":protected.append(rec)
def save(name,items,head):
 with (O/name).open("w",encoding="utf-8-sig",newline="") as fp:
  writer=csv.DictWriter(fp,fieldnames=head,extrasaction="ignore");writer.writeheader();writer.writerows(items)
save("dom_full_file_disposition.csv",rows,cols)
save("mvl_only_files.csv",[{"Path":p,"MVLBlobSHA":v[2],"MVLSource":url(p,"mvl-boston/openpilot",MS)} for p,v in sorted(MT.items()) if p not in DT],["Path","MVLBlobSHA","MVLSource"])
save("runtime_starport_references.csv",integration,["Path","Line","Text","Family","Evidence"])
save("parameter_key_references.csv",params,["Path","Key","Family","Evidence"])
save("protected_runtime_differences.csv",protected,cols)
modules=[]
for f,items in sorted(groups.items()):
 cnt=Counter(t["Delta"] for t in items)
 examples=[r for r in items if r["LocalTextInspected"]=="yes" and r["Decision"] not in ("PORT_TEST_ONLY_IF_OWNING_FEATURE","BUNDLE_WITH_FEATURE")][:3] or items[:3]
 modules.append({"Family":f,"TotalFiles":len(items),"DomOnly":cnt["dom_only"],"Modified":cnt["modified_against_mvl"],"Identical":cnt["identical"],"TextInspected":sum(r["LocalTextInspected"]=="yes" for r in items),"RepresentativePaths":"; ".join(r["Path"] for r in examples),"EvidenceLinks":"; ".join(r["DomSource"] for r in examples),"DominantDecision":Counter(r["Decision"] for r in items).most_common(1)[0][0]})
save("dom_module_inventory.csv",modules,["Family","TotalFiles","DomOnly","Modified","Identical","TextInspected","RepresentativePaths","EvidenceLinks","DominantDecision"])
summary={"DomSHA":DS,"MVLSHA":MS,"DomTreeFiles":len(DT),"MVLTreeFiles":len(MT),"SourceTextInspected":sum(r["LocalTextInspected"]=="yes" for r in rows),"SourceTextNotInspected":sum(r["LocalTextInspected"]=="no" for r in rows),"ModuleFamilies":len(modules),"IntegrationReferenceRows":len(integration),"ParameterReferences":len(params),"ProtectedDifferences":len(protected),"MVLOnlyPaths":len(MT.keys()-DT.keys()),"DeltaCounts":dict(Counter(r["Delta"] for r in rows)),"DecisionCounts":dict(Counter(r["Decision"] for r in rows))}
(O/"manifest_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
lines=["# Complete static repository file reconciliation","",f"- Source Dom: {DS}",f"- Protected MVL: {MS}",f"- Dom file entries reconciled: {len(DT)}",f"- Source text locally examined: {summary['SourceTextInspected']}",f"- Files not text examined (binary, vendor omitted by sparse checkout, etc.): {summary['SourceTextNotInspected']}",f"- Family buckets: {len(modules)}",f"- Critical or runtime modified paths requiring review: {len(protected)}",f"- Referencing lines: {len(integration)}",f"- Parameter literal sightings: {len(params)}","","## Delta counts"]
for k,v in summary["DeltaCounts"].items():lines.append("- "+k+": "+str(v))
lines+=["","## Source-family counts",""]
for r in sorted(modules,key=lambda x:-x["TotalFiles"]):lines.append("- "+r["Family"]+": "+str(r["TotalFiles"])+" paths; inspected "+str(r["TextInspected"]))
lines+=["","## Caveat","Every Dom Git tree entry is accounted for at file level, but automated path classification is *not* a complete human code review or executable proof. Text inspection is explicitly marked. Vehicle-critical differences require independent review. Nothing is installed or transmitted to the vehicle."]
(O/"INVENTORY_COVERAGE.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print(json.dumps(summary,indent=2))
