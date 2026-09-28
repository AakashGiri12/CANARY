from target_agent.llm import FinalAnswerAction, ScriptedLLM, ToolCallAction


def test_scripted_llm_walks_plan_in_order():
    plan = [
        ToolCallAction(tool="read_email", args={"message_id": "msg-1"}),
        FinalAnswerAction(text="done"),
    ]
    llm = ScriptedLLM(plan=plan)

    first = llm.next_action(task="t", messages=[], tool_specs=[])
    second = llm.next_action(task="t", messages=[], tool_specs=[])

    assert first == plan[0]
    assert second == plan[1]


def test_scripted_llm_exhausted_plan_returns_final_answer():
    llm = ScriptedLLM(plan=[FinalAnswerAction(text="only step")])
    llm.next_action(task="t", messages=[], tool_specs=[])

    exhausted = llm.next_action(task="t", messages=[], tool_specs=[])

    assert isinstance(exhausted, FinalAnswerAction)
