from attack_engine.library import STATIC_ATTACKS


def test_static_attacks_have_unique_ids():
    ids = [a.id for a in STATIC_ATTACKS]
    assert len(ids) == len(set(ids))


def test_static_attacks_target_known_fixture_keys():
    known_keys = {"msg-1", "docs/q3_plan.txt", "https://intranet.example.com/roadmap"}
    for attack in STATIC_ATTACKS:
        assert attack.target_key in known_keys


def test_static_attacks_success_marker_is_in_payload():
    for attack in STATIC_ATTACKS:
        assert attack.success_marker in attack.payload_text
