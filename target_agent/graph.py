"""LangGraph wiring: agent decides an action, tools node executes it, loop
until the agent produces a final answer.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from target_agent.llm import FinalAnswerAction, LLMClient, ToolCallAction
from target_agent.logging import get_run_logger
from target_agent.state import AgentState
from target_agent.tools import TOOLS, ToolError, tool_specs_for_llm


def build_graph(llm: LLMClient):
    tool_specs = tool_specs_for_llm()

    def agent_node(state: AgentState) -> dict:
        logger = get_run_logger(state["run_id"])
        action = llm.next_action(
            task=state["task"], messages=state["messages"], tool_specs=tool_specs
        )
        turn = state["turn"] + 1

        if isinstance(action, ToolCallAction):
            logger.info(
                "model_turn",
                turn=turn,
                action="tool_call",
                tool=action.tool,
                args=action.args,
            )
            message: dict = {"role": "assistant", "tool": action.tool, "args": action.args}
            return {"turn": turn, "messages": [*state["messages"], message]}

        assert isinstance(action, FinalAnswerAction)
        logger.info("model_turn", turn=turn, action="final_answer", content=action.text)
        message = {"role": "assistant", "content": action.text}
        return {
            "turn": turn,
            "messages": [*state["messages"], message],
            "final_answer": action.text,
        }

    def tools_node(state: AgentState) -> dict:
        logger = get_run_logger(state["run_id"])
        last = state["messages"][-1]
        tool_name, args = last["tool"], last.get("args", {})
        spec = TOOLS.get(tool_name)
        try:
            if spec is None:
                raise ToolError(f"unknown tool: {tool_name}")
            result = spec.run(**args)
            ok = True
        except ToolError as exc:
            result = {"error": str(exc)}
            ok = False

        logger.info(
            "tool_call", turn=state["turn"], tool=tool_name, args=args, ok=ok, result=result
        )
        message = {"role": "tool", "tool": tool_name, "content": result, "ok": ok}
        return {"messages": [*state["messages"], message]}

    def route(state: AgentState) -> str:
        return END if state.get("final_answer") is not None else "tools"

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route)
    graph.add_edge("tools", "agent")
    return graph.compile()
