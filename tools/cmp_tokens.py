#!/usr/bin/env python3
"""Qwen-token totals of the IRs written by cmp_run.py, old vs new (old may come from an earlier output directory).

  envs/qwen-data/bin/python cmp_tokens.py <new out dir> [<old out dir>]
"""
import json
import statistics as st
import sys
from pathlib import Path

from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[2]
tok = Tokenizer.from_file(str(ROOT / "envs/tok/tokenizer.json"))
new_dir = Path(sys.argv[1])
old_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else new_dir


def rows(d):
    return {r["part"]: r for r in (json.loads(l) for l in open(d / "results.jsonl"))}


new = {p: r for p, r in rows(new_dir).items() if r["tag"] == "new"} if new_dir == old_dir else rows(new_dir)
old = {}
for l in open(old_dir / "results.jsonl"):
    r = json.loads(l)
    if r["tag"] == "old":
        old[r["part"]] = r
pairs, errors = [], []
for p, n in new.items():
    o = old.get(p)
    if o is None or "error" in o or "error" in n:
        errors.append(p)
        continue
    to = len(tok.encode((old_dir / f"old__{p}.ir").read_text()).ids)
    tn = len(tok.encode((new_dir / f"new__{p}.ir").read_text()).ids)
    pairs.append((p, to, tn, o, n))
so, sn = sum(x[1] for x in pairs), sum(x[2] for x in pairs)
rat = sorted(x[2] / x[1] for x in pairs)
ver = [x[4].get("verify", {}) for x in pairs]
print(json.dumps({
    "parts": len(pairs), "errors": errors, "tokens_old": so, "tokens_new": sn, "ratio": round(sn / so, 4),
    "ratio_median": round(st.median(rat), 4), "ratio_p10": round(rat[len(rat) // 10], 4), "ratio_p90": round(rat[9 * len(rat) // 10], 4),
    "implied_old": sum(x[3]["implied"] for x in pairs), "implied_new": sum(x[4]["implied"] for x in pairs),
    "verify_ok": sum(v.get("ok", 0) for v in ver), "verify_implied": sum(v.get("implied", 0) for v in ver),
    "verify_bad": [[x[0], x[4]["verify"].get("bad")] for x in pairs if x[4].get("verify", {}).get("ok") != x[4].get("verify", {}).get("implied")],
    "parts_with_relief": sum(1 for x in pairs if x[4]["relief"]),
    "worse_3pct": [[x[0], x[1], x[2]] for x in pairs if x[2] > 1.03 * x[1]]}, indent=1))
