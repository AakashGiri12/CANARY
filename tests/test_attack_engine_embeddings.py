import math

from attack_engine.db import EMBEDDING_DIM
from attack_engine.embeddings import MockEmbedder


def test_mock_embedder_returns_correct_dimension():
    assert len(MockEmbedder().embed("hello world")) == EMBEDDING_DIM


def test_mock_embedder_is_deterministic():
    embedder = MockEmbedder()
    assert embedder.embed("same text") == embedder.embed("same text")


def test_mock_embedder_differs_for_different_text():
    embedder = MockEmbedder()
    assert embedder.embed("alpha") != embedder.embed("beta")


def test_mock_embedder_returns_unit_vector():
    vec = MockEmbedder().embed("normalize me")
    norm = math.sqrt(sum(v * v for v in vec))
    assert abs(norm - 1.0) < 1e-6
