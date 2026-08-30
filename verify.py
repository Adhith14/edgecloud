# ============================================================
# verify.py — Cross-check every numeric claim in the paper
# ============================================================
# Prints each figure quoted in the paper alongside the section
# that cites it, so prose can be checked against source data.
#
# Run:  python verify.py
# ============================================================

import pandas as pd
import numpy as np

PV = "qwen2.5vl:3b"
HW_GBP, YRS, UTIL, WATT, KWH, FX = 3500.0, 3.0, 0.30, 170.0, 0.25, 1.27
_cap = (HW_GBP / YRS) / (365*24*3600*UTIL)
_pow = (WATT/1000) * KWH / 3600
LOCAL_PER_SEC = (_cap + _pow) * FX

runs = pd.read_csv("results/runs.csv", keep_default_na=False, na_values=[])
tasks = pd.read_csv("results/results.csv", keep_default_na=False, na_values=[])
for df in (runs, tasks):
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip()
for c in ["success_rate_pct","tasks_passed","tasks_escalated","total_system_cost_usd",
          "orchestration_cost_usd","eval_cost_usd","total_latency_s","total_data_kb",
          "tasks_retried","total_tool_calls","total_iterations"]:
    runs[c] = pd.to_numeric(runs[c], errors="coerce").fillna(0)
tasks["ok"] = tasks.success.astype(str).str.strip().isin(["True","true"])
tasks["cat"] = tasks.category.str[:1]

def cond(system, model=None, assign=None, vision=PV):
    s = runs[runs.system == system]
    if model:  s = s[s.model == model]
    if assign: s = s[s.model_assignment == assign]
    if vision and system != "cloud_only": s = s[s.vision_model == vision]
    if s.empty: return None
    hw = 0 if system == "cloud_only" else s.total_latency_s.mean() * LOCAL_PER_SEC
    return dict(
        n=len(s),
        succ=s.success_rate_pct.mean(), sd=s.success_rate_pct.std(),
        passed=s.tasks_passed.mean(), esc=s.tasks_escalated.mean(),
        api=s.total_system_cost_usd.mean(), evalc=s.eval_cost_usd.mean(),
        hw=hw, lat=s.total_latency_s.mean(), data=s.total_data_kb.mean(),
        retried=s.tasks_retried.mean(), tools=s.total_tool_calls.mean(),
    )

def hr(t): print(f"\n{'='*70}\n  {t}\n{'='*70}")

# ── ABSTRACT / RESULTS 4.1 ──────────────────────────────────
hr("SETUP  (§4.1)")
print(f"  conditions           : {runs.groupby(['system','model','model_assignment','vision_model']).ngroups}")
print(f"  total runs           : {len(runs)}")
print(f"  total evaluations    : {len(tasks)}")
print(f"  tasks per run        : {int(runs.tasks_total.iloc[0])}")

# ── RQ1 : SCALE ─────────────────────────────────────────────
hr("MODEL SCALE  (§4.2, Fig. scale)")
cloud = cond("cloud_only")
for m in ["qwen2.5:0.5b","qwen2.5:1.5b","qwen2.5:3b","qwen2.5:7b"]:
    c = cond("local_only", m)
    if c: print(f"  local_only {m:16} {c['succ']:5.1f} +/- {c['sd']:.1f}")
print(f"  cloud_only               {cloud['succ']:5.1f} +/- {cloud['sd']:.1f}")
c7 = cond("local_only","qwen2.5:7b")
print(f"\n  >> local 7B as % of frontier : {c7['succ']/cloud['succ']*100:.1f}%   [abstract, H1]")

hr("PER-CATEGORY, local_only  (§4.2, Fig. heat)")
t = tasks[(tasks.system=="local_only") & (tasks.vision_model==PV)]
piv = t.groupby(["model","cat"])["ok"].mean().mul(100).unstack()
for m in ["qwen2.5:0.5b","qwen2.5:1.5b","qwen2.5:3b","qwen2.5:7b"]:
    if m in piv.index:
        print(f"  {m:16} " + "  ".join(f"{c}:{piv.loc[m,c]:5.1f}" for c in piv.columns))
if "qwen2.5:0.5b" in piv.index and "qwen2.5:7b" in piv.index:
    print(f"\n  >> cat A  0.5B->7B : {piv.loc['qwen2.5:0.5b','A']:.0f} -> {piv.loc['qwen2.5:7b','A']:.0f}")
    print(f"  >> cat G  0.5B->7B : {piv.loc['qwen2.5:0.5b','G']:.0f} -> {piv.loc['qwen2.5:7b','G']:.0f}")

# ── MAIN TABLE ──────────────────────────────────────────────
hr("MAIN TABLE  (§4.3, Table main)")
rows = [("Cloud-only", cond("cloud_only")),
        ("Local-only v1", cond("local_only","qwen2.5:7b")),
        ("Hybrid v1", cond("hybrid","qwen2.5:7b")),
        ("Local-only v2", cond("v2_local","qwen2.5:7b","specialist")),
        ("Hybrid v2", cond("v2_hybrid","qwen2.5:7b","specialist"))]
print(f"  {'system':16}{'pass%':>14}{'esc':>7}{'API$':>10}{'lat_s':>8}{'KB':>7}")
for name, c in rows:
    if c: print(f"  {name:16}{c['succ']:8.1f}+/-{c['sd']:4.1f}{c['esc']:7.1f}"
                f"{c['api']:10.4f}{c['lat']:8.0f}{c['data']:7.1f}")

hv2 = cond("v2_hybrid","qwen2.5:7b","specialist")
print(f"\n  >> API cost reduction  : {(1-hv2['api']/cloud['api'])*100:.1f}%   [abstract: 92%]")
print(f"  >> data reduction      : {(1-hv2['data']/cloud['data'])*100:.1f}%   [abstract: 80%]")
print(f"  >> latency ratio       : {hv2['lat']/cloud['lat']:.1f}x")

# ── COST PER COMPLETED TASK ─────────────────────────────────
hr("COST PER COMPLETED TASK  (§4.3, H2)")
best = None
for sysname, model, assign in [("cloud_only",None,None),
                               ("local_only","qwen2.5:0.5b",None),
                               ("local_only","qwen2.5:3b",None),
                               ("local_only","qwen2.5:7b",None),
                               ("hybrid","qwen2.5:0.5b",None),
                               ("hybrid","qwen2.5:3b",None),
                               ("hybrid","qwen2.5:7b",None),
                               ("v2_local","qwen2.5:7b","specialist"),
                               ("v2_hybrid","qwen2.5:7b","specialist")]:
    c = cond(sysname, model, assign)
    if not c or c["passed"] == 0: continue
    api_pp = c["api"]/c["passed"]; tot_pp = (c["api"]+c["hw"])/c["passed"]
    print(f"  {sysname:11}{str(model or '-'):16} API ${api_pp:.6f}   +hw ${tot_pp:.6f}")
    if best is None or tot_pp < best[1]: best = (f"{sysname} {model}", tot_pp)
cl = cond("cloud_only")
cloud_pp = cl["api"]/cl["passed"]
print(f"\n  >> cheapest      : {best[0]}  ${best[1]:.6f}")
print(f"  >> cloud-only    : ${cloud_pp:.6f}")
print(f"  >> ratio         : {cloud_pp/best[1]:.1f}x   [paper: 6.6x]")

print(f"\n  Hybrid v2 7B with evaluation overhead included:")
print(f"    API ${hv2['api']:.5f} + eval ${hv2['evalc']:.5f} = ${hv2['api']+hv2['evalc']:.5f}")
print(f"    vs cloud ${cloud['api']:.5f}  ->  {cloud['api']/(hv2['api']+hv2['evalc']):.1f}x cheaper")

# ── LATENCY ─────────────────────────────────────────────────
hr("LATENCY PER TASK  (§4.3, RQ2)")
N = int(runs.tasks_total.iloc[0])
for name, c in rows:
    if c: print(f"  {name:16} {c['lat']/N:6.1f} s/task")

# ── RQ3 ─────────────────────────────────────────────────────
hr("ESCALATION AND RETRIES  (§4.4, RQ3)")
for m in ["qwen2.5:0.5b","qwen2.5:1.5b","qwen2.5:3b","qwen2.5:7b"]:
    c = cond("hybrid", m)
    if c: print(f"  hybrid v1 {m:16} escalated {c['esc']:5.1f} / {N}")
for sysname in ["v2_local","v2_hybrid"]:
    for m in ["qwen2.5:3b","qwen2.5:7b"]:
        c = cond(sysname, m, "specialist")
        if c: print(f"  {sysname:10} {m:16} retried {c['retried']:5.1f}  "
                    f"escalated {c['esc']:5.1f}  tools {c['tools']:5.1f}")

# ── H3 ──────────────────────────────────────────────────────
hr("H3 SPECIALIST vs SHARED  (§4.5, Fig. h3)")
t = tasks[tasks.system.isin(["v2_local","v2_hybrid"])]
piv = t.groupby(["cat","model_assignment"])["ok"].mean().mul(100).unstack()
if {"specialist","shared_generalist"} <= set(piv.columns):
    for c in piv.index:
        d = piv.loc[c,"specialist"] - piv.loc[c,"shared_generalist"]
        print(f"  cat {c}  specialist {piv.loc[c,'specialist']:5.1f}  "
              f"shared {piv.loc[c,'shared_generalist']:5.1f}  diff {d:+6.1f}")

# ── ABLATIONS ───────────────────────────────────────────────
hr("QUANTISATION  (§4.5)")
q4, q8 = cond("local_only","qwen2.5:7b"), cond("local_only","qwen2.5:7b-instruct-q8_0")
if q4 and q8:
    print(f"  q4  {q4['succ']:5.1f} +/- {q4['sd']:.1f}   latency {q4['lat']:.0f}s")
    print(f"  q8  {q8['succ']:5.1f} +/- {q8['sd']:.1f}   latency {q8['lat']:.0f}s")
    print(f"  >> latency penalty : {(q8['lat']/q4['lat']-1)*100:.0f}%   [paper: 49%]")

hr("VISION MODEL  (§4.5)")
vq = cond("local_only","qwen2.5:3b",vision=PV)
vl = cond("local_only","qwen2.5:3b",vision="llava:7b")
if vq and vl:
    print(f"  qwen2.5vl:3b  {vq['succ']:5.1f} +/- {vq['sd']:.1f}")
    print(f"  llava:7b      {vl['succ']:5.1f} +/- {vl['sd']:.1f}")
    print(f"  >> difference : {vq['succ']-vl['succ']:+.1f} pts   [paper: 14]")

hr("ARCHITECTURE v1 vs v2  (§4.5)")
for m in ["qwen2.5:3b","qwen2.5:7b"]:
    for a, b in [("local_only","v2_local"), ("hybrid","v2_hybrid")]:
        c1, c2 = cond(a,m), cond(b,m,"specialist")
        if c1 and c2:
            print(f"  {m:14} {a:11}{c1['succ']:6.1f}  ->  {b:10}{c2['succ']:6.1f}   "
                  f"({c2['succ']-c1['succ']:+.1f})")

hr("COMPOSITE TASKS, category H  (§4.5)")
h = tasks[tasks.cat == "H"]
for (s, a), g in h.groupby(["system","model_assignment"]):
    print(f"  {s:11} {a:18} {g.ok.mean()*100:5.1f}%   (n={len(g)})")
print()
for tid, g in h[h.system.str.startswith("v2")].groupby("task_id"):
    print(f"  {tid}  v2 only: {g.ok.mean()*100:5.1f}%")

print(f"\n{'='*70}\n  local compute cost: ${LOCAL_PER_SEC:.8f}/sec"
      f"  (GBP{HW_GBP:.0f}/{YRS:.0f}yr @ {UTIL*100:.0f}%)\n{'='*70}\n")