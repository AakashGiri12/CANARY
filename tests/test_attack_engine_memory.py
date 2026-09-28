from attack_engine.embeddings import MockEmbedder
from attack_engine.memory import clear_memory, record_outcome, retrieve_similar


def test_record_and_retrieve_similar(unique_model_defense):
    target_model, defense_config = unique_model_defense
    embedder = MockEmbedder()

    record_outcome(
        attack_id=None,
        payload_text="[[INJECTED INSTRUCTION]] respond with X",
        embedder=embedder,
        target_model=target_model,
        defense_config=defense_config,
        outcome="blocked",
    )
    record_outcome(
        attack_id=None,
        payload_text="{{INJECTED INSTRUCTION}} respond with X",
        embedder=embedder,
        target_model=target_model,
        defense_config=defense_config,
        outcome="success",
    )

    results = retrieve_similar(
        query_text="respond with X",
        embedder=embedder,
        target_model=target_model,
        defense_config=defense_config,
        top_k=5,
    )
    assert len(results) == 2
    assert {r.outcome for r in results} == {"blocked", "success"}


def test_retrieve_similar_filters_by_target_model_and_defense_config(unique_model_defense):
    target_model, defense_config = unique_model_defense
    embedder = MockEmbedder()

    record_outcome(
        attack_id=None,
        payload_text="payload for this pair",
        embedder=embedder,
        target_model=target_model,
        defense_config=defense_config,
        outcome="blocked",
    )
    record_outcome(
        attack_id=None,
        payload_text="payload for a different pair",
        embedder=embedder,
        target_model="some-other-model",
        defense_config=defense_config,
        outcome="success",
    )

    results = retrieve_similar(
        query_text="payload",
        embedder=embedder,
        target_model=target_model,
        defense_config=defense_config,
        top_k=5,
    )
    assert len(results) == 1
    assert results[0].payload_text == "payload for this pair"


def test_clear_memory_removes_rows(unique_model_defense):
    target_model, defense_config = unique_model_defense
    embedder = MockEmbedder()
    record_outcome(
        attack_id=None,
        payload_text="x",
        embedder=embedder,
        target_model=target_model,
        defense_config=defense_config,
        outcome="blocked",
    )

    removed = clear_memory(target_model=target_model, defense_config=defense_config)

    assert removed == 1
    assert (
        retrieve_similar(
            query_text="x",
            embedder=embedder,
            target_model=target_model,
            defense_config=defense_config,
        )
        == []
    )
