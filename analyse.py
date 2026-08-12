# ============================================================
# analyse.py — Results Analysis and Figure Generation
# ============================================================
# Aggregates repeated runs into mean +/- standard deviation and
# produces the figures for the paper.
#
# IMPORTANT: runs are grouped by (system, model, vision_model).
# The sweep runs local_only+qwen2.5:3b with more than one vision
# model, so grouping without vision_model mixes llava results
# into the qwen-vl rows and corrupts the size comparison.
#
# Run:  python analyse.py
# Output: figures/*.png  and printed summary tables
# ============================================================

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIGDIR = "figures"
os.makedirs(FIGDIR, exist_ok=True)

# The vision model used for all main comparisons. Runs using any other
# vision model are excluded from the size/cost/escalation figures and
# analysed separately in the vision comparison figure.
PRIMARY_VISION = "qwen2.5vl:3b"      # <-- set to your exact ollama tag

MODEL_PARAMS = {
    "qwen2.5:0.5b": 0.5,
    "qwen2.5:1.5b": 1.5,
    "qwen2.5:3b": 3.0,
    "qwen2.5:7b": 7.0,
}
MODEL_ORDER = [
    "qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b",
    "qwen2.5:7b", "qwen2.5:7b-instruct-q8_0", "llama3.2:3b",
]

plt.rcParams.update({
    "figure.dpi": 150, "font.size": 10,
    "axes.grid": True, "grid.alpha": 0.3,
    "axes.spines.top": False, "axes.spines.right": False,
})


# ── LOADING ─────────────────────────────────────────────────
def load():
    runs = pd.read_csv("results/runs.csv")
    tasks = pd.read_csv("results/results.csv")

    # Strip stray whitespace from string columns
    for df in (runs, tasks):
        for c in df.select_dtypes("object"):
            df[c] = df[c].astype(str).str.strip()

    # If the vision_model column is missing (older runs), assume primary
    if "vision_model" not in runs.columns:
        runs["vision_model"] = PRIMARY_VISION
    runs["vision_model"] = runs["vision_model"].fillna(PRIMARY_VISION)

    tasks = tasks[tasks["system"].isin(["local_only", "hybrid", "cloud_only"])]
    return runs, tasks


def agg(runs):
    """Collapse repeats into mean and sd per (system, model, vision_model)."""
    g = runs.groupby(["system", "model", "vision_model"]).agg(
        n=("success_rate_pct", "size"),
        succ_mean=("success_rate_pct", "mean"),
        succ_sd=("success_rate_pct", "std"),
        esc_mean=("tasks_escalated", "mean"),
        esc_sd=("tasks_escalated", "std"),
        cost_mean=("total_system_cost_usd", "mean"),
        cost_sd=("total_system_cost_usd", "std"),
        lat_mean=("total_latency_s", "mean"),
        lat_sd=("total_latency_s", "std"),
        data_mean=("total_data_kb", "mean"),
        evalcost_mean=("eval_cost_usd", "mean"),
    ).reset_index()
    return g.fillna(0)      # sd is NaN when a config has a single run


def primary(a):
    """Only configurations using the primary vision model (plus cloud-only)."""
    return a[(a.vision_model == PRIMARY_VISION) | (a.system == "cloud_only")]


# ── FIG 1: accuracy vs model size ───────────────────────────
def fig_accuracy_vs_size(a):
    p = primary(a)
    fig, ax = plt.subplots(figsize=(6.2, 4.2))

    for system, colour, marker in [("local_only", "#C0392B", "o"),
                                   ("hybrid", "#1E8449", "s")]:
        sub = p[(p.system == system) & (p.model.isin(MODEL_PARAMS))].copy()
        if sub.empty:
            continue
        sub["params"] = sub.model.map(MODEL_PARAMS)
        sub = sub.sort_values("params")
        ax.errorbar(sub.params, sub.succ_mean, yerr=sub.succ_sd,
                    marker=marker, color=colour, linewidth=2,
                    capsize=4, label=system.replace("_", "-"))

    c = p[p.system == "cloud_only"]
    if not c.empty:
        ax.axhline(c.succ_mean.iloc[0], linestyle="--", color="#2E75B6",
                   label=f"cloud-only ({c.succ_mean.iloc[0]:.1f}%)")

    ax.set_xlabel("Local model size (billion parameters)")
    ax.set_ylabel("Task success rate (%)")
    ax.set_title("Success rate vs local model size (mean ± sd, n=3)")
    ax.set_ylim(45, 105)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig1_accuracy_vs_size.png")
    plt.close(fig)


# ── FIG 2: cost vs accuracy ─────────────────────────────────
def fig_cost_vs_accuracy(a):
    p = primary(a)
    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    colours = {"local_only": "#C0392B", "hybrid": "#1E8449", "cloud_only": "#2E75B6"}

    for system in ["local_only", "hybrid", "cloud_only"]:
        sub = p[p.system == system]
        if sub.empty:
            continue
        ax.errorbar(sub.cost_mean, sub.succ_mean,
                    yerr=sub.succ_sd, xerr=sub.cost_sd,
                    fmt="o", ms=8, color=colours[system], capsize=3,
                    label=system.replace("_", "-"), zorder=3)
        for _, r in sub.iterrows():
            short = r.model.replace("qwen2.5:", "").replace("-instruct", "")
            ax.annotate(short, (r.cost_mean, r.succ_mean),
                        textcoords="offset points", xytext=(7, -4), fontsize=7.5)

    ax.set_xscale("log")
    ax.set_xlabel("System cost per benchmark run (USD, log scale)")
    ax.set_ylabel("Task success rate (%)")
    ax.set_title("Cost vs accuracy trade-off (mean ± sd, n=3)")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig2_cost_vs_accuracy.png")
    plt.close(fig)


# ── FIG 3: three-system comparison ──────────────────────────
def fig_system_comparison(a, model="qwen2.5:3b"):
    p = primary(a)
    rows = [
        ("local-only", p[(p.system == "local_only") & (p.model == model)]),
        ("hybrid",     p[(p.system == "hybrid") & (p.model == model)]),
        ("cloud-only", p[p.system == "cloud_only"]),
    ]
    rows = [(n, d) for n, d in rows if not d.empty]
    if not rows:
        return
    names = [n for n, _ in rows]
    colours = ["#C0392B", "#1E8449", "#2E75B6"][:len(names)]

    fig, axes = plt.subplots(1, 4, figsize=(12, 3.6))
    specs = [
        ("succ_mean", "succ_sd", "Success rate (%)", "{:.1f}"),
        ("cost_mean", "cost_sd", "System cost (USD)", "${:.4f}"),
        ("lat_mean",  "lat_sd",  "Latency (s)", "{:.0f}"),
        ("data_mean", None,      "Data to cloud (KB)", "{:.1f}"),
    ]
    for ax, (mcol, scol, title, fmt) in zip(axes, specs):
        vals = [d[mcol].iloc[0] for _, d in rows]
        errs = [d[scol].iloc[0] for _, d in rows] if scol else None
        bars = ax.bar(names, vals, yerr=errs, capsize=4, color=colours)
        ax.set_title(title, fontsize=10)
        ax.tick_params(axis="x", labelsize=8)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width()/2, b.get_height(),
                    fmt.format(v), ha="center", va="bottom", fontsize=8)
        ax.margins(y=0.2)

    fig.suptitle(f"Three-system comparison (local model: {model}, n=3)", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig3_system_comparison.png")
    plt.close(fig)


# ── FIG 4: escalations vs model size ────────────────────────
def fig_escalations(a):
    p = primary(a)
    sub = p[(p.system == "hybrid") & (p.model.isin(MODEL_PARAMS))].copy()
    if sub.empty:
        return
    sub["params"] = sub.model.map(MODEL_PARAMS)
    sub = sub.sort_values("params")

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar([f"{p_}b" for p_ in sub.params], sub.esc_mean,
                  yerr=sub.esc_sd, capsize=4, color="#E67E22")
    for b, v in zip(bars, sub.esc_mean):
        ax.text(b.get_x() + b.get_width()/2, b.get_height(), f"{v:.1f}",
                ha="center", va="bottom", fontsize=9)
    ax.set_xlabel("Local model size")
    ax.set_ylabel("Tasks escalated to cloud (of 35)")
    ax.set_title("Escalation frequency falls as local capability rises")
    ax.margins(y=0.2)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig4_escalations.png")
    plt.close(fig)


# ── FIG 5: per-category heatmap (local-only) ────────────────
def fig_category_heat(tasks):
    sub = tasks[tasks.system == "local_only"].copy()

    # Exclude non-primary vision runs if the column exists, so the
    # vision category is not contaminated by the llava comparison runs.
    if "vision_model" in sub.columns:
        sub = sub[sub.vision_model.fillna(PRIMARY_VISION) == PRIMARY_VISION]

    if sub.empty:
        return
    sub["cat"] = sub.category.str[:1]
    sub["ok"] = sub.success.astype(str).str.strip() == "True"

    pivot = (sub.groupby(["model", "cat"])["ok"].mean().mul(100)
                .unstack().reindex(MODEL_ORDER).dropna(how="all"))

    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(pivot.columns))); ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([m.replace("qwen2.5:", "").replace("-instruct", "")
                        for m in pivot.index], fontsize=8)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8)
    ax.set_title("Local-only success rate (%) by task category")
    ax.set_xlabel("Category"); ax.grid(False)
    fig.colorbar(im, ax=ax, shrink=0.8, label="% passed")
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig5_category_heatmap.png")
    plt.close(fig)


# ── FIG 6: quantization ─────────────────────────────────────
def fig_quantization(a):
    p = primary(a)
    q4 = p[(p.system == "local_only") & (p.model == "qwen2.5:7b")]
    q8 = p[(p.system == "local_only") & (p.model == "qwen2.5:7b-instruct-q8_0")]
    if q4.empty or q8.empty:
        return
    labels = ["7b q4_K_M", "7b q8_0"]

    fig, axes = plt.subplots(1, 2, figsize=(7, 3.6))
    for ax, mcol, scol, title, fmt in [
        (axes[0], "succ_mean", "succ_sd", "Success rate (%)", "{:.1f}"),
        (axes[1], "lat_mean",  "lat_sd",  "Total latency (s)", "{:.0f}"),
    ]:
        vals = [q4[mcol].iloc[0], q8[mcol].iloc[0]]
        errs = [q4[scol].iloc[0], q8[scol].iloc[0]]
        bars = ax.bar(labels, vals, yerr=errs, capsize=4, color=["#2E75B6", "#7030A0"])
        ax.set_title(title, fontsize=10); ax.margins(y=0.2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width()/2, b.get_height(), fmt.format(v),
                    ha="center", va="bottom", fontsize=9)

    lat_pct = (q8.lat_mean.iloc[0] / q4.lat_mean.iloc[0] - 1) * 100
    fig.suptitle(f"Quantization: q8 raises latency by {lat_pct:.0f}% "
                 f"with overlapping accuracy ranges", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig6_quantization.png")
    plt.close(fig)


# ── FIG 7: vision model comparison (NEW) ────────────────────
def fig_vision_comparison(a, tasks, text_model="qwen2.5:3b"):
    """Compares local vision models at a fixed text model."""
    sub = a[(a.system == "local_only") & (a.model == text_model)]
    if sub.vision_model.nunique() < 2:
        return

    sub = sub.sort_values("vision_model")
    labels = list(sub.vision_model)

    # Overall success plus vision-category-only success
    cat_e = None
    if "vision_model" in tasks.columns:
        t = tasks[(tasks.system == "local_only") & (tasks.model == text_model)].copy()
        t["ok"] = t.success.astype(str).str.strip() == "True"
        t = t[t.category.str[:1] == "E"]
        if not t.empty:
            cat_e = t.groupby("vision_model")["ok"].mean().mul(100).reindex(labels)

    ncols = 2 if cat_e is not None else 1
    fig, axes = plt.subplots(1, ncols, figsize=(4 + 3*ncols, 3.6))
    axes = [axes] if ncols == 1 else list(axes)

    bars = axes[0].bar(labels, sub.succ_mean, yerr=sub.succ_sd,
                       capsize=4, color=["#1E8449", "#C0392B"][:len(labels)])
    axes[0].set_title("Overall success rate (%)", fontsize=10)
    axes[0].tick_params(axis="x", labelsize=8)
    for b, v in zip(bars, sub.succ_mean):
        axes[0].text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.1f}",
                     ha="center", va="bottom", fontsize=9)
    axes[0].margins(y=0.2)

    if cat_e is not None:
        bars = axes[1].bar(labels, cat_e.values,
                           color=["#1E8449", "#C0392B"][:len(labels)])
        axes[1].set_title("Category E (vision) success rate (%)", fontsize=10)
        axes[1].tick_params(axis="x", labelsize=8)
        for b, v in zip(bars, cat_e.values):
            axes[1].text(b.get_x()+b.get_width()/2, b.get_height(), f"{v:.0f}",
                         ha="center", va="bottom", fontsize=9)
        axes[1].margins(y=0.2)

    fig.suptitle(f"Local vision model comparison (text model: {text_model})", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/fig7_vision_comparison.png")
    plt.close(fig)


# ── SUMMARY ─────────────────────────────────────────────────
def print_summary(a):
    df = a[["system", "model", "vision_model", "n", "succ_mean", "succ_sd",
            "esc_mean", "cost_mean", "lat_mean", "data_mean"]].copy()
    df.columns = ["system", "model", "vision", "n", "succ%", "sd",
                  "escal", "cost$", "latency_s", "data_kb"]
    for c in ["succ%", "sd", "escal", "latency_s", "data_kb"]:
        df[c] = df[c].round(2)
    df["cost$"] = df["cost$"].round(5)

    print("\n" + "="*112)
    print("  AGGREGATED RESULTS (mean of repeated runs)")
    print("="*112)
    print(df.to_string(index=False))

    p = primary(a)
    cloud = p[p.system == "cloud_only"]
    hyb = p[p.system == "hybrid"].sort_values(
        ["succ_mean", "cost_mean"], ascending=[False, True])
    if cloud.empty or hyb.empty:
        return
    cloud = cloud.iloc[0]; hyb = hyb.iloc[0]

    print(f"\n  Best hybrid config: {hyb.model}")
    print(f"    success {hyb.succ_mean:.1f}% (sd {hyb.succ_sd:.2f})  "
          f"cost ${hyb.cost_mean:.5f}  latency {hyb.lat_mean:.0f}s  "
          f"data {hyb.data_mean:.2f} KB  escalations {hyb.esc_mean:.1f}")
    print(f"  Cloud-only baseline:")
    print(f"    success {cloud.succ_mean:.1f}%  cost ${cloud.cost_mean:.5f}  "
          f"latency {cloud.lat_mean:.0f}s  data {cloud.data_mean:.2f} KB")
    print(f"\n    cost reduction : {(1 - hyb.cost_mean/cloud.cost_mean)*100:.1f}%")
    print(f"    data reduction : {(1 - hyb.data_mean/cloud.data_mean)*100:.1f}%")
    print("="*112 + "\n")


def main():
    runs, tasks = load()
    a = agg(runs)
    fig_accuracy_vs_size(a)
    fig_cost_vs_accuracy(a)
    fig_system_comparison(a)
    fig_escalations(a)
    fig_category_heat(tasks)
    fig_quantization(a)
    fig_vision_comparison(a, tasks)
    print_summary(a)
    print(f"  Figures written to {FIGDIR}/\n")


if __name__ == "__main__":
    main()