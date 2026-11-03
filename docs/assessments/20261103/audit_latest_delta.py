import ast,csv,json,re,subprocess,os
from pathlib import Path
from collections import Counter
OUT=Path(r"D:\Dom 7.0\_StarPilot_Assessment_20261103")
DOM=Path(r"D:\Dom 7.0\StarPilot-Dom-Assessment-20261102")
MVL=Path(r"D:\Dom 7.0\MVL-StarPilot-SelectivePort-20261102")
D0="cbd6e1eb52e8a46f9837a750d675b877d5ac8762"
D1="3924bd2e3917731e72012e784879262ca954c7ae"
M0="a969e5e60debe4d7d5f5f6ec2935f5a97f2bd0d1"
M1="376c44b5731b2655e5c2f301b73c9729eb499e91"
SUF={".py",".h",".c",".cpp",".cc",".hpp",".ts",".tsx",".js",".vue",".kt",".swift",".capnp",".sh"}
def git(repo,*args):
 p=subprocess.run(["git","-C",str(repo),*args],capture_output=True,env=dict(os.environ,GIT_NO_LAZY_FETCH="1"))
 return p.stdout if p.returncode==0 else None
def trees(repo,ref):
 b=git(repo,"ls-tree","-r","--full-tree",ref); t={}
 if b is None:raise Exception("missing source tree "+ref)
 for x in b.decode("utf8","replace").splitlines():
  if "\t" not in x:continue
  meta,name=x.split("\t",1); k=meta.split()
  if len(k)==3:t[name]=dict(zip(["mode","type","sha"],k))
 return t
def source(ref,p,repo="StarPilotHQ/StarPilot"):
 return "https://github.com/"+repo+"/blob/"+ref+"/"+p
def domain(p):
 s=p.split("/")
 if p.startswith("openpilot/starpilot/") and len(s)>2:return "starpilot/"+s[2]
 for prefix,label in [("opendbc_repo/","opendbc"),("panda/","panda"),("openpilot/selfdrive/ui/","native_ui"),("openpilot/selfdrive/controls/","controls"),("openpilot/cereal/","schemas"),("openpilot/system/","system"),("openpilot/","openpilot_core")]:
  if p.startswith(prefix):return label
 return s[0]
def policy(p):
 if re.search(r"/(hyundai|tesla|toyota|subaru|ford|gm|byd|volvo)/",p,re.I) and ("/car/" in p or "/safety/" in p):return "HIGH","EXCLUDE_OTHER_MAKE"
 if re.search(r"(safety/|/honda/|panda/|controlsd|carcontroller|carstate|carinterface|starpilot/(aol|flm|lateral|longitudinal|controllers|curve_speed|speed_limits)/|cereal/|manager/)",p,re.I):return "HIGH","PRESERVE_MVL_NO_AUTOMATIC_PORT"
 if re.search(r"(galaxy|connect|bluetooth|starport|jetlink|companion|sentry|models|software|web/)",p,re.I):return "HIGH","SECURITY_AND_BENCH_REVIEW"
 if re.search(r"(ui/|themes|layout|onroad|settings)",p,re.I):return "MEDIUM","VISUAL_ONLY_ADAPTER"
 if "test" in p:return "LOW","TEST_ADAPT_NOT_QUALIFICATION"
 return "MEDIUM","SOURCE_AND_DEPENDENCY_REVIEW"
def rows(name,rr):
 if not rr:return
 with (OUT/name).open("w",encoding="utf-8-sig",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
def txt(repo,ref,p):
 if repo==DOM and ref==D0 and (DOM/p).is_file():
  b=(DOM/p).read_bytes()
 else:
  b=git(repo,"show",ref+":"+p)
 if b is None or len(b)>250000 or b"\0" in b[:4096]:return None
 return b.decode("utf8","replace")
def top_symbols(t):
 if t is None:return [],"not inspected"
 try:a=ast.parse(t)
 except Exception as e:return [],str(e)
 return [n.name for n in a.body if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))],"OK"
OLD=trees(DOM,D0);NEW=trees(DOM,D1);OLDM=trees(MVL,M0);NEWM=trees(MVL,M1)
raw=git(DOM,"diff","--name-status","--no-renames",D0,D1).decode("utf8","replace")
changes=[]
for x in raw.splitlines():
 if "\t" not in x:continue
 status,path=x.split("\t",1)
 risk,decision=policy(path)
 changes.append({"Change":status,"Domain":domain(path),"Risk":risk,"Disposition":decision,"Path":path,"OldBlob":OLD.get(path,{}).get("sha",""),"NewBlob":NEW.get(path,{}).get("sha",""),"LatestURL":source(D1,path),"PreviousURL":source(D0,path) if path in OLD else "","Evidence":"exact Git tree and blob SHA; decision provisional"})
rows("latest_dom_delta_register.csv",changes)
mvlchanges=[]
for x in git(MVL,"diff","--name-status","--no-renames",M0,M1).decode("utf8","replace").splitlines():
 if "\t" not in x:continue
 status,path=x.split("\t",1)
 mvlchanges.append({"Change":status,"Path":path,"Risk":policy(path)[0],"URL":source(M1,path,"mvl-boston/openpilot"),"Disposition":"PRESERVE_UPSTREAM_MVL; fork not rebased"})
rows("latest_mvl_delta_register.csv",mvlchanges)
hits=[];syms=[];problems=[];examined=0
codepaths=[r for r in changes if Path(r["Path"]).suffix.lower() in SUF and (r["Path"].startswith("openpilot/") or "honda" in r["Path"].lower() or "/safety/" in r["Path"] or r["Path"].startswith("panda/"))]
trigger=re.compile(r"(starpilot|CarParams|carState|carControl|controlsd|params|safety|panda|longitudinal|steering|pubmaster|submaster|button|vCruise|FCW|AEB|CMBS|Ollama|galaxy|localhost|auth|session|CAN|modeld|AOL)",re.I)
for r in codepaths:
 p=r["Path"]
 new=txt(DOM,D1,p) if r["Change"]!="D" else None
 old=txt(DOM,D0,p) if r["Change"]!="A" else None
 if new is None and r["Change"]!="D":
  problems.append({"Path":p,"Problem":"text/blob unavailable or >250KB","Risk":r["Risk"],"URL":r["LatestURL"]});continue
 examined+=1
 for n,line in enumerate((new or "").splitlines(),1):
  if trigger.search(line) and not line.lstrip().startswith(("#","//","*")) and ("import" in line or "from " in line or "def " in line or "class " in line or "params" in line.lower() or "safety" in line.lower() or "carstate" in line.lower()):
   hits.append({"Domain":r["Domain"],"Path":p,"Line":n,"Risk":r["Risk"],"Reference":line.strip()[:190],"URL":r["LatestURL"]+"#L"+str(n),"Status":"textual hook candidate; not proven runtime"})
 if p.endswith(".py"):
  a,ae=top_symbols(new);b,be=top_symbols(old)
  if ae!="OK" and new is not None:problems.append({"Path":p,"Problem":"Python AST parse: "+ae,"Risk":r["Risk"],"URL":r["LatestURL"]})
  if set(a)!=set(b):
   syms.append({"Domain":r["Domain"],"Path":p,"Risk":r["Risk"],"AddedSymbols":"; ".join(sorted(set(a)-set(b)))[:1300],"RemovedSymbols":"; ".join(sorted(set(b)-set(a)))[:1300],"URL":r["LatestURL"],"Status":"top-level symbol delta; behavior unverified"})
rows("latest_runtime_hook_candidates.csv",hits)
rows("latest_python_symbol_delta.csv",syms)
rows("latest_source_text_exceptions.csv",problems)
def iscomponent(p):
 return p.startswith("openpilot/starpilot/") and Path(p).suffix.lower() in {".py",".cpp",".cc",".c",".h",".hpp",".kt",".swift",".ts",".tsx",".vue",".js",".sh"} and "/tests/" not in p and "/vendor/" not in p and "/node_modules/" not in p and not Path(p).name.startswith("test_")
prior={p for p in OLD if iscomponent(p)}
current={p for p in NEW if iscomponent(p)}
component_changes=[]
for typ,ps in (("added",current-prior),("removed",prior-current)):
 for p in sorted(ps):
  component_changes.append({"Type":typ,"Family":domain(p),"Path":p,"Risk":policy(p)[0],"Decision":policy(p)[1],"URL":source(D1 if typ=="added" else D0,p)})
rows("latest_first_party_component_delta.csv",component_changes)
f0=Counter(domain(x) for x in prior);f1=Counter(domain(x) for x in current)
rows("latest_first_party_family_counts.csv",[{"Family":k,"PriorSourceFiles":f0[k],"LatestSourceFiles":f1[k],"Difference":f1[k]-f0[k]} for k in sorted(f0.keys()|f1.keys())])
summary={"AssessmentDate":"2026-11-03","DonorOld":D0,"DonorLatest":D1,"MVLOld":M0,"MVLLatest":M1,"DonorFileCountPrior":len(OLD),"DonorFileCountLatest":len(NEW),"MVLFileCountPrior":len(OLDM),"MVLFileCountLatest":len(NEWM),"DomDeltaPaths":len(changes),"RiskHighChanged":sum(r["Risk"]=="HIGH" for r in changes),"StarpilotNamespaceChanged":sum(x["Path"].startswith("openpilot/starpilot/") for x in changes),"PriorFirstPartyCodeFiles":len(prior),"LatestFirstPartyCodeFiles":len(current),"AddedFirstPartyCodeFiles":len(current-prior),"RemovedFirstPartyCodeFiles":len(prior-current),"SourceFilesAttempted":len(codepaths),"TextInspectedLatestChanged":examined,"NotTextInspectedLatestChanged":len(codepaths)-examined,"TextHookCandidates":len(hits),"TopLevelSymbolChanges":len(syms),"ParseOrReadExceptions":len(problems),"MVLChangedPaths":len(mvlchanges),"AGNOSBuild":"NOT_RUN","IndependentReview":"PENDING","VehicleQualification":"NOT_RUN"}
(OUT/"latest_delta_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf8")
(OUT/"LATEST_DELTA_README.md").write_text("# Latest StarPilot:Dom to MVL static delta audit\n\n"+
 "\n".join("- "+str(k)+": "+str(v) for k,v in summary.items())+
 "\n\nDecisions are provisional. Hook candidates and symbol deltas are static evidence, not proof of actual invocation. This supplement must be read with pinned November 2 file-level inventory. Preserve MVL Bosch-C and Panda/host ownership, do not mass-merge or field-deploy.\n",encoding="utf8")
print(json.dumps(summary,indent=2))
