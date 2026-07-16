from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from logging import getLogger

from tree_sitter import Language, Node, Parser
from tree_sitter_language_pack import LanguageNotFoundError, SupportedLanguage, get_parser

from semble._offline import OfflineAssetError, activate_bundled_grammars, grammar_library_path, grammar_symbol
from semble.index.files import ALL_LANGUAGES

logger = getLogger(__name__)

_RECURSION_DEPTH = 500
_MIN_CHUNK_SIZE = 50


def is_supported_language(language: str) -> bool:
    """Check if the language is supported by tree-sitter."""
    return language in ALL_LANGUAGES


@dataclass
class ChunkBoundary:
    """The output of the internal chunking algorithm."""

    start: int
    end: int


def _parser_from_installed_package(language: str) -> Parser | None:
    """Build a parser from an individually pip-installed ``tree-sitter-<language>`` wheel.

    Grammar wheels published by the tree-sitter org (e.g. ``tree-sitter-python``)
    expose a ``language()`` entry point. This requires no network access at
    runtime and works in firewalled environments where
    tree-sitter-language-pack's lazy download fails.
    """
    from importlib import import_module

    module_name = f"tree_sitter_{grammar_symbol(language)}"
    try:
        module = import_module(module_name)
        return Parser(Language(module.language()))
    except ModuleNotFoundError:
        return None
    except Exception:
        logger.warning("%s is installed but could not be loaded", module_name, exc_info=True)
        return None


@cache
def _cached_get_parser(language: SupportedLanguage) -> Parser | None:
    """Gets a parser from tree_sitter.

    Resolution order is the local language-pack cache, an individually installed
    grammar wheel, then line chunking. No runtime download is attempted.
    """
    language_name = str(language)
    try:
        library = grammar_library_path(language_name)
    except OfflineAssetError as error:
        fallback = _parser_from_installed_package(language_name)
        if fallback is not None:
            return fallback
        logger.error("Offline grammar assets are unavailable: %s", error)
        return None

    if library is None:
        fallback = _parser_from_installed_package(language_name)
        if fallback is not None:
            return fallback
        logger.warning("Language %s is not bundled; falling back to line chunking", language_name)
        return None

    try:
        activate_bundled_grammars()
        return get_parser(language)
    except LanguageNotFoundError:
        fallback = _parser_from_installed_package(language_name)
        if fallback is not None:
            return fallback
        logger.warning("Language %s could not be loaded; falling back to line chunking", language_name)
    except Exception:
        logger.error("Uncaught exception in _cached_get_parser", exc_info=True)
    return None


def _merge_adjacent_chunks(
    chunks: list[ChunkBoundary],
    desired_length: int,
) -> list[ChunkBoundary]:
    """Merge adjacent chunks up to the desired length."""
    merged = []

    current_start = chunks[0].start
    current_end = chunks[0].end
    current_length = current_end - current_start

    for group in chunks[1:]:
        start, end = group.start, group.end
        length = end - start

        if current_length + length > desired_length:
            merged.append(ChunkBoundary(start=current_start, end=current_end))
            current_start = start
            current_end = end
            current_length = length
            continue

        current_end = end
        current_length += length

    merged.append(ChunkBoundary(start=current_start, end=current_end))

    return merged


def _merge_node_inner(node: Node, desired_length: int, i: int) -> list[ChunkBoundary]:
    """Recursively merge and split nodes."""
    # If there are no child nodes, the only thing we can do is return the current node.
    if not node.children:
        return [ChunkBoundary(node.start_byte, node.end_byte)]

    length = node.end_byte - node.start_byte
    # Prevent recursion issues. A depth of > 500 is unlikely
    if i > _RECURSION_DEPTH:
        logger.warning("Recursion depth exceeded in chunk.")
        return [ChunkBoundary(node.start_byte, node.end_byte)]
    # Prevent recursing into short chunks.
    if length < _MIN_CHUNK_SIZE:
        return [ChunkBoundary(node.start_byte, node.end_byte)]

    groups: list[ChunkBoundary] = []
    children = node.children
    index = 0

    while index < len(children):
        child = children[index]
        start = child.start_byte
        end = child.end_byte
        length = child.end_byte - child.start_byte

        # Increment the pointer, as we accessed a child node.
        index += 1
        # If this single chunk is longer than the desired length
        # we try to split it again.
        if length > desired_length:
            groups.extend(_merge_node_inner(child, desired_length, i + 1))
            continue

        while index < len(children):
            # Extend the current group with or more children, if they fit.
            child = children[index]
            child_length = child.end_byte - child.start_byte

            if length + child_length > desired_length:
                break

            end = child.end_byte
            length += child_length
            index += 1

        groups.append(ChunkBoundary(start, end))

    return groups


def _merge_node(node: Node, desired_length: int) -> list[ChunkBoundary]:
    """Recursively turn nodes into chunks, then merge adjacent chunks."""
    raw_chunks = _merge_node_inner(node, desired_length, 0)
    return _merge_adjacent_chunks(raw_chunks, desired_length)


def chunk_lines(text: str, desired_length: int) -> list[ChunkBoundary]:
    """Chunk source code by line."""
    if not text.strip():
        return []
    lines_as_groups = []
    index = 0
    for line in text.splitlines(keepends=True):
        lines_as_groups.append(ChunkBoundary(start=index, end=index + len(line)))
        index += len(line)

    return _merge_adjacent_chunks(lines_as_groups, desired_length)


def chunk(text: str, language: str, desired_length: int) -> list[ChunkBoundary] | None:
    """Chunk source code."""
    if not text.strip():
        return []

    as_bytes = text.encode("utf-8")
    parser = _cached_get_parser(language)
    if parser is None:
        return None
    root = parser.parse(as_bytes).root_node

    chunks = []
    for chunk_boundary in _merge_node(root, desired_length):
        start_char = len(as_bytes[: chunk_boundary.start].decode("utf-8"))
        end_char = len(as_bytes[: chunk_boundary.end].decode("utf-8"))
        chunks.append(ChunkBoundary(start=start_char, end=end_char))

    return chunks
