"""BTVN#3 - Pattern 2: Plan-then-Execute with a REAL LLM.

    Goal -> Model writes the WHOLE plan (1 call) -> Human reviews the plan
         -> approved: plain code runs Step 1, 2, 3 (NO more model calls) -> Result
         -> rejected: the model writes a new plan (at most MAX_PLANS plans)

+ the plan is visible BEFORE anything runs, so a human can stop it.
- the plan cannot adapt: if a step fails, we stop and hand off.

Run:  python agent_plan_execute.py        (needs LLM_API_KEY / LLM_MODEL / LLM_BASE_URL in .env)
"""
import json
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from harness import (CONSTRAINTS, SEARCH_ARGS, WORLD, check_permission, choose_scenario, finish,
                     guarded_call, make_model, print_trace_and_result)


# ---- The plan: the model must answer with this structure (structured output)
class Step(BaseModel):
    tool: Literal["book_seat", "pay", "get_booking"]
    flight: str | None = None     # for book_seat, e.g. "VN122"
    code: str | None = None       # for pay / get_booking: "$booking_code" (filled in later)

    def call_args(self) -> dict:
        return {k: v for k, v in (("flight", self.flight), ("code", self.code)) if v is not None}


class Plan(BaseModel):
    steps: list[Step]             # an EMPTY list means: "no flight meets the constraints"


PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You plan a flight booking. Write the WHOLE plan at once, as a list of steps. "
     "Tools: book_seat(flight), pay(code), get_booking(code). "
     "The booking code is not known yet: write \"$booking_code\" as the code and it will be filled in. "
     "A normal plan is: book_seat, pay, get_booking. "
     "Choose ONLY a flight that meets ALL the constraints. "
     "If no flight meets ALL constraints, return an empty list of steps."),
    ("human", "Goal: {goal}\nAvailable flights: {flights}"),
])
MAX_PLANS = 2       # budget: the model may write at most 2 plans


def fill_placeholders(args: dict) -> dict:
    """Replace "$booking_code" with the code returned by book_seat."""
    code = next((r["code"] for t, _, r in reversed(WORLD.log) if t == "book_seat" and r["status"] == "ok"), "")
    return {k: (code if v == "$booking_code" else v) for k, v in args.items()}


def execute_plan(plan: Plan, verbose: bool = False) -> dict | None:
    """Plain code runs the steps in order. Returns None if all OK, else the failed step."""
    for i, step in enumerate(plan.steps, 1):
        args = fill_placeholders(step.call_args())
        result = guarded_call(step.tool, args)                    # harness gate, BEFORE the step
        if verbose:
            print(f"  Step {i}: {step.tool}({args}) -> {result['status']} {result.get('reason', '')}")
        if result["status"] != "ok":
            return {"step": i, "tool": step.tool, "args": args, "result": result}
    return None


# ---- Plan review. A real human types y/n; the evaluation uses a careful scripted reviewer
#      (NOT an LLM: it is the "human" in the loop).
def auto_review(plan: Plan) -> bool:
    """A careful reviewer: reject any plan that books a flight breaking the constraints."""
    for step in plan.steps:
        if step.tool == "book_seat" and check_permission("book_seat", step.call_args()):
            return False
    return True


def ask_human(plan: Plan) -> bool:
    for i, step in enumerate(plan.steps, 1):
        print(f"  Step {i}: {step.tool}({step.call_args()})")
    answer = ""
    while answer not in ("y", "n"):
        answer = input("Human reviewer - approve this plan? (y/n): ").strip().lower()
    return answer == "y"


def write_plan(planner, flights: list) -> Plan:
    """ONE model call. If the model returns nothing usable, treat it as an empty plan."""
    draft = planner.invoke({"goal": CONSTRAINTS.to_prompt(), "flights": json.dumps(flights)})
    return draft or Plan(steps=[])


def run(scenario: str, reviewer=auto_review, verbose: bool = False) -> dict:
    WORLD.reset(scenario)
    # GOAL: the request + the flight list (a read-only search, arguments come from DATA)
    found = guarded_call("search_flights", SEARCH_ARGS)

    # PLAN + REVIEW
    planner = PLANNER_PROMPT | make_model().with_structured_output(Plan, method="function_calling")
    plan = None
    for attempt in range(1, MAX_PLANS + 1):
        draft = write_plan(planner, found["flights"])
        if verbose:
            print(f"\n--- plan #{attempt} (ONE model call) ---")
        if not draft.steps:
            if verbose:
                print("(empty plan: no flight meets the constraints)")
            break
        if reviewer(draft):
            plan = draft
            break
        if verbose:
            print("Rejected -> ask the model for a new plan.")

    # EXECUTE: no model call from here on
    if plan:
        if verbose:
            print("\n--- execute ---")
        failure = execute_plan(plan, verbose)
        if failure and verbose:
            print("  A step failed. Plan-then-execute cannot change the plan -> stop.")
    return finish()


if __name__ == "__main__":
    scenario = choose_scenario()
    print(f"\n=== Plan-then-Execute | scenario: {scenario} ===\nUser's request:", CONSTRAINTS.to_prompt())
    print_trace_and_result(run(scenario, reviewer=ask_human, verbose=True))
