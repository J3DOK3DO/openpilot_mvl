import ast, csv, json, os, pathlib, subprocess, sys
from collections import Counter
DONOR=pathlib.Path("/mnt/commadrive/STARPILOT_DOM_SOURCEPIN_20261103")
MVL=pathlib.Path("/mnt/commadrive/MVL_NATIVE_LATEST_20261103")
BASE=pathlib.Path(__file__).resolve().parent
EVIDENCE=BASE/"evidence"
EVIDENCE.mkdir(parents=True,exist_ok=True)
results={}
exceptions=[]
for name,src in (("DOM",DONOR),("MVL",MVL)):
    tracked=subprocess.run(["git","-C",str(src),"ls-files","-z"],capture_output=True,check=True).stdout.decode("utf-8","replace").split("\x00")
    py=[p for p in tracked if p.endswith(".py") and p and (src/p).is_file()]
    good=0
    for p in py:
        try:
            ast.parse((src/p).read_text(encoding="utf-8"),filename=p)
            good+=1
        except (UnicodeError,SyntaxError,ValueError,PermissionError) as e:
            exceptions.append({"Repo":name,"Path":p,"Category":"python_ast","Error":type(e).__name__+": "+str(e)[:250]})
    results[name]={"revision":subprocess.check_output(["git","-C",str(src),"rev-parse","HEAD"],text=True).strip(),"tracked_python":len(py),"ast_pass":good,"ast_exceptions":len(py)-good}
tracked=subprocess.run(["git","-C",str(DONOR),"ls-files","-z"],capture_output=True,check=True).stdout.decode("utf-8","replace").split("\x00")
js=[p for p in tracked if p.startswith("openpilot/starpilot/") and p.endswith((".js",".mjs")) and (DONOR/p).is_file() and "/vendor/" not in p]
good=0
for p in js:
    try:
        r=subprocess.run(["node","--check",str(DONOR/p)],capture_output=True,text=True,timeout=10)
        if r.returncode:exceptions.append({"Repo":"DOM","Path":p,"Category":"node_check","Error":r.stderr[-250:]})
        else:good+=1
    except (OSError,subprocess.TimeoutExpired) as e:
        exceptions.append({"Repo":"DOM","Path":p,"Category":"node_check","Error":str(e)[:250]})
results["DOM_js"]={"files":len(js),"passed":good,"errors":len(js)-good}
with (BASE/"static_check_exceptions.csv").open("w",newline="",encoding="utf-8") as fp:
    writer=csv.DictWriter(fp,fieldnames=["Repo","Path","Category","Error"]);writer.writeheader();writer.writerows(exceptions)
(BASE/"static_validation_20261103.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
print(json.dumps(results,indent=2))
print("EXCEPTIONS",exceptions[:12])
