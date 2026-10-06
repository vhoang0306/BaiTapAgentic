"""BTVN#3 - Evaluate the 3 patterns on the same 4 scenarios with a REAL LLM.

Run:  python evaluate.py              (3 runs per case)
      python evaluate.py --runs 5     (more runs = more reliable, but more cost)

A real LLM is not 100% repeatable, so every (pattern, scenario) is run N times.

Metrics per run:
    result           DONE / FAILED (decided by the harness, is_done) / ERROR (API or code error)
    correct          result == expected result of the scenario
    model_calls      how many times the model was called
    tokens           total tokens used (the real cost)
    tool_calls       how many tool calls (incl. blocked ones)
    blocked          calls stopped by the harness (permission / budget)
    unsafe_payments  money spent on a booking that breaks the constraints (must be 0)

Output: a table on screen + evaluation_results.json (every run) + evaluation_results.md (paste into the report)
"""
import argparse
import json

import agent_hybrid
import agent_plan_execute
import agent_react
from harness import METER, SCENARIOS, WORLD

PATTERNS = {"ReAct": agent_react.run,
            "Plan-then-Execute": agent_plan_execute.run,
            "Hybrid": agent_hybrid.run}


def one_run(run, scenario: str) -> dict:
    try:
        return run(scenario)
    except Exception as e:                       # API error, rate limit, bad output...
        return {"result": "ERROR", "error": f"{type(e).__name__}: {str(e)[:150]}",
                "model_calls": METER.model_calls, "tokens": METER.tokens,
                "tool_calls": len(WORLD.log), "blocked": 0, "unsafe_payments": 0}


def avg(rs, key):
    return sum(r[key] for r in rs) / len(rs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=3)
    n = ap.parse_args().runs

    runs = []                                    # every single run
    for pattern, run in PATTERNS.items():
        for scenario, cfg in SCENARIOS.items():
            for i in range(n):
                out = one_run(run, scenario)
                out.update(pattern=pattern, scenario=scenario, expect=cfg["expect"],
                           correct=out["result"] == cfg["expect"])
                runs.append(out)
                print(f"  {pattern:<18}{scenario:<10} run {i + 1}/{n}: {out['result']}"
                      f"{'  ' + out['error'] if 'error' in out else ''}", flush=True)

    # ---- per (pattern, scenario)
    lines = [f"| Pattern | Scenario | Correct | Avg model calls | Avg tokens | Avg tool calls | Blocked | Unsafe pay | Errors |",
             "|---|---|---|---|---|---|---|---|---|"]
    for pattern in PATTERNS:
        for scenario in SCENARIOS:
            rs = [r for r in runs if r["pattern"] == pattern and r["scenario"] == scenario]
            lines.append(f"| {pattern} | {scenario} | {sum(r['correct'] for r in rs)}/{len(rs)} | "
                         f"{avg(rs, 'model_calls'):.1f} | {avg(rs, 'tokens'):.0f} | {avg(rs, 'tool_calls'):.1f} | "
                         f"{sum(r['blocked'] for r in rs)} | {sum(r['unsafe_payments'] for r in rs)} | "
                         f"{sum(r['result'] == 'ERROR' for r in rs)} |")
    # ---- per pattern
    lines += ["", "| Pattern | Correct | Avg model calls | Avg tokens | Avg tool calls | Unsafe pay |",
              "|---|---|---|---|---|---|"]
    for pattern in PATTERNS:
        rs = [r for r in runs if r["pattern"] == pattern]
        lines.append(f"| {pattern} | {sum(r['correct'] for r in rs)}/{len(rs)} | {avg(rs, 'model_calls'):.2f} | "
                     f"{avg(rs, 'tokens'):.0f} | {avg(rs, 'tool_calls'):.2f} | {sum(r['unsafe_payments'] for r in rs)} |")
    table = "\n".join(lines)
    print("\n" + table)

    open("evaluation_results.md", "w", encoding="utf-8").write(table + "\n")
    json.dump(runs, open("evaluation_results.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("\nSaved evaluation_results.md and evaluation_results.json")


if __name__ == "__main__":
    main()
