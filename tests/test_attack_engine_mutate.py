from attack_engine.memory import RetrievedMemory
from attack_engine.mutate import _FRAMINGS, mutate


def _mem(payload_text: str, outcome: str) -> RetrievedMemory:
    return RetrievedMemory(
        id=None,
        attack_id=None,
        payload_text=payload_text,
        target_model="m",
        defense_config="d",
        outcome=outcome,
        asr_delta=None,
    )


def test_mutate_picks_first_framing_with_empty_history():
    result = mutate(base_instruction="do X", history=[])
    assert result.framing_index == 0
    assert result.payload_text == _FRAMINGS[0]("do X")


def test_mutate_skips_one_blocked_framing():
    history = [_mem(_FRAMINGS[0]("do X"), "blocked")]
    result = mutate(base_instruction="do X", history=history)
    assert result.framing_index == 1


def test_mutate_skips_all_blocked_framings_in_order():
    history = [
        _mem(_FRAMINGS[0]("do X"), "blocked"),
        _mem(_FRAMINGS[1]("do X"), "blocked"),
    ]
    result = mutate(base_instruction="do X", history=history)
    assert result.framing_index == 2


def test_mutate_does_not_avoid_a_framing_that_already_succeeded():
    history = [
        _mem(_FRAMINGS[0]("do X"), "blocked"),
        _mem(_FRAMINGS[1]("do X"), "blocked"),
        _mem(_FRAMINGS[2]("do X"), "success"),
    ]
    result = mutate(base_instruction="do X", history=history)
    assert result.framing_index == 2
