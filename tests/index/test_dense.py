import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from vicinity.backends.basic import BasicArgs

from semble.index.create import create_index_from_path
from semble.index.dense import SelectableBasicBackend, embed_chunks


def test_save_load_roundtrip(tmp_path: Path) -> None:
    """Test save and load roundtrip."""
    vecs = np.random.default_rng(seed=42).normal(size=(10, 32))
    args = BasicArgs()
    selectable = SelectableBasicBackend(vecs, args)
    selectable.save(tmp_path)

    selectable_2 = SelectableBasicBackend.load(tmp_path)
    assert np.allclose(selectable.vectors, selectable_2.vectors)


@pytest.mark.parametrize("module_name", ["benchmarks.baselines.coderankembed", "benchmarks.speed_benchmark"])
def test_coderankembed_adapter_indexing(
    module_name: str, mock_model: Any, tmp_py_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both benchmark adapters index batches and preserve asymmetric query prompts."""
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=object))
    monkeypatch.setattr("semble.utils.DEFAULT_MODEL_NAME", "unused-benchmark-model", raising=False)
    module = importlib.import_module(module_name)
    mock_model.get_sentence_embedding_dimension.return_value = mock_model.dim
    adapter = module._AsymmetricWrapper(mock_model)

    _, semantic_index, chunks, _ = create_index_from_path(tmp_py_file.parent, adapter)
    assert semantic_index.vectors.shape == (len(chunks), mock_model.dim)
    assert all("prompt_name" not in call.kwargs for call in mock_model.encode.call_args_list)
    assert embed_chunks(adapter, []).shape == (0, mock_model.dim)

    mock_model.encode.reset_mock()
    adapter.encode(["find authentication"])
    mock_model.encode.assert_called_once_with(["find authentication"], prompt_name="query", batch_size=1)
