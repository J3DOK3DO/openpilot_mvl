import csv,json,re,subprocess,datetime
from pathlib import Path
A=Path("/mnt/commadrive/MVL_STARPILOT_UBUNTU_REASSESSMENT_20261103")
D=Path("/mnt/commadrive/STARPILOT_DOM_SOURCEPIN_20261103")
M=Path("/mnt/commadrive/MVL_NATIVE_LATEST_20261103")
O=Path(__file__).resolve().parent
E=O/"evidence"
DONOR="10d170e799aa8d492a3f604ef8e91aafa3c11408"
MVL="376c44b5731b2655e5c2f301b73c9729eb499e91"
PRIOR="3924bd2e3917731e72012e784879262ca954c7ae"
tested_driving={"lateral":"latest_dom_selected_feature_pytest.log","curve_speed":"latest_dom_selected_feature_pytest.log","conditional_mode":"latest_dom_selected_feature_pytest.log","speed_limits":"latest_dom_selected_feature_pytest.log","flm":"latest_dom_selected_feature_pytest.log"}
tested_other={x:"latest_dom_nondriving_selected_pytest.log" for x in ("audio","models","sentry_mode","spot_monitor","validation","galaxy_bluetooth","bluetooth","navigation","software")}
tested_other["galaxy"]="latest_dom_selected_feature_pytest.log and latest_dom_nondriving_selected_pytest.log"
blocked={"ui":"raylib_nb missing in active Python environment","system":"StarPort test collection requires raylib_nb"}
mvl_baseline={"car","aol","controllers","longitudinal"}
high={"aol","car","conditional_mode","controllers","curve_speed","flm","lateral","longitudinal","speed_limits","models","power","software","system","connect"}
fpath=A/"docs/assessments/20261102/feature_family_review.csv"
with fpath.open(encoding="utf-8-sig",newline="") as fp: families=list(csv.DictReader(fp))
rows=[]
for r in families:
    name=r["Family"]
    if name in tested_driving|tested_other: status="SELECTED_DONOR_TESTS_PASS"; ev=(tested_driving|tested_other)[name]; caveat="Representative unit tests only; no MVL feature integration or hardware"
    elif name in blocked:status="HOST_DEPENDENCY_BLOCKED";ev="latest_dom_nondriving_selected_pytest.log";caveat=blocked[name]
    elif name in mvl_baseline:status="MVL_HOST_BASELINE_ONLY";ev="latest_mvl_native_combined_pytest.log";caveat="Existing MVL behavior tested, Dom port not executed"
    else:status="SOURCE_REVIEW_ONLY";ev="none";caveat="No executed feature-specific donor tests in this campaign"
    priority="P0" if name in ("aol","car","controllers","lateral","longitudinal","speed_limits","flm") else ("P1" if name in high else "P2")
    owner="Honda control owner + independent safety reviewer" if name in high else "MVL adapter/UI owner + security reviewer"
    rows.append({
       "Family":name,"OriginalDonorFamilyFiles":r["TotalFiles"],"OriginalDecision":r["DomFeatureDecision"],
       "Risk":r["Risk"],"UbuntuReviewStatus":status,"RepresentativeTestLog":ev,
       "RemainingEvidence":caveat,"MVLIntegrationOwner":r["MVLInterface"],
       "FutureAcceptance":r["SafetyOrSecurityAcceptance"],"Priority":priority,"ResponsibleRole":owner,
       "DonorEvidenceLatest":r["DomEvidence"].replace("cbd6e1eb52e8a46f9837a750d675b877d5ac8762",DONOR),
       "MVLEvidence":r["MVLEvidence"],"NoActuationUntilQualified":"YES"
    })
def save_csv(path,rows):
    with (O/path).open("w",encoding="utf-8-sig",newline="") as fp:
        writer=csv.DictWriter(fp,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
save_csv("feature_qualification_matrix_32.csv",rows)
def out(*cmd):
    p=subprocess.run(cmd,text=True,capture_output=True,check=True)
    return p.stdout.strip()
def diff_rows(repo,base,head,host):
    rows=[]
    for line in out("git","-C",str(repo),"diff","--name-status",base,head).splitlines():
        fields=line.split("\t")
        status,path=fields[0],fields[-1]
        if host=="mvl" and path.startswith("docs/"): continue
        for label,ref in (("old",base),("new",head)):
            try:sha=out("git","-C",str(repo),"rev-parse",f"{ref}:{path}")
            except subprocess.CalledProcessError:sha=""
            if label=="old":old=sha
            else:new=sha
        rows.append({"Repository":host,"Change":status,"Path":path,"OldRevision":base,"NewRevision":head,"OldBlobSHA":old,"NewBlobSHA":new,
                     "EvidenceURL":f"https://github.com/{'StarPilotHQ/StarPilot' if host=='dom' else 'mvl-boston/openpilot'}/blob/{head}/{path}",
                     "ReleaseDisposition":"REVIEW_CHANGED_FEATURE_HOOK" if path.endswith((".py",".cpp",".h")) else "REVIEW_ASSET_OR_BUILD_METADATA"})
    return rows
dom=diff_rows(D,PRIOR,DONOR,"dom")
mvl=diff_rows(A,"HEAD","refs/remotes/audit/mvl-latest","mvl")
deltas=dom+mvl
save_csv("pinned_source_changes_since_prior_review.csv",deltas)
def metrics(name):
    txt=(E/name).read_text(encoding="utf-8",errors="replace")
    m=re.findall(r"(\d+) passed(?:, (\d+) skipped)?",txt)
    return [int(x or 0) for x in m[-1]] if m else None
met={
 "donor_latest":DONOR,"mvl_latest":MVL,
 "original_branch":"7607cf9aa6664f4a31ff611613152c7bc87c6218",
 "dom_latest_delta_paths":len(dom),"mvl_non_docs_delta_paths":len(mvl),
 "families_total":len(rows),
 "families_representative_donor_tested":sum(x["UbuntuReviewStatus"]=="SELECTED_DONOR_TESTS_PASS" for x in rows),
 "mvl_latest_native_regressions":metrics("latest_mvl_native_combined_pytest.log"),
 "dom_selected_driving_feature_tests":metrics("latest_dom_selected_feature_pytest.log"),
 "dom_selected_nondriving_feature_tests":metrics("latest_dom_nondriving_selected_pytest.log"),
 "donor_static":json.loads((O/"static_validation_20261103.json").read_text()),
 "modelreview_codex":"completed, deployment HOLD; source risks identified",
 "modelreview_qwen":"completed direct Ollama Qwen3:8b advisory only; OpenCode stalled",
 "native_arm64_agnos":"NOT_RUN","panda_hardware":"NOT_RUN","on_vehicle_test":"NOT_RUN",
 "car_code_modified":False,"panda_code_modified":False,
}
(O/"qualification_evidence_summary.json").write_text(json.dumps(met,indent=2)+"\n",encoding="utf-8")
print(json.dumps(met,indent=2))
