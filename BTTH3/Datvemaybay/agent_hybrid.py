"""BTVN#3 - Pattern 3: HYBRID = Plan-then-Execute + ReAct fallback (LangGraph), REAL LLM.

    START -> plan -> review --approved--> execute --all steps OK--> END
              ^         |                    |
              |  rejected (plans left)       +--a step failed--> react (fallback) -> END
              +---------+
                        +--empty plan / no plans left--> END (handoff)

Idea: use the CHEAP and REVIEWABLE path (1 plan, no model calls while executing)
when everything goes well. Only when a step fails, hand the problem to a ReAct
agent that can adapt. The same harness guards every tool call in both paths.

Run:  python agent_hybrid.py        (needs LLM_API_KEY / LLM_MODEL / LLM_BASE_URL in .env)
"""
import json
from typing import TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langgraph.graph import END, START, StateGraph

from agent_plan_execute import (MAX_PLANS, PLANNER_PROMPT, Plan, ask_human, auto_review,
                                execute_plan, write_plan)
from harness import (CONSTRAINTS, SEARCH_ARGS, TOOLS, WORLD, choose_scenario, finish, guarded_call,
                     harness_middleware, make_model, print_trace_and_result)

FALLBACK_PROMPT = ("You are a flight booking agent that takes over when a plan failed. "
                   "Tools: search_flights, book_seat, pay, get_booking. "
                   "Call ONE tool at a time and wait for its result. "
                   "Only book and pay a flight that meets ALL the user's constraints. "
                   "Do NOT repeat a step that already succeeded. "
                   "If a tool fails, adapt: retry if the error is temporary, or choose another valid flight. "
                   "If no valid way is left, stop and say so.")


class State(TypedDict, total=False):
    flights: list           # result of the search
    plan: Plan
    attempts: int           # plans written so far
    approved: bool
    failure: dict | None    # the step that failed during execute


def build_graph(reviewer, verbose: bool = False):
    model = make_model()
    planner = PLANNER_PROMPT | model.with_structured_output(Plan, method="function_calling")
    react = create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=FALLBACK_PROMPT,
        middleware=[harness_middleware, ModelCallLimitMiddleware(run_limit=6, exit_behavior="end")],
    )

    def plan_node(state: State) -> dict:                       # 1 model call
        if verbose:
            print(f"\n--- plan #{state['attempts'] + 1} ---")
        return {"plan": write_plan(planner, state["flights"]), "attempts": state["attempts"] + 1}

    def review_node(state: State) -> dict:                     # human (or scripted) approval
        plan = state["plan"]
        return {"approved": bool(plan.steps) and reviewer(plan)}

    def after_review(state: State) -> str:
        if state["approved"]:
            return "execute"
        if not state["plan"].steps or state["attempts"] >= MAX_PLANS:
            return "end"                                       # empty plan = no valid flight
        return "plan"                                          # rejected -> new plan

    def execute_node(state: State) -> dict:                    # plain code, 0 model calls
        if verbose:
            print("\n--- execute ---")
        return {"failure": execute_plan(state["plan"], verbose)}

    def after_execute(state: State) -> str:
        return "react" if state.get("failure") else "end"

    def react_node(state: State) -> dict:                      # fallback: the model can adapt now
        f = state["failure"]
        if verbose:
            print(f"\n--- step {f['step']} failed -> ReAct fallback takes over ---")
        message = (f"{CONSTRAINTS.to_prompt()}\n"
                   f"A plan was running and step {f['step']} failed: {f['tool']}({f['args']}) -> {f['result']}\n"
                   f"Flights found: {json.dumps(state['flights'])}\n"
                   f"Bookings so far: {json.dumps(list(WORLD.bookings.values()))}\n"
                   "Finish the booking in another way.")
        react.invoke({"messages": [{"role": "user", "content": message}]})
        return {}

    g = StateGraph(State)
    g.add_node("plan", plan_node)
    g.add_node("review", review_node)
    g.add_node("execute", execute_node)
    g.add_node("react", react_node)
    g.add_edge(START, "plan")
    g.add_edge("plan", "review")
    g.add_conditional_edges("review", after_review, {"execute": "execute", "plan": "plan", "end": END})
    g.add_conditional_edges("execute", after_execute, {"react": "react", "end": END})
    g.add_edge("react", END)
    return g.compile()


def run(scenario: str, reviewer=auto_review, verbose: bool = False) -> dict:
    WORLD.reset(scenario)
    found = guarded_call("search_flights", SEARCH_ARGS)        # read-only search, args from DATA
    graph = build_graph(reviewer, verbose)
    graph.invoke({"flights": found["flights"], "attempts": 0})
    return finish()


if __name__ == "__main__":
    scenario = choose_scenario()
    print(f"\n=== Hybrid (LangGraph) | scenario: {scenario} ===\nUser's request:", CONSTRAINTS.to_prompt())
    print_trace_and_result(run(scenario, reviewer=ask_human, verbose=True))
