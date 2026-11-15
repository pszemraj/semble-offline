import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def speed_benchmark(monkeypatch: pytest.MonkeyPatch) -> tuple[ModuleType, list[tuple[str, dict[str, object]]]]:
    """The speed benchmark module with its benchmarking and result saving replaced by stubs; also returns saves."""
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=object))
    monkeypatch.setattr("semble.utils.DEFAULT_MODEL_NAME", "unused-benchmark-model", raising=False)
    module = importlib.import_module("benchmarks.speed_benchmark")
    saves: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(
        module, "available_repo_specs", lambda: {r: SimpleNamespace(language="x") for r in module._REPOS}
    )
    monkeypatch.setattr(module, "load_tasks", lambda repo_specs: [])
    monkeypatch.setattr(module, "load_model", lambda name: None)
    monkeypatch.setattr(module, "_run_tool", lambda tool, spec, tasks, index, model: ((1.0, (1.0, 2.0)), index))
    monkeypatch.setattr(module, "save_results", lambda name, payload: saves.append((name, payload)) or "out.json")
    return module, saves


def test_speed_benchmark_saves_only_unfiltered_runs(
    speed_benchmark: tuple[ModuleType, list[tuple[str, dict[str, object]]]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A --repo run leaves the full-run results file alone; an unfiltered run saves the repos it covered."""
    module, saves = speed_benchmark
    repo = module._REPOS[0]

    monkeypatch.setattr(sys, "argv", ["speed_benchmark", "--tools", "ripgrep", "--repo", repo])
    module.main()
    assert saves == []

    monkeypatch.setattr(sys, "argv", ["speed_benchmark", "--tools", "ripgrep"])
    module.main()
    assert [(name, payload["repos"]) for name, payload in saves] == [("speed", module._REPOS)]
