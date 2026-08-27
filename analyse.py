# ============================================================
# analyse.py — Results Analysis and Figure Generation
# ============================================================
# Produces every figure and table for the paper and supporting
# report from results/runs.csv and results/results.csv.
#
# Runs are grouped by (system, model, model_assignment, vision_model)
# so that conditions differing in only one variable stay separable.
#
# Run:  python analyse.py
# Output: figures/*.png, tables/*.csv, printed summaries
# ============================================================

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIGDIR, TABDIR = "figures", "tables"
os.makedirs(FIGDIR, exist_ok=True)
os.makedirs(TABDIR, exist_ok=True)

PRIMARY_VISION = "qwen2.5vl:3b"

MODEL_PARAMS = {
    "qwen2.5:0.5b": 0.5, "qwen2.5:1.5b": 1.5,
    "qwen2.5:3b": 3.0, "qwen2.5:7b": 7.0,
}
SHORT = lambda m: str(m).replace("qwen2.5:", "").replace("-instruct", "").replace("qwen2.5-", "")

CAT_NAMES = {
    "A": "File/Log", "B": "Code", "C": "Planning", "D": "Document",
    "E": "Multimodal", "F": "Ambiguous", "G": "Complex", "H": "Chained",
}

plt.rcParams.update({
    "figure.dpi": 160, "font.size": 9, "axes.grid": True, "grid.alpha": 0.25,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "DejaVu Sans",
})

C_LOCAL, C_HYB, C_CLOUD = "#C0392B", "#1E8449", "#2E75B6"
C_V2L, C_V2H, C_ACCENT = "#7D3C98", "#117A8B", "#E67E22"


# ── LOADING ─────────────────────────────────────────────────
def load():
    runs = pd.read_csv("results/runs.csv")
    tasks = pd.read_csv("results/results.csv")
    for df in (runs, tasks):
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].astype(str).str.strip()
    for df in (runs, tasks):
        if "model_assignment" not in df.columns:
            df["model_assignment"] = "n/a"
        if "vision_model" not in df.columns:
            df["vision_model"] = PRIMARY_VISION
        # Empty fields read as NaN, and pandas silently drops NaN rows
        # when grouping — which would empty every aggregated figure.
        df["model_assignment"] = df["model_assignment"].fillna("n/a").replace("", "n/a")
        df["vision_model"] = df["vision_model"].fillna(PRIMARY_VISION).replace("", PRIMARY_VISION)
    tasks["ok"] = tasks["success"].astype(str).str.strip().isin(["True", "true"])
    tasks["cat"] = tasks["category"].str[:1]
    return runs, tasks


def agg(runs):
    """Mean and sd per experimental condition."""
    g = runs.groupby(["system", "model", "model_assignment", "vision_model"]).agg(
        n=("success_rate_pct", "size"),
        succ=("success_rate_pct", "mean"), succ_sd=("success_rate_pct", "std"),
        passed=("tasks_passed", "mean"),
        esc=("tasks_escalated", "mean"), esc_sd=("tasks_escalated", "std"),
        cost=("total_system_cost_usd", "mean"), cost_sd=("total_system_cost_usd", "std"),
        orch=("orchestration_cost_usd", "mean"),
        evalcost=("eval_cost_usd", "mean"),
        lat=("total_latency_s", "mean"), lat_sd=("total_latency_s", "std"),
        data=("total_data_kb", "mean"),
        iters=("total_iterations", "mean"),
        retried=("tasks_retried", "mean"),
        tools=("total_tool_calls", "mean"),
    ).reset_index().fillna(0)

    # Cost per COMPLETED task — Jonny asked for this specifically
    g["cost_per_pass"] = g.apply(
        lambda r: r["cost"] / r["passed"] if r["passed"] > 0 else np.nan, axis=1)
    g["lat_per_task"] = g["lat"] / 44.0
    return g


def prim(a):
    """Conditions using the primary vision model, plus cloud."""
    return a[(a.vision_model == PRIMARY_VISION) | (a.system == "cloud_only")]


def v1(a):
    return prim(a)[prim(a).system.isin(["local_only", "hybrid"])]


# ════════════════════════════════════════════════════════════
# FIG 1 — Accuracy vs model size  (RQ1, Barry's ablation)
# ════════════════════════════════════════════════════════════
def fig1_scale(a):
    p = prim(a)
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    for sysname, colour, marker, lbl in [
        ("local_only", C_LOCAL, "o", "Local-only (v1)"),
        ("hybrid", C_HYB, "s", "Hybrid (v1)"),
    ]:
        s = p[(p.system == sysname) & (p.model.isin(MODEL_PARAMS))].copy()
        if s.empty: continue
        s["x"] = s.model.map(MODEL_PARAMS)
        s = s.sort_values("x")
        ax.errorbar(s.x, s.succ, yerr=s.succ_sd, marker=marker, color=colour,
                    lw=2, capsize=3, ms=5, label=lbl)

    for sysname, colour, marker, lbl in [
        ("v2_local", C_V2L, "^", "Local-only (v2)"),
        ("v2_hybrid", C_V2H, "D", "Hybrid (v2)"),
    ]:
        s = p[(p.system == sysname) & (p.model_assignment == "specialist")
              & (p.model.isin(MODEL_PARAMS))].copy()
        if s.empty: continue
        s["x"] = s.model.map(MODEL_PARAMS)
        s = s.sort_values("x")
        ax.errorbar(s.x, s.succ, yerr=s.succ_sd, marker=marker, color=colour,
                    lw=2, capsize=3, ms=5, ls="--", label=lbl)

    c = p[p.system == "cloud_only"]
    if not c.empty:
        ax.axhline(c.succ.iloc[0], ls=":", color=C_CLOUD, lw=1.8,
                   label=f"Cloud-only ({c.succ.iloc[0]:.1f}%)")

    ax.set_xlabel("Local model size (billion parameters)")
    ax.set_ylabel("Task success rate (%)")
    ax.set_title("Success rate vs local model scale (mean ± sd)")
    ax.set_ylim(45, 105)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig1_scale.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 2 — Cost vs accuracy  (Jonny: optimal per unit cost)
# ════════════════════════════════════════════════════════════
def fig2_cost_accuracy(a):
    p = prim(a)
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    styles = {
        "local_only": (C_LOCAL, "o", "Local-only (v1)"),
        "hybrid": (C_HYB, "s", "Hybrid (v1)"),
        "v2_local": (C_V2L, "^", "Local-only (v2)"),
        "v2_hybrid": (C_V2H, "D", "Hybrid (v2)"),
        "cloud_only": (C_CLOUD, "*", "Cloud-only"),
    }
    for sysname, (colour, marker, lbl) in styles.items():
        s = p[p.system == sysname]
        if sysname.startswith("v2"):
            s = s[s.model_assignment == "specialist"]
        if s.empty: continue
        ax.errorbar(s.cost, s.succ, yerr=s.succ_sd, xerr=s.cost_sd,
                    fmt=marker, color=colour, ms=8 if marker == "*" else 6,
                    capsize=2, lw=1, label=lbl, zorder=3)
        for _, r in s.iterrows():
            ax.annotate(SHORT(r.model), (r.cost, r.succ), fontsize=6.5,
                        textcoords="offset points", xytext=(6, -4))

    ax.set_xscale("log")
    ax.set_xlabel("System cost per benchmark run (USD, log scale)")
    ax.set_ylabel("Task success rate (%)")
    ax.set_title("Cost–accuracy trade-off across all configurations")
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig2_cost_accuracy.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 3 — Cost per COMPLETED task  (Jonny's H2 framing)
# ════════════════════════════════════════════════════════════
def fig3_cost_per_pass(a):
    p = prim(a).copy()
    p = p[p.cost_per_pass.notna()]
    p = p[(p.model_assignment != "shared_generalist")]
    p["lbl"] = p.system.str.replace("_", "-") + "\n" + p.model.map(SHORT)
    p = p.sort_values("cost_per_pass")

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    colours = [C_CLOUD if s == "cloud_only" else
               C_HYB if s == "hybrid" else
               C_V2H if s == "v2_hybrid" else
               C_V2L if s == "v2_local" else C_LOCAL for s in p.system]
    bars = ax.bar(range(len(p)), p.cost_per_pass * 1000, color=colours)
    ax.set_xticks(range(len(p)))
    ax.set_xticklabels(p.lbl, fontsize=6, rotation=45, ha="right")
    ax.set_ylabel("Cost per completed task (USD × 10⁻³)")
    ax.set_title("Cost per successfully completed task")
    for b, v in zip(bars, p.cost_per_pass * 1000):
        ax.text(b.get_x() + b.get_width()/2, b.get_height(), f"{v:.2f}",
                ha="center", va="bottom", fontsize=6)
    ax.margins(y=0.16)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig3_cost_per_pass.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 4 — Five-system comparison at a fixed model
# ════════════════════════════════════════════════════════════
def fig4_systems(a, model="qwen2.5:7b"):
    p = prim(a)
    rows = []
    for sysname, lbl in [("local_only", "Local v1"), ("hybrid", "Hybrid v1"),
                         ("v2_local", "Local v2"), ("v2_hybrid", "Hybrid v2")]:
        s = p[(p.system == sysname) & (p.model == model)]
        if sysname.startswith("v2"):
            s = s[s.model_assignment == "specialist"]
        if not s.empty: rows.append((lbl, s.iloc[0]))
    c = p[p.system == "cloud_only"]
    if not c.empty: rows.append(("Cloud", c.iloc[0]))
    if not rows: return

    names = [n for n, _ in rows]
    cols = [C_LOCAL, C_HYB, C_V2L, C_V2H, C_CLOUD][:len(names)]

    fig, axes = plt.subplots(1, 4, figsize=(11, 3.0))
    specs = [("succ", "succ_sd", "Success rate (%)", "{:.1f}"),
             ("cost", "cost_sd", "System cost (USD)", "${:.4f}"),
             ("lat", "lat_sd", "Total latency (s)", "{:.0f}"),
             ("data", None, "Data to cloud (KB)", "{:.1f}")]
    for ax, (mc, sc, title, fmt) in zip(axes, specs):
        vals = [r[mc] for _, r in rows]
        errs = [r[sc] for _, r in rows] if sc else None
        bars = ax.bar(names, vals, yerr=errs, capsize=3, color=cols)
        ax.set_title(title, fontsize=9)
        ax.tick_params(axis="x", labelsize=7, rotation=30)
        for b, v in zip(bars, vals):
            ax.text(b.get_x()+b.get_width()/2, b.get_height(), fmt.format(v),
                    ha="center", va="bottom", fontsize=6.5)
        ax.margins(y=0.2)
    fig.suptitle(f"System comparison at {SHORT(model)} local model", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig4_systems.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 5 — Per-category heatmap  (Barry: per-category stats)
# ════════════════════════════════════════════════════════════
def fig5_heatmap(tasks):
    t = tasks[(tasks.system == "local_only") & (tasks.vision_model == PRIMARY_VISION)]
    if t.empty: return
    order = ["qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b",
             "qwen2.5:7b", "qwen2.5:7b-instruct-q8_0"]
    piv = (t.groupby(["model", "cat"])["ok"].mean().mul(100)
             .unstack().reindex([m for m in order if m in t.model.unique()]))
    if piv.empty: return

    fig, ax = plt.subplots(figsize=(6.8, 2.8))
    im = ax.imshow(piv.values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(piv.columns)))
    ax.set_xticklabels([f"{c}\n{CAT_NAMES.get(c,'')}" for c in piv.columns], fontsize=7)
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels([SHORT(m) for m in piv.index], fontsize=7.5)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7)
    ax.set_title("Local-only success rate (%) by task category", fontsize=9)
    ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.85, label="% passed")
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig5_heatmap.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 6 — H3: specialist vs shared, per category
# ════════════════════════════════════════════════════════════
def fig6_h3(tasks):
    t = tasks[(tasks.system == "v2_local") &
              (tasks.model_assignment.isin(["specialist", "shared_generalist"]))]
    if t.empty or t.model_assignment.nunique() < 2: return
    piv = t.groupby(["cat", "model_assignment"])["ok"].mean().mul(100).unstack()
    if "specialist" not in piv or "shared_generalist" not in piv: return
    diff = (piv["specialist"] - piv["shared_generalist"]).sort_index()

    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    colours = [C_HYB if d > 0 else (C_LOCAL if d < 0 else "#999999") for d in diff]
    bars = ax.bar([f"{c}\n{CAT_NAMES.get(c,'')}" for c in diff.index], diff.values,
                  color=colours)
    ax.axhline(0, color="black", lw=0.8)
    for b, v in zip(bars, diff.values):
        ax.text(b.get_x()+b.get_width()/2, v, f"{v:+.0f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=7)
    ax.set_ylabel("Specialist advantage (percentage points)")
    ax.set_title("H3: specialist routing vs shared generalist, by category", fontsize=9)
    ax.tick_params(axis="x", labelsize=7)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig6_h3.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 7 — Escalation and iteration behaviour  (RQ3)
# ════════════════════════════════════════════════════════════
def fig7_escalation(a):
    p = prim(a)
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2))

    s = p[(p.system == "hybrid") & (p.model.isin(MODEL_PARAMS))].copy()
    if not s.empty:
        s["x"] = s.model.map(MODEL_PARAMS); s = s.sort_values("x")
        bars = axes[0].bar([f"{x}B" for x in s.x], s.esc, yerr=s.esc_sd,
                           capsize=3, color=C_ACCENT)
        for b, v in zip(bars, s.esc):
            axes[0].text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.1f}",
                         ha="center", va="bottom", fontsize=7)
        axes[0].set_xlabel("Local model size")
        axes[0].set_ylabel("Tasks escalated (of 44)")
        axes[0].set_title("Escalation falls as local capability rises", fontsize=9)
        axes[0].margins(y=0.18)

    v = p[(p.system.isin(["v2_local", "v2_hybrid"])) &
          (p.model_assignment == "specialist")].copy()
    if not v.empty:
        v["lbl"] = v.system.str.replace("v2_", "v2 ") + "\n" + v.model.map(SHORT)
        x = np.arange(len(v)); w = 0.38
        axes[1].bar(x - w/2, v.retried, w, label="Retried locally", color=C_V2L)
        axes[1].bar(x + w/2, v.esc, w, label="Escalated to cloud", color=C_ACCENT)
        axes[1].set_xticks(x); axes[1].set_xticklabels(v.lbl, fontsize=6.5)
        axes[1].set_ylabel("Tasks (of 44)")
        axes[1].set_title("Local retries vs cloud escalations (v2)", fontsize=9)
        axes[1].legend(frameon=False, fontsize=7)
        axes[1].margins(y=0.18)

    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig7_escalation.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 8 — Quantisation and vision model
# ════════════════════════════════════════════════════════════
def fig8_quant_vision(a):
    p = prim(a)
    q4 = p[(p.system == "local_only") & (p.model == "qwen2.5:7b")]
    q8 = p[(p.system == "local_only") & (p.model == "qwen2.5:7b-instruct-q8_0")]
    vq = a[(a.system == "local_only") & (a.model == "qwen2.5:3b")
           & (a.vision_model == PRIMARY_VISION)]
    vl = a[(a.system == "local_only") & (a.model == "qwen2.5:3b")
           & (a.vision_model == "llava:7b")]

    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.0))

    if not q4.empty and not q8.empty:
        for ax, col, sd, title, fmt in [
            (axes[0], "succ", "succ_sd", "Quantisation: success (%)", "{:.1f}"),
            (axes[1], "lat", "lat_sd", "Quantisation: latency (s)", "{:.0f}")]:
            vals = [q4[col].iloc[0], q8[col].iloc[0]]
            errs = [q4[sd].iloc[0], q8[sd].iloc[0]]
            bars = ax.bar(["7B q4_K_M", "7B q8_0"], vals, yerr=errs, capsize=3,
                          color=[C_CLOUD, "#7030A0"])
            ax.set_title(title, fontsize=9); ax.margins(y=0.2)
            for b, v in zip(bars, vals):
                ax.text(b.get_x()+b.get_width()/2, b.get_height(), fmt.format(v),
                        ha="center", va="bottom", fontsize=7)

    if not vq.empty and not vl.empty:
        vals = [vq.succ.iloc[0], vl.succ.iloc[0]]
        bars = axes[2].bar(["Qwen2.5-VL 3B", "LLaVA 7B"], vals,
                           yerr=[vq.succ_sd.iloc[0], vl.succ_sd.iloc[0]],
                           capsize=3, color=[C_HYB, C_LOCAL])
        axes[2].set_title("Vision model: overall success (%)", fontsize=9)
        axes[2].margins(y=0.2)
        for b, v in zip(bars, vals):
            axes[2].text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.1f}",
                         ha="center", va="bottom", fontsize=7)

    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig8_quant_vision.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# TABLES
# ════════════════════════════════════════════════════════════
def tables(a, tasks):
    # Main results table
    t1 = a[["system", "model", "model_assignment", "n", "succ", "succ_sd", "esc",
            "cost", "cost_per_pass", "lat", "data", "retried", "tools"]].copy()
    t1.columns = ["System", "Model", "Assignment", "n", "Success%", "SD",
                  "Escalated", "Cost$", "Cost/pass$", "Latency_s", "Data_KB",
                  "Retried", "ToolCalls"]
    for c in ["Success%", "SD", "Escalated", "Latency_s", "Data_KB", "Retried", "ToolCalls"]:
        t1[c] = t1[c].round(2)
    t1["Cost$"] = t1["Cost$"].round(5)
    t1["Cost/pass$"] = t1["Cost/pass$"].round(5)
    t1.to_csv(f"{TABDIR}/table1_main_results.csv", index=False)

    # Per-category success for every condition
    t2 = (tasks.groupby(["system", "model", "model_assignment", "cat"])["ok"]
                .mean().mul(100).round(1).unstack())
    t2.to_csv(f"{TABDIR}/table2_per_category.csv")

    # Cost decomposition: system vs orchestration vs evaluation
    t3 = a[["system", "model", "model_assignment", "orch", "cost", "evalcost"]].copy()
    t3["task_cost"] = t3["cost"] - t3["orch"]
    t3.columns = ["System", "Model", "Assignment", "Orchestration$",
                  "TotalSystem$", "Evaluation$", "TaskExecution$"]
    t3.to_csv(f"{TABDIR}/table3_cost_breakdown.csv", index=False)
    return t1


# ════════════════════════════════════════════════════════════
def hypotheses(a, tasks):
    """Prints evidence for H1-H3 and the RQs."""
    p = prim(a)
    print("\n" + "="*78)
    print("  HYPOTHESIS EVIDENCE")
    print("="*78)

    cloud = p[p.system == "cloud_only"]
    if cloud.empty: return
    cloud = cloud.iloc[0]

    # H1
    print("\n  H1 — local completes 40-70% of frontier tasks")
    for sysname in ["local_only", "v2_local"]:
        s = p[p.system == sysname]
        if sysname.startswith("v2"): s = s[s.model_assignment == "specialist"]
        for _, r in s.sort_values("succ").iterrows():
            print(f"    {sysname:11} {SHORT(r.model):16} "
                  f"{r.succ:5.1f}%  = {r.succ/cloud.succ*100:5.1f}% of frontier")
    print(f"    cloud-only baseline: {cloud.succ:.1f}%")

    # H2
    print("\n  H2 — cost per completed task")
    for _, r in p.sort_values("cost_per_pass").iterrows():
        if pd.notna(r.cost_per_pass):
            print(f"    {r.system:11} {SHORT(r.model):16} {r.model_assignment:18} "
                  f"${r.cost_per_pass:.5f} per completed task")

    # H3
    print("\n  H3 — specialist vs shared generalist, per category")
    t = tasks[tasks.system.isin(["v2_local", "v2_hybrid"])]
    piv = t.groupby(["cat", "model_assignment"])["ok"].mean().mul(100).unstack()
    if "specialist" in piv and "shared_generalist" in piv:
        for c in piv.index:
            d = piv.loc[c, "specialist"] - piv.loc[c, "shared_generalist"]
            print(f"    {c} {CAT_NAMES.get(c,''):11} specialist {piv.loc[c,'specialist']:5.1f}%  "
                  f"shared {piv.loc[c,'shared_generalist']:5.1f}%  diff {d:+5.1f}")

    # Headline
    print("\n  HEADLINE COMPARISON")
    best = p[p.system.isin(["hybrid", "v2_hybrid"])].sort_values(
        ["succ", "cost"], ascending=[False, True])
    if not best.empty:
        b = best.iloc[0]
        print(f"    Best hybrid : {b.system} / {SHORT(b.model)} / {b.model_assignment}")
        print(f"      {b.succ:.1f}% success | ${b.cost:.5f} | {b.lat:.0f}s | {b.data:.2f} KB")
        print(f"    Cloud-only  : {cloud.succ:.1f}% | ${cloud.cost:.5f} | "
              f"{cloud.lat:.0f}s | {cloud.data:.2f} KB")
        print(f"      cost reduction {(1-b.cost/cloud.cost)*100:.1f}%  |  "
              f"data reduction {(1-b.data/cloud.data)*100:.1f}%")
    print("="*78 + "\n")


def main():
    runs, tasks = load()
    a = agg(runs)

    fig1_scale(a); fig2_cost_accuracy(a); fig3_cost_per_pass(a)
    fig4_systems(a); fig5_heatmap(tasks); fig6_h3(tasks)
    fig7_escalation(a); fig8_quant_vision(a)

    t1 = tables(a, tasks)
    print("\n=== MAIN RESULTS ===")
    print(t1.to_string(index=False))
    hypotheses(a, tasks)
    print(f"  Figures -> {FIGDIR}/   Tables -> {TABDIR}/\n")


if __name__ == "__main__":
    main()