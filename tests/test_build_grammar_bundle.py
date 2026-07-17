import pytest

from scripts import build_grammar_bundle
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


def test_compiler_provenance_uses_xcrun_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Apple Clang provenance uses xcrun instead of GCC's unsupported sysroot flag."""
    monkeypatch.setattr(build_grammar_bundle.sys, "platform", "darwin")
    monkeypatch.delenv("SDKROOT", raising=False)
    monkeypatch.delenv("CONDA_BUILD_SYSROOT", raising=False)
    calls: list[tuple[str, ...]] = []

    def fake_output(*args: str, cwd: object = None) -> str:
        assert cwd is None
        return "Apple clang version 17.0.0"

    def fake_run(args: tuple[str, ...], **kwargs: object) -> object:
        calls.append(args)
        assert kwargs == {"check": False, "capture_output": True, "text": True}
        return type("Result", (), {"returncode": 0, "stdout": "/Applications/Xcode.app/SDKs/MacOSX.sdk\n"})()

    monkeypatch.setattr(build_grammar_bundle, "_output", fake_output)
    monkeypatch.setattr(build_grammar_bundle.subprocess, "run", fake_run)

    provenance = build_grammar_bundle._compiler_provenance()

    assert calls == [("xcrun", "--show-sdk-path")]
    assert provenance["compiler_sysroot"] == "/Applications/Xcode.app/SDKs/MacOSX.sdk"
