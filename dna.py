#!/usr/bin/env python3
"""DNA double helix drawn across a GitHub contribution graph.

The pattern is a pure function of the calendar date, anchored to a fixed epoch
Sunday. That matters: the 53-week graph window slides forward every day, so
anchoring to absolute dates (not to window position) keeps the helix stable
instead of smearing as weeks roll off the left edge.

  python3 dna.py preview        # ASCII render of the next/last year
  python3 dna.py backfill 53    # commit the past 53 weeks
  python3 dna.py today          # commit today's pixel only (for the daily agent)
  python3 dna.py selfcheck
"""
import datetime as dt
import math
import os
import subprocess
import sys

EPOCH = dt.date(2020, 1, 5)   # a Sunday; fixes the helix phase forever
PERIOD = 18                   # weeks per full turn (~2.9 turns per year)
AMP, CENTER = 3.0, 3.0
RUNG_EVERY = 3                # a base-pair rung every 3rd week
BRIGHT, DIM = 28, 9           # commits per cell; BRIGHT must exceed the
                              # account's existing max daily count (23) or
                              # GitHub's shading quantiles wash the art out
REPO = os.path.dirname(os.path.abspath(__file__))


def cell(d):
    """Intensity for a date: 2 = strand, 1 = rung, 0 = blank."""
    week = (d - EPOCH).days // 7
    row = (d.weekday() + 1) % 7            # Sunday = 0, matching the graph
    t = 2 * math.pi * week / PERIOD
    a = round(CENTER + AMP * math.sin(t))
    b = round(CENTER - AMP * math.sin(t))
    if row in (a, b):
        return 2
    if week % RUNG_EVERY == 0 and abs(a - b) >= 3 and min(a, b) < row < max(a, b):
        return 1
    return 0


def commits_for(d):
    return {2: BRIGHT, 1: DIM, 0: 0}[cell(d)]


def commit(d, n):
    """n commits dated d. Touches a file: empty commits are not worth the risk."""
    stamp = f"{d.isoformat()}T12:00:00"
    env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    path = os.path.join(REPO, "helix.txt")
    kind = "strand" if cell(d) == 2 else "rung"
    for i in range(n):
        with open(path, "a") as f:
            f.write(f"{d.isoformat()} {kind} {i + 1}/{n}\n")
        subprocess.run(["git", "add", "helix.txt"], cwd=REPO, env=env, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", f"dna: {kind} pixel {d.isoformat()} ({i + 1}/{n})"],
            cwd=REPO, env=env, check=True,
        )


def sundays_back(weeks):
    today = dt.date.today()
    start = today - dt.timedelta(days=(today.weekday() + 1) % 7) - dt.timedelta(weeks=weeks - 1)
    return [start + dt.timedelta(days=i) for i in range(weeks * 7)]


def preview(weeks=53):
    days = sundays_back(weeks)
    glyph = {0: "·", 1: "▒", 2: "█"}
    grid = [[glyph[cell(d)] for d in days if (d.weekday() + 1) % 7 == r] for r in range(7)]
    print(f"period {PERIOD}w, {weeks / PERIOD:.1f} turns, {days[0]} -> {days[-1]}")
    for row in grid:
        print("".join(row))
    tot = sum(commits_for(d) for d in days)
    lit = sum(1 for d in days if cell(d))
    print(f"\n{lit} lit cells of {len(days)} days, {tot} commits total")


def backfill(weeks=53):
    days = [d for d in sundays_back(weeks) if d <= dt.date.today() and commits_for(d)]
    total = sum(commits_for(d) for d in days)
    print(f"backfilling {len(days)} days, {total} commits")
    for i, d in enumerate(days, 1):
        commit(d, commits_for(d))
        if i % 25 == 0:
            print(f"  {i}/{len(days)} days")
    print(f"done, {total} commits")


def selfcheck():
    # phase is anchored to absolute dates, not to the sliding window
    d = dt.date(2026, 6, 14)
    assert cell(d) == cell(d), "cell must be deterministic"
    assert cell(d + dt.timedelta(weeks=PERIOD)) == cell(d), "must repeat one full turn later"

    # every column has exactly the two strand cells (they merge when crossing)
    for w in range(PERIOD):
        base = EPOCH + dt.timedelta(weeks=w + 300)
        col = [cell(base + dt.timedelta(days=i)) for i in range(7)]
        assert 1 <= col.count(2) <= 2, f"week {w} has {col.count(2)} strand cells"

    # rows stay inside the 7-day grid, and the two strands mirror each other
    for w in range(40):
        t = 2 * math.pi * w / PERIOD
        a, b = round(CENTER + AMP * math.sin(t)), round(CENTER - AMP * math.sin(t))
        assert 0 <= a <= 6 and 0 <= b <= 6, f"row out of grid at week {w}: {a},{b}"
        assert a + b == 6, f"strands not mirrored at week {w}: {a},{b}"

    # the bright tier must outrank existing real activity or the art washes out
    assert BRIGHT > 23, "BRIGHT must exceed the account's current max daily count"
    assert DIM * 3 < BRIGHT, "DIM and BRIGHT must land in different shading buckets"

    # Sunday maps to row 0, Saturday to row 6
    assert (dt.date(2026, 10, 11).weekday() + 1) % 7 == 0, "Sunday must be row 0"
    assert (dt.date(2026, 10, 17).weekday() + 1) % 7 == 6, "Saturday must be row 6"
    print("selfcheck ok")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "preview"
    arg = int(sys.argv[2]) if len(sys.argv) > 2 else 53
    {"preview": lambda: preview(arg), "backfill": lambda: backfill(arg),
     "today": lambda: commit(dt.date.today(), commits_for(dt.date.today()))
                      if commits_for(dt.date.today()) else print("blank cell today"),
     "selfcheck": selfcheck}[cmd]()
