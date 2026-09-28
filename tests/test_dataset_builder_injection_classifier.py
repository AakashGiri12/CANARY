import random

from datasets.injection_classifier.build_dataset import (
    SEED,
    _split,
    generate_benign_examples,
    generate_injection_examples,
)


def test_generation_is_deterministic():
    a = generate_injection_examples(random.Random(SEED), 30)
    b = generate_injection_examples(random.Random(SEED), 30)
    assert a == b


def test_injection_examples_are_labeled_1_and_cover_multiple_categories():
    examples = generate_injection_examples(random.Random(SEED), 60)
    assert all(e["label"] == 1 for e in examples)
    assert len({e["category"] for e in examples}) > 1


def test_benign_examples_are_labeled_0():
    examples = generate_benign_examples(random.Random(SEED), 30)
    assert all(e["label"] == 0 for e in examples)
    assert all(e["category"] == "benign" for e in examples)


def test_generated_examples_are_unique():
    examples = generate_injection_examples(random.Random(SEED), 100)
    texts = [e["text"] for e in examples]
    assert len(texts) == len(set(texts))


def test_split_has_no_leakage_between_held_out_and_rest():
    examples = generate_injection_examples(random.Random(SEED), 80)
    train, val, held_out = _split(examples, random.Random(SEED))

    train_texts = {e["text"] for e in train}
    val_texts = {e["text"] for e in val}
    held_texts = {e["text"] for e in held_out}

    assert not (train_texts & val_texts)
    assert not (train_texts & held_texts)
    assert not (val_texts & held_texts)
    assert len(train) + len(val) + len(held_out) == len(examples)
