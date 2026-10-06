"""BTVN#3 - SHARED HARNESS for the flight booking agent.

    Agent = Model + Harness

The MODEL decides what to do. The HARNESS (plain Python) decides whether it is
allowed and whether the job is really done. All 3 agent patterns
(ReAct, Plan-then-Execute, Hybrid) use THIS SAME harness, so we can compare
the patterns fairly:

    1. Constraints are DATA      Constraints, CONSTRAINTS
    2. Permission check          check_permission()    (runs BEFORE every tool)
    3. Done is checked by CODE   is_done()             (reads the booking back)
    4. Handoff to a human        handoff()
    +  Budget                    MAX_TOOL_CALLS + ModelCallLimitMiddleware
    +  One gate for all tools    guarded_call()        (permission + log + budget)
"""
import json
import os
from dataclasses import dataclass

from langchain.agents.middleware import wrap_tool_call
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI

try:                                    # optional: read API keys from a .env file
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# =====================================================================
# THE LLM - a REAL model through an OpenAI-compatible API (no fake model).
# Everything is configured in the .env file (see .env.example):
#     LLM_API_KEY    the API key
#     LLM_MODEL      the model name, e.g. gpt-4o-mini, deepseek-chat, qwen-plus ...
#     LLM_BASE_URL   the API endpoint, e.g. https://api.openai.com/v1
# =====================================================================


class Meter(BaseCallbackHandler):
    """Counts model calls and tokens (the cost of a run). Attached to the model itself."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.model_calls = 0
        self.tokens = 0

    def on_llm_end(self, response, **kwargs):
        self.model_calls += 1
        for generations in response.generations:
            for g in generations:
                usage = getattr(getattr(g, "message", None), "usage_metadata", None)
                if usage:
                    self.tokens += usage.get("total_tokens", 0)


METER = Meter()


def make_model() -> ChatOpenAI:
    """One chat model instance, built ONLY from the .env settings. temperature=0 for repeatable runs."""
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")
    base_url = os.getenv("LLM_BASE_URL")
    missing = [n for n, v in (("LLM_API_KEY", api_key), ("LLM_MODEL", model), ("LLM_BASE_URL", base_url)) if not v]
    if missing:
        raise RuntimeError(f"Missing in .env: {', '.join(missing)} (copy .env.example to .env and fill it in)")
    return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=0, callbacks=[METER])


# =====================================================================
# 1. CONSTRAINTS ARE DATA
#    The prompt is built FROM the data, and the harness CHECKS the data
#    in code. The model cannot "forget" a constraint.
# =====================================================================
@dataclass
class Constraints:
    origin: str = "SGN"
    destination: str = "DAD"
    date: str = "2026-10-07"
    depart_before: str = "12:00"      # morning flight
    max_price: int = 2_000_000        # VND

    def to_prompt(self) -> str:
        return (f"Book one ticket {self.origin} -> {self.destination} on {self.date}, "
                f"departing before {self.depart_before}, price at most {self.max_price:,} VND.")

    def is_ok(self, flight: dict) -> bool:
        """Does this flight satisfy ALL constraints?"""
        return (flight["depart"].startswith(self.date)
                and flight["depart"][11:16] < self.depart_before
                and flight["price"] <= self.max_price)


CONSTRAINTS = Constraints()


# =====================================================================
# MOCKUP WORLD - fake data, no network. 4 scenarios used for evaluation.
# =====================================================================
VN122 = {"flight": "VN122", "depart": "2026-10-07T08:10", "price": 1_850_000}   # valid
QH118 = {"flight": "QH118", "depart": "2026-10-07T15:40", "price": 1_640_000}   # cheap, but afternoon
VU330 = {"flight": "VU330", "depart": "2026-10-07T07:30", "price": 1_950_000}   # valid (backup)
VJ604 = {"flight": "VJ604", "depart": "2026-10-07T08:10", "price": 2_480_000}   # morning, but too expensive

SCENARIOS = {
    "success":   {"flights": [VN122, QH118], "sold_out": [], "flaky_book": 0, "expect": "DONE",
                  "desc": "A valid flight exists, nothing goes wrong"},
    "no_valid":  {"flights": [VJ604, QH118], "sold_out": [], "flaky_book": 0, "expect": "FAILED",
                  "desc": "No flight is both in the morning AND <= 2M -> must hand off"},
    "sold_out":  {"flights": [VN122, VU330, QH118], "sold_out": ["VN122"], "flaky_book": 0, "expect": "DONE",
                  "desc": "The best flight is sold out, but a valid backup (VU330) exists"},
    "transient": {"flights": [VN122, QH118], "sold_out": [], "flaky_book": 1, "expect": "DONE",
                  "desc": "book_seat fails once with a timeout, a retry works"},
}
MAX_TOOL_CALLS = 12     # harness budget: hard limit of tool calls per run


class World:
    """The fake booking system. reset() before every run."""
    def __init__(self):
        self.reset("success")

    def reset(self, scenario: str):
        self.scenario = scenario
        self.cfg = SCENARIOS[scenario]
        self.bookings = {}                         # code -> booking
        self.log = []                              # every tool call: (name, args, result)
        self.book_errors_left = self.cfg["flaky_book"]
        METER.reset()


WORLD = World()


def search_flights(origin: str, destination: str, date: str) -> dict:
    """Search flights by route and date (YYYY-MM-DD)."""
    return {"status": "ok", "flights": WORLD.cfg["flights"]}


def book_seat(flight: str) -> dict:
    """Hold a seat on a flight. Returns a booking code. No money is charged yet."""
    info = next((f for f in WORLD.cfg["flights"] if f["flight"] == flight), None)
    if info is None:
        return {"status": "not_found", "flight": flight}
    if WORLD.book_errors_left > 0:                 # transient fault: the service times out
        WORLD.book_errors_left -= 1
        return {"status": "error", "error": "timeout, please retry"}
    if flight in WORLD.cfg["sold_out"]:
        return {"status": "sold_out", "flight": flight}
    code = f"{flight}-12A"
    WORLD.bookings[code] = {"code": code, "paid": False, **info}
    return {"status": "ok", **WORLD.bookings[code]}


def pay(code: str) -> dict:
    """Pay for a held booking. This spends money and cannot be undone."""
    if code not in WORLD.bookings:
        return {"status": "not_found", "code": code}
    WORLD.bookings[code]["paid"] = True
    return {"status": "ok", **WORLD.bookings[code]}


def get_booking(code: str) -> dict:
    """Read a booking back from the system."""
    return {"status": "ok", **WORLD.bookings[code]} if code in WORLD.bookings else {"status": "not_found"}


TOOLS = [search_flights, book_seat, pay, get_booking]
TOOL_FUNCS = {f.__name__: f for f in TOOLS}


# =====================================================================
# THE HARNESS
# =====================================================================
# ---- 2. PERMISSION CHECK: runs BEFORE the tool, using the constraint DATA
def check_permission(tool: str, args: dict) -> str | None:
    """Return None if allowed, or a reason if the call must be blocked."""
    if tool == "book_seat":
        flight = next((f for f in WORLD.cfg["flights"] if f["flight"] == args.get("flight")), None)
        if flight is None or not CONSTRAINTS.is_ok(flight):
            return f"{args.get('flight')} breaks the constraints: {CONSTRAINTS.to_prompt()}"
    if tool == "pay":                              # money cannot be undone -> strictest check
        b = WORLD.bookings.get(args.get("code"))
        if b is not None and not CONSTRAINTS.is_ok(b):
            return f"booking {b['code']} breaks the constraints, will not pay"
        if b is not None and b["paid"]:
            return f"booking {b['code']} is already paid"
    return None


# ---- 3. DONE IS CHECKED BY CODE: never trust the model saying "I'm done"
def is_done() -> bool:
    """Done = a booking exists, is paid, and satisfies the constraints."""
    for code in WORLD.bookings:
        b = get_booking(code)                      # read back from the system
        if b["paid"] and CONSTRAINTS.is_ok(b):
            return True
    return False


# ---- 4. HANDOFF: when the agent fails, give a human 3 things
def handoff() -> dict:
    searched = next((r["flights"] for t, _, r in WORLD.log if t == "search_flights" and r["status"] == "ok"), [])
    valid = [f["flight"] for f in searched if CONSTRAINTS.is_ok(f)]
    last_problem = next((f"{t}({a}) -> {r['status']}" for t, a, r in reversed(WORLD.log) if r["status"] != "ok"), None)
    if not valid:
        question = ("No flight meets all constraints. Which one can we relax: "
                    "departure time or maximum price?")
    else:
        question = (f"Valid flights exist ({', '.join(valid)}) but the booking did not finish "
                    f"(last problem: {last_problem}). Retry, or book by hand?")
    return {
        "done_so_far": [f"{c}: paid={b['paid']}" for c, b in WORLD.bookings.items()] or ["Nothing booked, nothing paid"],
        "tried": [f"{t}({a}) -> {r['status']}" for t, a, r in WORLD.log],
        "question": question,
    }


# ---- ONE GATE for every tool call of every pattern: budget -> permission -> run -> log
def guarded_call(name: str, args: dict) -> dict:
    if len(WORLD.log) >= MAX_TOOL_CALLS:
        result = {"status": "denied", "reason": "tool-call budget used up"}
    else:
        reason = check_permission(name, args)
        result = {"status": "denied", "reason": reason} if reason else TOOL_FUNCS[name](**args)
    WORLD.log.append((name, args, result))
    return result


@wrap_tool_call
def harness_middleware(request, handler):
    """LangChain middleware: the ReAct agent can only reach tools through guarded_call()."""
    call = request.tool_call
    result = guarded_call(call["name"], call["args"])
    return ToolMessage(content=json.dumps(result), tool_call_id=call["id"], name=call["name"])


# ---- The harness, not the model, writes the final result
def finish() -> dict:
    done = is_done()
    out = {
        "result": "DONE" if done else "FAILED",
        "model_calls": METER.model_calls,
        "tokens": METER.tokens,
        "tool_calls": len(WORLD.log),
        "blocked": sum(r["status"] == "denied" for _, _, r in WORLD.log),
        "unsafe_payments": sum(b["paid"] and not CONSTRAINTS.is_ok(b) for b in WORLD.bookings.values()),
    }
    if done:
        out["booking"] = list(WORLD.bookings.values())
    else:
        out["handoff"] = handoff()
    return out


SEARCH_ARGS = dict(origin=CONSTRAINTS.origin, destination=CONSTRAINTS.destination, date=CONSTRAINTS.date)


# =====================================================================
# SMALL HELPERS FOR THE DEMOS (main of each agent file)
# =====================================================================
def choose_scenario() -> str:
    names = list(SCENARIOS)
    print("Choose a scenario:")
    for i, n in enumerate(names, 1):
        print(f"  {i}. {n:<10} - {SCENARIOS[n]['desc']}")
    choice = ""
    while choice not in [str(i) for i in range(1, len(names) + 1)]:
        choice = input(f"Your choice (1-{len(names)}): ").strip()
    return names[int(choice) - 1]


def print_trace_and_result(output: dict):
    print("\n--- trace (every tool call) ---")
    for i, (tool, args, result) in enumerate(WORLD.log, 1):
        print(f"[{i}] {tool}({args}) -> {result['status']} {result.get('reason', '')}")
    print("\n--- result (decided by the harness, not by the model) ---")
    print(json.dumps(output, indent=2))
