import pytest

from scripts.build_grammar_bundle import validate_sources


def test_validate_sources_accepts_exact_pin() -> None:
    """Exact source, revision, symbol, and license metadata is accepted."""
    sources = {
        "csharp": {
            "library": "libtree_sitter_c_sharp.so",
            "license": "MIT",
            "repository": "https://github.com/tree-sitter/tree-sitter-c-sharp",
            "revision": "abc123",
        }
    }
    definitions = {
        "csharp": {
            "c_symbol": "c_sharp",
            "repo": "https://github.com/tree-sitter/tree-sitter-c-sharp",
            "rev": "abc123",
        }
    }
    validate_sources(sources, definitions, {"tree-sitter/tree-sitter-c-sharp": "MIT"})


def test_validate_sources_rejects_revision_drift() -> None:
    """A definition revision different from the fork's pin is rejected."""
    sources = {
        "python": {
            "library": "libtree_sitter_python.so",
            "license": "MIT",
            "repository": "https://github.com/tree-sitter/tree-sitter-python",
            "revision": "old",
        }
    }
    definitions = {
        "python": {
            "repo": "https://github.com/tree-sitter/tree-sitter-python",
            "rev": "new",
        }
    }
    with pytest.raises(RuntimeError, match="revision"):
        validate_sources(sources, definitions, {"tree-sitter/tree-sitter-python": "MIT"})
