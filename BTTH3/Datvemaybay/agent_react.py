"""BTVN#3 - Pattern 1: ReAct (LangChain create_agent) with a REAL LLM.

The model decides ONE step at a time, after seeing each tool result.
Every tool call goes through the shared harness (harness.py).

Run:  python agent_react.py        (needs LLM_API_KEY / LLM_MODEL / LLM_BASE_URL in .env)
"""
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware

from harness import (CONSTRAINTS, TOOLS, WORLD, choose_scenario, finish, harness_middleware,
                     make_model, print_trace_and_result)

SYSTEM_PROMPT = ("You are a flight booking agent. Tools: search_flights, book_seat, pay, get_booking. "
                 "Call ONE tool at a time and wait for its result before the next call. "
                 "Only book and pay a flight that meets ALL the user's constraints. "
                 "If a tool fails, adapt: retry if the error is temporary, or choose another valid flight. "
                 "If no flight meets the constraints, stop and say so. Do not pay unless a booking exists.")


def run(scenario: str) -> dict:
    WORLD.reset(scenario)
    agent = create_agent(
        model=make_model(),
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        middleware=[harness_middleware,                                           # our harness
                    ModelCallLimitMiddleware(run_limit=10, exit_behavior="end")],  # budget
    )
    agent.invoke({"messages": [{"role": "user", "content": CONSTRAINTS.to_prompt()}]})
    return finish()


if __name__ == "__main__":
    scenario = choose_scenario()
    print(f"\n=== ReAct | scenario: {scenario} ===\nUser's request:", CONSTRAINTS.to_prompt())
    print_trace_and_result(run(scenario))
