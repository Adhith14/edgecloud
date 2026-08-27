# ============================================================
# analyse.py — Results Analysis and Figure Generation
# ============================================================
# Produces every figure and table for the paper and supporting
# report from results/runs.csv and results/results.csv.
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
N_TASKS = 44

# ════════════════════════════════════════════════════════════
# HARDWARE COST MODEL  —  ADJUST THESE TO YOUR REAL FIGURES
# ════════════════════════════════════════════════════════════
# Local inference is free at the API level but not free in reality.
# Amortising the workstation over its useful life gives a defensible
# cost per second of local compute, which is what H2 requires.
HW_PURCHASE_GBP    = 3500.0    # Dell Pro Max GB10 purchase price
HW_LIFETIME_YEARS  = 3.0       # depreciation period
HW_UTILISATION     = 0.30      # fraction of the year the machine does useful work
HW_POWER_W         = 170.0     # average draw under inference load
ELECTRICITY_GBP_KWH= 0.25      # UK commercial rate
GBP_TO_USD         = 1.27      # for comparison with API costs in USD

_secs_per_year = 365 * 24 * 3600 * HW_UTILISATION
_capital_per_s = (HW_PURCHASE_GBP / HW_LIFETIME_YEARS) / _secs_per_year
_power_per_s   = (HW_POWER_W / 1000.0) * ELECTRICITY_GBP_KWH / 3600.0
LOCAL_COST_PER_SEC_USD = (_capital_per_s + _power_per_s) * GBP_TO_USD

# ── LABELLING ───────────────────────────────────────────────
# Human-readable names so figures are self-explanatory to a reader
# who has not read the methodology section.
SYSTEM_LABELS = {
    "cloud_only": "Cloud-only (frontier LLM)",
    "local_only": "Local-only (v1, no tools)",
    "hybrid":     "Hybrid (v1, escalation)",
    "v2_local":   "Local-only (v2, tools + iteration)",
    "v2_hybrid":  "Hybrid (v2, tools + escalation)",
}
SYSTEM_SHORT = {
    "cloud_only": "Cloud", "local_only": "Local v1", "hybrid": "Hybrid v1",
    "v2_local": "Local v2", "v2_hybrid": "Hybrid v2",
}
ASSIGN_LABELS = {
    "specialist": "Specialist models per agent",
    "shared_generalist": "One shared generalist model",
    "n/a": "Single model (v1)",
}
CAT_NAMES = {
    "A": "File/Log", "B": "Code", "C": "Planning", "D": "Document",
    "E": "Multimodal", "F": "Ambiguous", "G": "Complex", "H": "Chained",
}
MODEL_PARAMS = {
    "qwen2.5:0.5b": 0.5, "qwen2.5:1.5b": 1.5,
    "qwen2.5:3b": 3.0, "qwen2.5:7b": 7.0,
}
MODEL_LABELS = {
    "qwen2.5:0.5b": "Qwen2.5 0.5B", "qwen2.5:1.5b": "Qwen2.5 1.5B",
    "qwen2.5:3b": "Qwen2.5 3B", "qwen2.5:7b": "Qwen2.5 7B (q4)",
    "qwen2.5:7b-instruct-q8_0": "Qwen2.5 7B (q8)",
    "llama3.2:3b": "Llama 3.2 3B", "gpt-4o-mini": "GPT-4o-mini",
    "n/a": "n/a",
}
LBL = lambda m: MODEL_LABELS.get(str(m), str(m))
SHORT = lambda m: str(m).replace("qwen2.5:", "").replace("-instruct", "").replace("qwen2.5-", "")

plt.rcParams.update({
    "figure.dpi": 160, "font.size": 9, "axes.grid": True, "grid.alpha": 0.25,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.family": "DejaVu Sans",
})
C = {"local_only": "#C0392B", "hybrid": "#1E8449", "cloud_only": "#2E75B6",
     "v2_local": "#7D3C98", "v2_hybrid": "#117A8B"}
C_ACCENT = "#E67E22"


# ── LOADING ─────────────────────────────────────────────────
def load():
    # keep_default_na=False stops pandas reading the literal string "n/a"
    # as NaN, which would silently drop every v1 row from any groupby.
    runs = pd.read_csv("results/runs.csv", keep_default_na=False, na_values=[])
    tasks = pd.read_csv("results/results.csv", keep_default_na=False, na_values=[])

    for df in (runs, tasks):
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].astype(str).str.strip()
        if "model_assignment" not in df.columns:
            df["model_assignment"] = "n/a"
        if "vision_model" not in df.columns:
            df["vision_model"] = PRIMARY_VISION
        df["model_assignment"] = df["model_assignment"].replace(["", "nan", "none"], "n/a")
        df["vision_model"] = df["vision_model"].replace(["", "nan"], PRIMARY_VISION)

    # Numeric coercion — keep_default_na=False leaves blanks as strings
    numcols_r = ["tasks_total", "tasks_passed", "success_rate_pct", "tasks_escalated",
                 "orchestration_tokens", "orchestration_cost_usd", "task_cost_usd",
                 "total_system_cost_usd", "eval_cost_usd", "total_latency_s",
                 "total_data_kb", "total_iterations", "tasks_retried", "total_tool_calls"]
    for c in numcols_r:
        if c in runs.columns:
            runs[c] = pd.to_numeric(runs[c], errors="coerce").fillna(0)
    for c in ["score", "latency_s", "cost_usd", "data_kb", "iterations_used"]:
        if c in tasks.columns:
            tasks[c] = pd.to_numeric(tasks[c], errors="coerce")

    tasks["ok"] = tasks["success"].astype(str).str.strip().isin(["True", "true"])
    tasks["cat"] = tasks["category"].str[:1]
    return runs, tasks


def agg(runs):
    """Mean and sd per experimental condition, plus derived cost measures."""
    g = runs.groupby(["system", "model", "model_assignment", "vision_model"]).agg(
        n=("success_rate_pct", "size"),
        succ=("success_rate_pct", "mean"), succ_sd=("success_rate_pct", "std"),
        passed=("tasks_passed", "mean"),
        esc=("tasks_escalated", "mean"), esc_sd=("tasks_escalated", "std"),
        api=("total_system_cost_usd", "mean"), api_sd=("total_system_cost_usd", "std"),
        orch=("orchestration_cost_usd", "mean"),
        evalcost=("eval_cost_usd", "mean"),
        lat=("total_latency_s", "mean"), lat_sd=("total_latency_s", "std"),
        data=("total_data_kb", "mean"),
        iters=("total_iterations", "mean"),
        retried=("tasks_retried", "mean"),
        tools=("total_tool_calls", "mean"),
    ).reset_index().fillna(0)

    # Hardware cost: local compute is charged by wall-clock time on the
    # amortised workstation. Cloud-only does no local inference.
    g["hw"] = np.where(g.system == "cloud_only", 0.0,
                       g.lat * LOCAL_COST_PER_SEC_USD)
    g["total"] = g.api + g.hw
    g["api_per_pass"]   = np.where(g.passed > 0, g.api / g.passed, np.nan)
    g["total_per_pass"] = np.where(g.passed > 0, g.total / g.passed, np.nan)
    g["lat_per_task"]   = g.lat / N_TASKS
    return g


def prim(a):
    return a[(a.vision_model == PRIMARY_VISION) | (a.system == "cloud_only")]


def spec(a):
    """Primary vision, and specialist assignment for v2 conditions."""
    p = prim(a)
    return p[~p.system.str.startswith("v2") | (p.model_assignment == "specialist")]


# ════════════════════════════════════════════════════════════
# FIG 1 — Accuracy vs model size (RQ1)
# ════════════════════════════════════════════════════════════
def fig1_scale(a):
    p = spec(a)
    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    for sysname, marker, ls in [("local_only", "o", "-"), ("hybrid", "s", "-"),
                                ("v2_local", "^", "--"), ("v2_hybrid", "D", "--")]:
        s = p[(p.system == sysname) & (p.model.isin(MODEL_PARAMS))].copy()
        if s.empty: continue
        s["x"] = s.model.map(MODEL_PARAMS); s = s.sort_values("x")
        ax.errorbar(s.x, s.succ, yerr=s.succ_sd, marker=marker, color=C[sysname],
                    lw=2, capsize=3, ms=5, ls=ls, label=SYSTEM_LABELS[sysname])

    c = p[p.system == "cloud_only"]
    if not c.empty:
        ax.axhline(c.succ.iloc[0], ls=":", color=C["cloud_only"], lw=1.8,
                   label=f"{SYSTEM_LABELS['cloud_only']} — {c.succ.iloc[0]:.1f}%")

    ax.set_xlabel("Local model size (billion parameters)")
    ax.set_ylabel("Benchmark tasks passed (%)")
    ax.set_title("Task success vs local model scale\n(44 tasks, mean ± sd over 3 runs)")
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig1_scale.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 2 — Cost vs accuracy (API cost only)
# ════════════════════════════════════════════════════════════
def fig2_cost_accuracy(a):
    p = spec(a)
    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    for sysname in ["local_only", "hybrid", "v2_local", "v2_hybrid", "cloud_only"]:
        s = p[p.system == sysname]
        if s.empty: continue
        marker = "*" if sysname == "cloud_only" else "o"
        ax.errorbar(s.api, s.succ, yerr=s.succ_sd, xerr=s.api_sd, fmt=marker,
                    color=C[sysname], ms=12 if marker == "*" else 6, capsize=2,
                    lw=1, label=SYSTEM_LABELS[sysname], zorder=3)
        for _, r in s.iterrows():
            ax.annotate(SHORT(r.model), (r.api, r.succ), fontsize=6.5,
                        textcoords="offset points", xytext=(6, -4))

    ax.set_xscale("log")
    ax.set_xlabel("Cloud API cost per 44-task benchmark run (USD, log scale)")
    ax.set_ylabel("Benchmark tasks passed (%)")
    ax.set_title("Cost–accuracy trade-off (API cost only)")
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig2_cost_accuracy.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 3 — Cost per completed task, API vs total (H2)
# ════════════════════════════════════════════════════════════
def fig3_cost_per_pass(a):
    p = spec(a).copy()
    p = p[p.api_per_pass.notna()].sort_values("total_per_pass")
    if p.empty: return
    p["lbl"] = p.system.map(SYSTEM_SHORT) + "\n" + p.model.map(SHORT)

    x = np.arange(len(p)); w = 0.38
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ax.bar(x - w/2, p.api_per_pass * 1000, w, label="Cloud API cost only",
           color="#2E75B6")
    ax.bar(x + w/2, p.total_per_pass * 1000, w,
           label="API + amortised local hardware", color=C_ACCENT)
    ax.set_xticks(x); ax.set_xticklabels(p.lbl, fontsize=6, rotation=45, ha="right")
    ax.set_ylabel("Cost per successfully completed task (USD $\\times 10^{-3}$)")
    ax.set_title("H2: cost per completed task, with and without hardware amortisation\n"
                 f"(hardware modelled at £{HW_PURCHASE_GBP:.0f} over "
                 f"{HW_LIFETIME_YEARS:.0f} years at {HW_UTILISATION*100:.0f}% utilisation)",
                 fontsize=9)
    ax.legend(frameon=False, fontsize=7.5)
    ax.margins(y=0.18)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig3_cost_per_pass.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 4 — Five-system comparison
# ════════════════════════════════════════════════════════════
def fig4_systems(a, model="qwen2.5:7b"):
    p = spec(a)
    rows = []
    for sysname in ["local_only", "hybrid", "v2_local", "v2_hybrid"]:
        s = p[(p.system == sysname) & (p.model == model)]
        if not s.empty: rows.append((SYSTEM_SHORT[sysname], sysname, s.iloc[0]))
    c = p[p.system == "cloud_only"]
    if not c.empty: rows.append((SYSTEM_SHORT["cloud_only"], "cloud_only", c.iloc[0]))
    if not rows: return

    names = [n for n, _, _ in rows]
    cols = [C[s] for _, s, _ in rows]

    fig, axes = plt.subplots(1, 5, figsize=(13.5, 3.4))
    specs = [("succ", "succ_sd", "Tasks passed (%)", "{:.1f}"),
             ("api", "api_sd", "Cloud API cost (USD)", "${:.4f}"),
             ("total", None, "API + hardware (USD)", "${:.4f}"),
             ("lat", "lat_sd", "Total latency (s)", "{:.0f}"),
             ("data", None, "Data sent to cloud (KB)", "{:.1f}")]
    for ax, (mc, sc, title, fmt) in zip(axes, specs):
        vals = [r[mc] for _, _, r in rows]
        errs = [r[sc] for _, _, r in rows] if sc else None
        bars = ax.bar(names, vals, yerr=errs, capsize=3, color=cols)
        ax.set_title(title, fontsize=9)
        ax.tick_params(axis="x", labelsize=7, rotation=35)
        for b, v in zip(bars, vals):
            ax.text(b.get_x()+b.get_width()/2, b.get_height(), fmt.format(v),
                    ha="center", va="bottom", fontsize=6.5)
        ax.margins(y=0.2)
    fig.suptitle(f"System comparison at {LBL(model)} local model "
                 f"(44 tasks, mean of 3 runs)", fontsize=10)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig4_systems.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 5 — Per-category heatmap
# ════════════════════════════════════════════════════════════
def fig5_heatmap(tasks):
    t = tasks[(tasks.system == "local_only") & (tasks.vision_model == PRIMARY_VISION)]
    if t.empty: return
    order = ["qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b",
             "qwen2.5:7b", "qwen2.5:7b-instruct-q8_0", "llama3.2:3b"]
    piv = (t.groupby(["model", "cat"])["ok"].mean().mul(100)
             .unstack().reindex([m for m in order if m in set(t.model)]))
    if piv.empty: return

    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    im = ax.imshow(piv.values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(piv.columns)))
    ax.set_xticklabels([f"{c}\n{CAT_NAMES.get(c,'')}" for c in piv.columns], fontsize=7)
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels([LBL(m) for m in piv.index], fontsize=7)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7)
    ax.set_title("Local-only (v1): tasks passed (%) by benchmark category", fontsize=9)
    ax.set_xlabel("Benchmark category"); ax.grid(False)
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
    if not {"specialist", "shared_generalist"} <= set(piv.columns): return
    diff = (piv["specialist"] - piv["shared_generalist"]).sort_index()

    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    colours = ["#1E8449" if d > 0 else ("#C0392B" if d < 0 else "#999999") for d in diff]
    bars = ax.bar([f"{c}\n{CAT_NAMES.get(c,'')}" for c in diff.index], diff.values,
                  color=colours)
    ax.axhline(0, color="black", lw=0.8)
    for b, v in zip(bars, diff.values):
        ax.text(b.get_x()+b.get_width()/2, v, f"{v:+.0f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=7)
    ax.set_ylabel("Percentage points\n(specialist − shared generalist)")
    ax.set_xlabel("Benchmark category")
    ax.set_title("H3: effect of specialist model routing, by category\n"
                 "Positive = specialist routing performs better", fontsize=9)
    ax.tick_params(axis="x", labelsize=7)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig6_h3.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 7 — Escalation and local iteration (RQ3)
# ════════════════════════════════════════════════════════════
def fig7_escalation(a):
    p = spec(a)
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.4))

    s = p[(p.system == "hybrid") & (p.model.isin(MODEL_PARAMS))].copy()
    if not s.empty:
        s["x"] = s.model.map(MODEL_PARAMS); s = s.sort_values("x")
        bars = axes[0].bar([f"{x}B" for x in s.x], s.esc, yerr=s.esc_sd,
                           capsize=3, color=C_ACCENT)
        for b, v in zip(bars, s.esc):
            axes[0].text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.1f}",
                         ha="center", va="bottom", fontsize=7)
        axes[0].set_xlabel("Local model size")
        axes[0].set_ylabel(f"Tasks escalated to cloud (of {N_TASKS})")
        axes[0].set_title("Hybrid v1: cloud escalations fall\nas local capability rises",
                          fontsize=9)
        axes[0].margins(y=0.18)

    v = p[p.system.isin(["v2_local", "v2_hybrid"])].copy()
    if not v.empty:
        v = v.sort_values(["system", "model"])
        v["lbl"] = v.system.map(SYSTEM_SHORT) + "\n" + v.model.map(SHORT)
        x = np.arange(len(v)); w = 0.38
        axes[1].bar(x - w/2, v.retried, w, label="Corrected locally (retry)",
                    color=C["v2_local"])
        axes[1].bar(x + w/2, v.esc, w, label="Escalated to cloud", color=C_ACCENT)
        axes[1].set_xticks(x); axes[1].set_xticklabels(v.lbl, fontsize=6.5)
        axes[1].set_ylabel(f"Tasks (of {N_TASKS})")
        axes[1].set_title("v2: local self-correction vs cloud escalation", fontsize=9)
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

    fig, axes = plt.subplots(1, 3, figsize=(10.0, 3.2))
    if not q4.empty and not q8.empty:
        for ax, col, sd, title, fmt in [
            (axes[0], "succ", "succ_sd", "Tasks passed (%)", "{:.1f}"),
            (axes[1], "lat", "lat_sd", "Total latency (s)", "{:.0f}")]:
            vals = [q4[col].iloc[0], q8[col].iloc[0]]
            errs = [q4[sd].iloc[0], q8[sd].iloc[0]]
            bars = ax.bar(["4-bit (q4_K_M)", "8-bit (q8_0)"], vals, yerr=errs,
                          capsize=3, color=["#2E75B6", "#7030A0"])
            ax.set_title(f"Quantisation at 7B — {title}", fontsize=8.5)
            ax.tick_params(axis="x", labelsize=7); ax.margins(y=0.2)
            for b, v in zip(bars, vals):
                ax.text(b.get_x()+b.get_width()/2, b.get_height(), fmt.format(v),
                        ha="center", va="bottom", fontsize=7)

    if not vq.empty and not vl.empty:
        vals = [vq.succ.iloc[0], vl.succ.iloc[0]]
        bars = axes[2].bar(["Qwen2.5-VL 3B", "LLaVA 7B"], vals,
                           yerr=[vq.succ_sd.iloc[0], vl.succ_sd.iloc[0]],
                           capsize=3, color=["#1E8449", "#C0392B"])
        axes[2].set_title("Local vision model — tasks passed (%)", fontsize=8.5)
        axes[2].tick_params(axis="x", labelsize=7); axes[2].margins(y=0.2)
        for b, v in zip(bars, vals):
            axes[2].text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.1f}",
                         ha="center", va="bottom", fontsize=7)

    fig.suptitle("Precision and vision-model ablations (local-only, mean of 3 runs)",
                 fontsize=9.5)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig8_quant_vision.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 9 — v1 vs v2 at matched model size (NEW)
# ════════════════════════════════════════════════════════════
def fig9_v1_vs_v2(a):
    p = spec(a)
    models = [m for m in ["qwen2.5:3b", "qwen2.5:7b"] if m in set(p.model)]
    if not models: return

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6))
    x = np.arange(len(models)); w = 0.35

    for ax, (m1, m2, title, ylab) in zip(axes, [
        ("local_only", "v2_local", "Local-only: effect of tools and iteration",
         "Tasks passed (%)"),
        ("hybrid", "v2_hybrid", "Hybrid: effect of tools and iteration",
         "Tasks passed (%)")]):
        v1 = [p[(p.system == m1) & (p.model == m)].succ.mean() for m in models]
        v2 = [p[(p.system == m2) & (p.model == m)].succ.mean() for m in models]
        e1 = [p[(p.system == m1) & (p.model == m)].succ_sd.mean() for m in models]
        e2 = [p[(p.system == m2) & (p.model == m)].succ_sd.mean() for m in models]
        b1 = ax.bar(x - w/2, v1, w, yerr=e1, capsize=3, color=C[m1],
                    label=SYSTEM_LABELS[m1])
        b2 = ax.bar(x + w/2, v2, w, yerr=e2, capsize=3, color=C[m2],
                    label=SYSTEM_LABELS[m2])
        for bars, vals in [(b1, v1), (b2, v2)]:
            for b, v in zip(bars, vals):
                if not np.isnan(v):
                    ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.1f}",
                            ha="center", va="bottom", fontsize=7)
        ax.set_xticks(x); ax.set_xticklabels([LBL(m) for m in models], fontsize=8)
        ax.set_ylabel(ylab); ax.set_title(title, fontsize=9)
        ax.legend(frameon=False, fontsize=6.5, loc="lower right")
        ax.margins(y=0.2)

    fig.suptitle("Architecture ablation: v1 (prompt-only) vs v2 (tool-using agents)",
                 fontsize=10)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig9_v1_vs_v2.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 10 — Latency vs accuracy (RQ2) (NEW)
# ════════════════════════════════════════════════════════════
def fig10_latency(a):
    p = spec(a)
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    for sysname in ["local_only", "hybrid", "v2_local", "v2_hybrid", "cloud_only"]:
        s = p[p.system == sysname]
        if s.empty: continue
        marker = "*" if sysname == "cloud_only" else "o"
        ax.errorbar(s.lat_per_task, s.succ, yerr=s.succ_sd, fmt=marker,
                    color=C[sysname], ms=12 if marker == "*" else 6,
                    capsize=2, lw=1, label=SYSTEM_LABELS[sysname], zorder=3)
        for _, r in s.iterrows():
            ax.annotate(SHORT(r.model), (r.lat_per_task, r.succ), fontsize=6.5,
                        textcoords="offset points", xytext=(6, -4))
    ax.set_xlabel("Mean latency per task (seconds)")
    ax.set_ylabel("Benchmark tasks passed (%)")
    ax.set_title("RQ2: latency–accuracy trade-off\n"
                 "Local execution trades response time for cost and privacy", fontsize=9)
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig10_latency.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# FIG 11 — Privacy: data egress (NEW)
# ════════════════════════════════════════════════════════════
def fig11_privacy(a):
    p = spec(a).copy()
    p = p.sort_values("data")
    if p.empty: return
    p["lbl"] = p.system.map(SYSTEM_SHORT) + " " + p.model.map(SHORT)

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    cols = [C[s] for s in p.system]
    bars = ax.barh(range(len(p)), p.data, color=cols)
    ax.set_yticks(range(len(p))); ax.set_yticklabels(p.lbl, fontsize=6.5)
    ax.set_xlabel("Data transmitted to cloud per benchmark run (KB)")
    ax.set_title("Privacy exposure: volume of data leaving the device\n"
                 "Zero indicates fully on-device execution", fontsize=9)
    for b, v in zip(bars, p.data):
        ax.text(b.get_width(), b.get_y()+b.get_height()/2, f" {v:.1f}",
                va="center", fontsize=6.5)
    ax.margins(x=0.12)
    fig.tight_layout(); fig.savefig(f"{FIGDIR}/fig11_privacy.png"); plt.close(fig)


# ════════════════════════════════════════════════════════════
# TABLES
# ════════════════════════════════════════════════════════════
def tables(a, tasks):
    t1 = a[["system", "model", "model_assignment", "n", "succ", "succ_sd", "esc",
            "api", "hw", "total", "api_per_pass", "total_per_pass",
            "lat", "data", "retried", "tools"]].copy()
    t1["system"] = t1.system.map(SYSTEM_LABELS).fillna(t1.system)
    t1["model"] = t1.model.map(LBL)
    t1["model_assignment"] = t1.model_assignment.map(ASSIGN_LABELS).fillna(t1.model_assignment)
    t1.columns = ["System", "Local model", "Model assignment", "Runs",
                  "Passed %", "SD", "Escalated", "API cost $", "Hardware $",
                  "Total $", "API $/pass", "Total $/pass",
                  "Latency s", "Data KB", "Retried", "Tool calls"]
    for c in ["Passed %", "SD", "Escalated", "Latency s", "Data KB", "Retried", "Tool calls"]:
        t1[c] = t1[c].round(2)
    for c in ["API cost $", "Hardware $", "Total $", "API $/pass", "Total $/pass"]:
        t1[c] = t1[c].round(6)
    t1.to_csv(f"{TABDIR}/table1_main_results.csv", index=False)

    t2 = (tasks.groupby(["system", "model", "model_assignment", "cat"])["ok"]
                .mean().mul(100).round(1).unstack())
    t2.to_csv(f"{TABDIR}/table2_per_category.csv")

    t3 = a[["system", "model", "model_assignment", "orch", "api",
            "hw", "total", "evalcost"]].copy()
    t3["task_exec"] = t3["api"] - t3["orch"]
    t3.columns = ["System", "Model", "Assignment", "Orchestration $", "API total $",
                  "Hardware $", "System total $", "Evaluation overhead $", "Task execution $"]
    t3.to_csv(f"{TABDIR}/table3_cost_breakdown.csv", index=False)

    # Benchmark composition, for the methodology section
    comp = (tasks[tasks.run_time == tasks.run_time.iloc[0]]
            .groupby("cat").size().reset_index())
    comp.columns = ["Category", "Tasks"]
    comp["Name"] = comp.Category.map(CAT_NAMES)
    comp[["Category", "Name", "Tasks"]].to_csv(f"{TABDIR}/table4_benchmark.csv", index=False)
    return t1


# ════════════════════════════════════════════════════════════
def hypotheses(a, tasks):
    p = spec(a)
    print("\n" + "="*82)
    print("  HYPOTHESIS EVIDENCE")
    print("="*82)
    print(f"\n  Local compute cost model: ${LOCAL_COST_PER_SEC_USD:.8f}/second")
    print(f"    (£{HW_PURCHASE_GBP:.0f} over {HW_LIFETIME_YEARS:.0f}y at "
          f"{HW_UTILISATION*100:.0f}% utilisation + {HW_POWER_W:.0f}W electricity)")

    cloud = p[p.system == "cloud_only"]
    if cloud.empty: return
    cloud = cloud.iloc[0]

    print(f"\n  H1 — local completes 40-70% of frontier tasks?")
    print(f"    Frontier baseline: {cloud.succ:.1f}%")
    for sysname in ["local_only", "v2_local"]:
        for _, r in p[p.system == sysname].sort_values("succ").iterrows():
            print(f"    {SYSTEM_SHORT[sysname]:9} {LBL(r.model):18} "
                  f"{r.succ:5.1f}%  = {r.succ/cloud.succ*100:5.1f}% of frontier")

    print(f"\n  H2 — cost per completed task")
    print(f"    {'condition':38} {'API only':>12} {'API+hardware':>14}")
    for _, r in p.sort_values("total_per_pass").iterrows():
        if pd.notna(r.total_per_pass):
            name = f"{SYSTEM_SHORT[r.system]} {SHORT(r.model)}"
            print(f"    {name:38} ${r.api_per_pass:10.6f} ${r.total_per_pass:12.6f}")

    print(f"\n  H3 — specialist vs shared generalist (v2, per category)")
    t = tasks[tasks.system.isin(["v2_local", "v2_hybrid"])]
    piv = t.groupby(["cat", "model_assignment"])["ok"].mean().mul(100).unstack()
    if {"specialist", "shared_generalist"} <= set(piv.columns):
        for c in piv.index:
            d = piv.loc[c, "specialist"] - piv.loc[c, "shared_generalist"]
            print(f"    {c} {CAT_NAMES.get(c,''):11} specialist {piv.loc[c,'specialist']:5.1f}%"
                  f"   shared {piv.loc[c,'shared_generalist']:5.1f}%   diff {d:+6.1f}")

    print(f"\n  ARCHITECTURE ABLATION (v1 vs v2, matched model)")
    for m in ["qwen2.5:3b", "qwen2.5:7b"]:
        for m1, m2 in [("local_only", "v2_local"), ("hybrid", "v2_hybrid")]:
            s1 = p[(p.system == m1) & (p.model == m)]
            s2 = p[(p.system == m2) & (p.model == m)]
            if not s1.empty and not s2.empty:
                print(f"    {LBL(m):18} {SYSTEM_SHORT[m1]:9} {s1.succ.iloc[0]:5.1f}%  ->  "
                      f"{SYSTEM_SHORT[m2]:9} {s2.succ.iloc[0]:5.1f}%   "
                      f"({s2.succ.iloc[0]-s1.succ.iloc[0]:+.1f} pts)")

    print(f"\n  HEADLINE")
    best = p[p.system.isin(["hybrid", "v2_hybrid"])].sort_values(
        ["succ", "api"], ascending=[False, True])
    if not best.empty:
        b = best.iloc[0]
        print(f"    Best hybrid: {SYSTEM_LABELS[b.system]}, {LBL(b.model)}")
        print(f"      {b.succ:.1f}% passed | API ${b.api:.5f} | +hw ${b.total:.5f} | "
              f"{b.lat:.0f}s | {b.data:.2f} KB")
        print(f"    Cloud-only: {cloud.succ:.1f}% passed | ${cloud.api:.5f} | "
              f"{cloud.lat:.0f}s | {cloud.data:.2f} KB")
        print(f"      API cost reduction  : {(1-b.api/cloud.api)*100:.1f}%")
        print(f"      Total cost reduction: {(1-b.total/cloud.api)*100:.1f}%  (incl. hardware)")
        print(f"      Data egress reduction: {(1-b.data/cloud.data)*100:.1f}%")
    print("="*82 + "\n")


def main():
    runs, tasks = load()
    a = agg(runs)
    fig1_scale(a); fig2_cost_accuracy(a); fig3_cost_per_pass(a)
    fig4_systems(a); fig5_heatmap(tasks); fig6_h3(tasks)
    fig7_escalation(a); fig8_quant_vision(a); fig9_v1_vs_v2(a)
    fig10_latency(a); fig11_privacy(a)
    t1 = tables(a, tasks)
    print("\n=== MAIN RESULTS ===")
    print(t1.to_string(index=False))
    hypotheses(a, tasks)
    print(f"  Figures -> {FIGDIR}/   Tables -> {TABDIR}/\n")


if __name__ == "__main__":
    main()