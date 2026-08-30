import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "indexer"))

from tokenizer import tokenize


def test_lowercases():
    assert tokenize("HELLO World") == ["hello", "world"]


def test_removes_stopwords():
    tokens = tokenize("the quick fox and the lazy dog")
    assert "the" not in tokens
    assert "and" not in tokens
    assert "quick" in tokens


def test_strips_punctuation():
    tokens = tokenize("Hello, world! Isn't this great?")
    assert "hello" in tokens
    assert "world" in tokens
    assert not any("," in t or "!" in t for t in tokens)


def test_stemming_collapses_forms():
    tokens = tokenize("running runs ran")
    # Porter stemmer should collapse "running"/"runs" to the same root.
    assert tokens[0] == tokens[1]


def test_empty_input():
    assert tokenize("") == []
    assert tokenize(None) == []


if __name__ == "__main__":
    test_lowercases()
    test_removes_stopwords()
    test_strips_punctuation()
    test_stemming_collapses_forms()
    test_empty_input()
    print("All Day 3 tokenizer tests passed.")
