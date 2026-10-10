#!/usr/bin/env python3
"""Turns bench/scaling.csv into a Markdown table, a few key numbers, and docs/scaling.png.

    python3 bench/analyze.py
"""
import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")                      # draw straight to a file, no window
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator

# threads -> list of (total, write), one entry per round
runs = defaultdict(list)
with open("bench/scaling.csv") as f:
    for row in csv.DictReader(f):
        runs[int(row["threads"])].append((float(row["total_s"]), float(row["write_s"])))

threads = sorted(runs)
best    = {t: min(runs[t]) for t in threads}             # fastest round wins: noise only ADDS time
speedup = {t: best[1][0] / best[t][0] for t in threads}  # every ratio uses the same 1-thread run
rounds  = len(runs[1])

# 1. The table, ready to paste into benchmarks.md
print(f"| Threads | Best of {rounds} (s) | Speedup |")
print("|--------:|---------------:|--------:|")
for t in threads:
    print(f"| {t} | {best[t][0]:.2f} | {speedup[t]:.2f}× |")

# 2. Amdahl's law: the write phase is the part that can't run in parallel.
total_1, write_1 = best[1]
serial = write_1 / total_1
print(f"\nSerial fraction (write ÷ total, 1 thread): {serial:.2%}")
print(f"Amdahl limit on 8 identical cores: {1 / (serial + (1 - serial) / 8):.2f}×")

# 3. Where the curve bends. 4 threads fill the 4 P-cores; threads 5-8 land on E-cores.
if 4 in speedup:
    print(f"4 threads: {speedup[4]:.2f}× = {speedup[4] / 4:.0%} of perfect (P-cores only)")
if 4 in speedup and 8 in speedup:
    added = speedup[8] - speedup[4]
    # each P-core is worth speedup[4]/4, each E-core is worth added/4, so the ratio is added/speedup[4]
    print(f"Threads 5-8 added {added:.2f}×  ->  one E-core ≈ {added / speedup[4]:.2f} of a P-core")

# 4. The chart. Both axes double at each step, so perfect scaling is a straight diagonal
#    and everything below it is lost efficiency.
SURFACE, INK, INK_2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, BAND, BLUE = "#e1e0d9", "#c3c2b7", "#f0efec", "#2a78d6"
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Helvetica", "Arial", "DejaVu Sans"]

fig, ax = plt.subplots(figsize=(7, 4.5), facecolor=SURFACE)
ax.set_facecolor(SURFACE)

ax.axvspan(4, 8, color=BAND, zorder=0)                     # the region where E-cores join in
ax.plot([1, 8, 16], [1, 8, 8], "--", color=MUTED, linewidth=1.1, zorder=2,
        label="Ideal (8 equal cores)")                     # can't beat 8x with 8 cores
ax.plot(threads, [speedup[t] for t in threads], "-o", color=BLUE, linewidth=1.6, zorder=3,
        markersize=6.5, markeredgecolor=SURFACE, markeredgewidth=1.3, label="Measured")

if 8 in speedup:                                           # label only the headline number
    ax.annotate(f"{speedup[8]:.1f}× on 8 threads", xy=(8, speedup[8]), xytext=(8, -12),
                textcoords="offset points", ha="left", va="top", fontsize=9.5, color=INK)
ax.text(5.66, 1.0, "threads 5–8 run on\nefficiency cores", ha="center", va="bottom",
        fontsize=8.5, color=MUTED)
ax.text(11.3, 1.0, "more threads\nthan cores", ha="center", va="bottom", fontsize=8.5, color=MUTED)

ax.set_xscale("log", base=2)
ax.set_yscale("log", base=2)
ax.set_xticks(threads, [str(t) for t in threads])
ax.set_yticks([1, 2, 4, 8], ["1×", "2×", "4×", "8×"])
ax.xaxis.set_minor_locator(NullLocator())
ax.yaxis.set_minor_locator(NullLocator())
ax.set_xlim(0.85, 19)
ax.set_ylim(0.85, 11)

ax.grid(True, color=GRID, linewidth=0.6)
ax.set_axisbelow(True)
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color(AXIS)
    ax.spines[side].set_linewidth(0.8)
ax.tick_params(length=0, labelsize=9, labelcolor=MUTED)
ax.set_xlabel("Threads", color=INK_2, fontsize=9.5)
ax.set_ylabel("Speedup vs. 1 thread", color=INK_2, fontsize=9.5)
ax.set_title("Thread scaling on Apple M2 (4 performance + 4 efficiency cores)",
             loc="left", color=INK, fontsize=11.5, pad=24)
ax.text(0, 1.025, f"Best of {rounds} runs per thread count", transform=ax.transAxes,
        color=INK_2, fontsize=9)
ax.legend(loc="upper left", frameon=False, fontsize=9, labelcolor=INK_2)

os.makedirs("docs", exist_ok=True)
fig.savefig("docs/scaling.png", dpi=150, bbox_inches="tight", facecolor=SURFACE)
print("\nSaved docs/scaling.png")
