from target_agent.graph import build_graph
from target_agent.llm import FinalAnswerAction, ScriptedLLM, ToolCallAction


def _run(plan):
    llm = ScriptedLLM(plan=plan)
    graph = build_graph(llm)
    initial_state = {
        "run_id": "test-run",
        "task": "test task",
        "turn": 0,
        "messages": [],
        "final_answer": None,
    }
    return graph.invoke(initial_state)


def test_graph_completes_after_tool_calls_and_final_answer():
    plan = [
        ToolCallAction(tool="read_email", args={"message_id": "msg-1"}),
        ToolCallAction(tool="read_file", args={"path": "docs/q3_plan.txt"}),
        FinalAnswerAction(text="summary"),
    ]

    final_state = _run(plan)

    assert final_state["final_answer"] == "summary"
    # 2 tool calls -> 2 assistant messages + 2 tool-result messages, plus
    # the final assistant message.
    assert len(final_state["messages"]) == 5
    tool_results = [m for m in final_state["messages"] if m["role"] == "tool"]
    assert all(m["ok"] for m in tool_results)


def test_graph_logs_tool_error_without_crashing():
    plan = [
        ToolCallAction(tool="read_email", args={"message_id": "missing"}),
        FinalAnswerAction(text="handled the error"),
    ]

    final_state = _run(plan)

    tool_message = final_state["messages"][1]
    assert tool_message["role"] == "tool"
    assert tool_message["ok"] is False
    assert "error" in tool_message["content"]
    assert final_state["final_answer"] == "handled the error"


def test_graph_completes_immediately_with_no_tool_calls():
    final_state = _run([FinalAnswerAction(text="no tools needed")])

    assert final_state["final_answer"] == "no tools needed"
    assert final_state["messages"] == [{"role": "assistant", "content": "no tools needed"}]
