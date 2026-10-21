"""Phase 5 charts (matplotlib, PNG). Palette: reference categorical slots 1-3 (blue, orange, aqua), realised in ink; one axis per chart,
thin lines, recessive grid, direct end labels plus legend."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
C = {"A": "#2a78d6", "B": "#eb6834", "AR4": "#1baf7a", "AR1": "#8a8984"}
DRV = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#6250d6"]
EQC = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]


def _style(ax, title, ylabel):
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold")
    ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#bdbcb6")
    ax.tick_params(colors=MUTED, labelsize=8)


def _xticks(ax, idx):
    ax.set_xticks(range(len(idx)))
    ax.set_xticklabels([str(q) for q in idx], rotation=45, ha="right")


def actual_vs_forecast(real: pd.Series, fc: pd.DataFrame, hist: pd.Series, title: str, ylabel: str, path: Path, note: str = ""):
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150)
    idx = pd.PeriodIndex(list(hist.index) + list(real.index), freq="Q")
    h = len(hist)
    x_h, x_f = np.arange(h), np.arange(h, h + len(real))
    ax.plot(x_h, hist.values, color=INK, lw=1.6)
    ax.plot(np.r_[x_h[-1], x_f], np.r_[hist.values[-1], real.values], color=INK, lw=2.2, label="Realised")
    spec = [("A: pseudo-real-time", "A", "-"), ("B: conditional (realised drivers)", "B", "-"), ("AR(4)", "AR4", "--"), ("AR(1)", "AR1", ":")]
    for lab, k, ls in spec:
        if lab in fc:
            ax.plot(np.r_[x_h[-1], x_f], np.r_[hist.values[-1], fc[lab].values], color=C[k], lw=1.8, ls=ls, label=lab, marker="o" if k in "AB" else None, ms=3.5)
    ax.axvline(h - 0.5, color="#bdbcb6", lw=1, ls="--")
    ax.text(h - 0.4, ax.get_ylim()[1], " forecast origin 2023Q2", va="top", fontsize=8, color=MUTED)
    _style(ax, title, ylabel)
    _xticks(ax, idx)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    if note:
        fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def stacked_decomposition(parts: pd.DataFrame, total: pd.Series, title: str, ylabel: str, colors, path: Path, note: str = ""):
    fig, ax = plt.subplots(figsize=(9, 4.6), dpi=150)
    x = np.arange(len(parts))
    pos, neg = np.zeros(len(parts)), np.zeros(len(parts))
    for i, c in enumerate(parts.columns):
        v = parts[c].values
        b = np.where(v >= 0, pos, neg)
        ax.bar(x, v, bottom=b, color=colors[i], width=0.72, label=c, edgecolor="white", linewidth=1)
        pos, neg = pos + np.clip(v, 0, None), neg + np.clip(v, None, 0)
    ax.plot(x, total.values, color=INK, lw=1.6, marker="o", ms=4, label="Total")
    ax.axhline(0, color="#bdbcb6", lw=1)
    _style(ax, title, ylabel)
    _xticks(ax, parts.index)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    if note:
        fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(path)
    plt.close(fig)


def error_bars(err: pd.DataFrame, title: str, ylabel: str, path: Path):
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    x = np.arange(len(err))
    cols = list(err.columns)
    w = 0.8 / len(cols)
    colors = [C["A"], C["B"], C["AR4"], C["AR1"]]
    for i, c in enumerate(cols):
        ax.bar(x - 0.4 + w * (i + 0.5), err[c].values, width=w * 0.9, color=colors[i % 4], label=c)
    ax.axhline(0, color="#bdbcb6", lw=1)
    _style(ax, title, ylabel)
    _xticks(ax, err.index)
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def decomposition_panels(dec: pd.DataFrame, drv_cols: list[str], rel_cols: list[str], path: Path, note: str = ""):
    """Two panels sharing the quarters axis: (top) error from external assumptions, A - B, split by driver; (bottom) error from the estimated
    relationships, B - realised, split by equation. Each panel's black line is its total; the two totals add up to the Exercise A error."""
    fig, axes = plt.subplots(2, 1, figsize=(11, 7.4), dpi=150, sharex=True)
    x = np.arange(len(dec))
    for ax, cols, colors, tot, ttl in ((axes[0], drv_cols, CH_DRV, "= error from assumptions (A - B)", "Errors from external assumptions (A - B), by driver"),
                                       (axes[1], rel_cols, CH_EQ, "= error from relationships (B - realised)", "Errors from the estimated equations (B - realised), by equation")):
        pos, neg = np.zeros(len(dec)), np.zeros(len(dec))
        for i, c in enumerate(cols):
            v = dec[c].values
            b = np.where(v >= 0, pos, neg)
            ax.bar(x, v, bottom=b, color=colors[i], width=0.72, label=c.split(": ", 1)[1], edgecolor="white", linewidth=1)
            pos, neg = pos + np.clip(v, 0, None), neg + np.clip(v, None, 0)
        ax.plot(x, dec[tot].values, color=INK, lw=1.6, marker="o", ms=4, label="Total of panel")
        ax.axhline(0, color="#bdbcb6", lw=1)
        _style(ax, ttl, "pp, q/q annualised (+ = forecast too high)")
        ax.legend(frameon=False, fontsize=8, ncol=1, loc="center left", bbox_to_anchor=(1.01, 0.5))
    _xticks(axes[1], dec.index)
    if note:
        fig.text(0.01, 0.005, note, fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.savefig(path)
    plt.close(fig)


CH_DRV = DRV
CH_EQ = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6"]
