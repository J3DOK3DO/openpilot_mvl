import ast,csv,hashlib,json,re
from pathlib import Path
from collections import Counter
D=Path(r"D:\Dom 7.0\StarPilot-Dom-Assessment-20261102")
M=Path(r"D:\Dom 7.0\MVL-StarPilot-SelectivePort-20261102")
H=Path(r"D:\Dom 7.0\MVL-Honda-Research-20261101\opendbc\car\honda")
OUT=Path(r"D:\Dom 7.0\_StarPilot_Assessment_20261102")
def parse_source(root):
 files=list(root.rglob("*.py"))
 good=[];errors=[]
 for f in files:
  if ".git" in f.parts:continue
  rel=f.relative_to(root).as_posix()
  try:
   src=f.read_text(encoding="utf-8")
   ast.parse(src,filename=rel,feature_version=None)
   good.append(rel)
  except (SyntaxError,UnicodeDecodeError,ValueError) as e:
   errors.append({"Path":rel,"Error":str(e)[:240]})
 return len(files),good,errors
dc,dg,de=parse_source(D/"openpilot")
mc,mg,me=parse_source(M/"openpilot")
def content(f):
 try:return f.read_bytes()
 except OSError:return None
cross=[]
for f in sorted((D/"opendbc_repo"/"opendbc"/"car"/"honda").glob("*.py")):
 p=H/f.name
 if not p.exists():status="DOM_ONLY_HONDA_FILE";other=""
 else:
  a=content(f);b=content(p);status="IDENTICAL" if a==b else "CONTENT_DIFF"
  other=str(p)
 cross.append({"File":f.name,"Comparison":status,"DomPath":str(f),"MVLPath":other,"Disposition":"RETAIN_MVL_DO_NOT_OVERWRITE","DomURL":"https://github.com/StarPilotHQ/StarPilot/blob/cbd6e1eb52e8a46f9837a750d675b877d5ac8762/opendbc_repo/opendbc/car/honda/"+f.name,"MVLURL":"https://github.com/mvl-boston/opendbc/blob/3fec9a418a659de31d7b1f494193161697a35071/opendbc/car/honda/"+f.name if p.exists() else ""})
def keys(root):
 vals={}
 pat=re.compile(r"\b(?:get_bool|get|put_bool|put)\s*\(\s*['\"]([A-Za-z][A-Za-z0-9_]{2,})['\"]")
 for f in root.rglob("*.py"):
  try:
   if f.stat().st_size>700000:continue
   txt=f.read_text(encoding="utf-8",errors="replace")
   for k in set(pat.findall(txt)): vals.setdefault(k,[]).append(str(f.relative_to(root)).replace("\\","/"))
  except OSError:pass
 return vals
dk=keys(D/"openpilot");mk=keys(M/"openpilot")
collisions=sorted(set(dk)&set(mk))
with (OUT/"honda_controller_crosswalk.csv").open("w",newline="",encoding="utf-8-sig") as f:
 w=csv.DictWriter(f,fieldnames=list(cross[0]));w.writeheader();w.writerows(cross)
with (OUT/"syntax_parse_errors.csv").open("w",newline="",encoding="utf-8-sig") as f:
 w=csv.DictWriter(f,fieldnames=["Source","Path","Error"]);w.writeheader()
 for r in de:w.writerow(dict(r,Source="DOM"))
 for r in me:w.writerow(dict(r,Source="MVL"))
with (OUT/"shared_parameter_literal_keys.csv").open("w",newline="",encoding="utf-8-sig") as f:
 w=csv.DictWriter(f,fieldnames=["Key","DomOccurrences","MVLOccurrences","DomExample","MVLExample"]);w.writeheader()
 for k in collisions:w.writerow({"Key":k,"DomOccurrences":len(dk[k]),"MVLOccurrences":len(mk[k]),"DomExample":dk[k][0],"MVLExample":mk[k][0]})
result={"Interpreter":"Python 3.13 expected; verify actual invocation separately","DomPythonFiles":dc,"DomParsed":len(dg),"DomSyntaxErrors":len(de),"MVLPythonFiles":mc,"MVLParsed":len(mg),"MVLSyntaxErrors":len(me),"HondaFilesCrosswalk":len(cross),"HondaContentDifferences":sum(r["Comparison"]=="CONTENT_DIFF" for r in cross),"DomOnlyHondaFiles":sum(r["Comparison"]=="DOM_ONLY_HONDA_FILE" for r in cross),"DomLiteralParams":len(dk),"MVLLiteralParams":len(mk),"SharedLiteralParams":len(collisions),"HostRuntime":"Windows source parse only, not AGNOS/panda/native build"}
(OUT/"static_validation_summary.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps(result,indent=2))
