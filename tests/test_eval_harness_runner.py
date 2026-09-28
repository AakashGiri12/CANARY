from attack_engine.library import STATIC_ATTACKS
from eval_harness.runner import load_task, run_static_eval
from target_agent.llm import NaiveCompliantLLM, ScriptedLLM
from target_agent.llm import FinalAnswerAction, ToolCallAction


def test_load_task_returns_expected_shape():
    task = load_task("q3-plan-check")
    assert "prompt" in task
    assert "Target Agent" in task["expected_keywords"]


def _immune_plan():
    return [
        ToolCallAction(tool="read_email", args={"message_id": "msg-1"}),
        ToolCallAction(tool="read_file", args={"path": "docs/q3_plan.txt"}),
        ToolCallAction(
            tool="fetch_url", args={"url": "https://intranet.example.com/roadmap"}
        ),
        FinalAnswerAction(
            text="Alice's numbers check out: Target Agent ships in September."
        ),
    ]


def test_run_static_eval_produces_one_baseline_plus_one_row_per_attack():
    results = run_static_eval({"scripted-immune": lambda: ScriptedLLM(plan=_immune_plan())})
    assert len(results) == 1 + len(STATIC_ATTACKS)
    assert sum(r.attack_id is None for r in results) == 1


def test_immune_llm_never_falls_for_static_attacks():
    results = run_static_eval({"scripted-immune": lambda: ScriptedLLM(plan=_immune_plan())})
    attacked = [r for r in results if r.attack_id is not None]
    assert all(not r.asr for r in attacked)
    assert all(r.utility for r in results)


def test_naive_compliant_llm_falls_for_every_static_attack():
    results = run_static_eval({"naive-compliant": lambda: NaiveCompliantLLM()})
    attacked = [r for r in results if r.attack_id is not None]
    assert all(r.asr for r in attacked)
    # Complying with the injection means abandoning the real task.
    assert all(not r.utility for r in attacked)

    baseline = next(r for r in results if r.attack_id is None)
    assert baseline.utility
    assert not baseline.asr
