import uuid

import pytest


@pytest.fixture
def unique_model_defense():
    """A unique (target_model, defense_config) pair per test, so
    attack_memory rows written by one test don't leak into another's
    retrieval query."""
    suffix = uuid.uuid4().hex[:8]
    return f"test-model-{suffix}", f"test-defense-{suffix}"
