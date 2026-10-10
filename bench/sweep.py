#!/usr/bin/env python3
"""Thread-scaling sweep for the ray tracer.

Runs build/main at 1, 2, 4, 8, and 16 threads, three rounds each, and saves
every measurement to bench/scaling.csv. Run it from the RayTracer folder:

    python3 bench/sweep.py --quick               # 1-minute smoke test first
    caffeinate -i python3 bench/sweep.py         # the real sweep, about 35-40 minutes
"""
import csv
import os
import re
import subprocess
import sys
import time

QUICK   = "--quick" in sys.argv
BINARY  = "build/main"
THREADS = [8] if QUICK else [1, 2, 4, 8, 16]
ROUNDS  = 1 if QUICK else 3
PAUSE_S = 0 if QUICK else 60            # rest between runs: the MacBook Air has no fan
OUT_CSV = "bench/quick.csv" if QUICK else "bench/scaling.csv"

# Finds the timing line your renderer prints at the end, e.g.
#   Done. Compute time: 47.2828s    Write: 0.202911s
TIMING = re.compile(r"Compute(?: time)?:\s*([\d.]+)\s*s.*Write:\s*([\d.]+)\s*s")


def git(*args):
    result = subprocess.run(["git", *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


if not os.path.isdir("build"):
    sys.exit("Run this from the RayTracer folder (there's no build/ directory here).")

# 1. Only measure committed code, so the hash saved with every row is the truth.
if git("status", "--porcelain", "--untracked-files=no"):
    sys.exit("You have uncommitted changes. Commit them first, then run the sweep.")
commit = git("rev-parse", "--short", "HEAD")

# 2. Rebuild, so the binary matches that commit.
subprocess.run(["cmake", "--build", "build"], check=True)

# 3. Run. Rounds go on the OUTSIDE, so cool-chip and warm-chip runs
#    get spread evenly across every thread count.
print(f"\nCommit {commit}: threads {THREADS}, {ROUNDS} round(s), {PAUSE_S}s rest between runs\n")
os.makedirs("bench", exist_ok=True)
with open(OUT_CSV, "w", newline="") as f:
    out = csv.writer(f)
    out.writerow(["commit", "round", "threads", "compute_s", "write_s", "total_s"])

    for rnd in range(1, ROUNDS + 1):
        for t in THREADS:
            print(f"round {rnd}/{ROUNDS}  threads {t:>2}  ...", end="", flush=True)

            run = subprocess.run([BINARY, str(t)],
                                 stdout=subprocess.DEVNULL,   # throw the image away
                                 stderr=subprocess.PIPE,      # keep the timing line
                                 text=True, check=True)
            match = TIMING.search(run.stderr)
            if match is None:
                sys.exit("\nNo timing line found in the renderer's output:\n" + run.stderr[-300:])

            compute, write = float(match.group(1)), float(match.group(2))
            total = compute + write
            out.writerow([commit, rnd, t, compute, write, round(total, 4)])
            f.flush()                     # saved now, even if a later run crashes

            print(f"  {total:7.2f} s", flush=True)
            if (rnd, t) != (ROUNDS, THREADS[-1]):     # no rest needed after the last run
                time.sleep(PAUSE_S)

print(f"\nDone. Saved {OUT_CSV}.")
