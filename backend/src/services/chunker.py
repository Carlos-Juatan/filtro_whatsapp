"""
Token-based text chunker for the Extrator e Filtro de P&R (Local) tool.

Design (research.md §2 – Text Chunking Strategy):
  - Encoding: tiktoken cl100k_base (standard for gpt-4o / gpt-4o-mini).
  - Chunk size limit: MAX_TOKENS = 8 000 tokens per chunk.
  - Split hierarchy (in priority order):
      1. If the whole text fits in one chunk → return as-is.
      2. Try splitting on double newlines (paragraph breaks).
      3. Fall back to single newlines (line breaks).
      4. Fall back to sentence delimiters (. / ? / !).
      5. Hard-split on token boundaries as last resort.
  - The algorithm accumulates segments until the next one would exceed the
    token limit, at which point it flushes the current chunk and starts a new one.
"""

from __future__ import annotations

import re
from typing import Sequence

import tiktoken

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

ENCODING_NAME: str = "cl100k_base"
MAX_TOKENS: int = 5_000  # capped to leave room for the JSON response output


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────


def _get_encoding() -> tiktoken.Encoding:
    """Return (and cache) the cl100k_base tiktoken encoding."""
    return tiktoken.get_encoding(ENCODING_NAME)


def _token_count(text: str, enc: tiktoken.Encoding) -> int:
    """Return the number of tokens in *text* using *enc*."""
    return len(enc.encode(text))


def _pack_segments(
    segments: Sequence[str],
    max_tokens: int,
    enc: tiktoken.Encoding,
    separator: str = "",
) -> list[str]:
    """
    Greedily pack *segments* into chunks so that each chunk's token count
    stays within *max_tokens*.

    Args:
        segments:   Ordered list of text segments to pack.
        max_tokens: Maximum tokens per output chunk.
        enc:        tiktoken encoding used for counting.
        separator:  String inserted between consecutive segments inside one chunk.

    Returns:
        A list of non-empty chunk strings.
    """
    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens: int = 0

    for seg in segments:
        if not seg.strip():
            continue  # skip empty / whitespace-only segments

        seg_tokens = _token_count(seg, enc)

        # If a single segment is larger than the limit, it must be split
        # further (recursive call handled at the call site).
        if current_tokens + seg_tokens + (len(current_parts) > 0) * _token_count(separator, enc) > max_tokens:
            if current_parts:
                chunks.append(separator.join(current_parts))
            current_parts = [seg]
            current_tokens = seg_tokens
        else:
            current_parts.append(seg)
            current_tokens += seg_tokens + (
                _token_count(separator, enc) if len(current_parts) > 1 else 0
            )

    if current_parts:
        chunks.append(separator.join(current_parts))

    return chunks


def _split_by_sentences(text: str) -> list[str]:
    """
    Split *text* on sentence-ending punctuation (. ? !).
    The delimiter is kept at the end of each sentence fragment.
    """
    # Keep the delimiter attached to the preceding sentence
    parts = re.split(r"(?<=[.?!])\s+", text)
    return [p for p in parts if p.strip()]


def _hard_split(text: str, max_tokens: int, enc: tiktoken.Encoding) -> list[str]:
    """
    Split *text* purely by token count when no linguistic boundary is available.
    Operates on the token ids and decodes each slice back to a string.
    """
    tokens = enc.encode(text)
    chunks: list[str] = []
    for start in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[start : start + max_tokens]
        chunks.append(enc.decode(chunk_tokens))
    return chunks


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────


def split_text(text: str, max_tokens: int = MAX_TOKENS) -> list[str]:
    """
    Split *text* into token-safe chunks using a hierarchical splitting strategy.

    Args:
        text:       The full input text to split.
        max_tokens: Maximum token count per output chunk (default: 8 000).

    Returns:
        A list of non-empty string chunks, each ≤ *max_tokens* tokens.
        Returns an empty list when *text* is blank.

    Raises:
        ValueError: If *max_tokens* is less than 1.
    """
    if max_tokens < 1:
        raise ValueError(f"max_tokens must be ≥ 1, got {max_tokens}.")

    stripped = text.strip()
    if not stripped:
        return []

    enc = _get_encoding()
    total_tokens = _token_count(stripped, enc)

    # ── Step 1: fits in a single chunk ────────────────────────────────────────
    if total_tokens <= max_tokens:
        return [stripped]

    # ── Step 2: split on paragraph breaks (double newlines) ──────────────────
    paragraphs = [p.strip() for p in stripped.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        chunks = _pack_segments(paragraphs, max_tokens, enc, separator="\n\n")
        # Recursively split any chunk that is still too large
        result: list[str] = []
        for chunk in chunks:
            if _token_count(chunk, enc) > max_tokens:
                result.extend(split_text(chunk, max_tokens))
            else:
                result.append(chunk)
        return result

    # ── Step 3: split on single newlines (line breaks) ───────────────────────
    lines = [ln.strip() for ln in stripped.split("\n") if ln.strip()]
    if len(lines) > 1:
        chunks = _pack_segments(lines, max_tokens, enc, separator="\n")
        result = []
        for chunk in chunks:
            if _token_count(chunk, enc) > max_tokens:
                result.extend(split_text(chunk, max_tokens))
            else:
                result.append(chunk)
        return result

    # ── Step 4: split on sentence punctuation ────────────────────────────────
    sentences = _split_by_sentences(stripped)
    if len(sentences) > 1:
        chunks = _pack_segments(sentences, max_tokens, enc, separator=" ")
        result = []
        for chunk in chunks:
            if _token_count(chunk, enc) > max_tokens:
                result.extend(split_text(chunk, max_tokens))
            else:
                result.append(chunk)
        return result

    # ── Step 5: hard token-boundary split (last resort) ──────────────────────
    return _hard_split(stripped, max_tokens, enc)


def count_tokens(text: str) -> int:
    """
    Return the cl100k_base token count for *text*.
    Convenience wrapper exposed for external callers and tests.
    """
    enc = _get_encoding()
    return _token_count(text, enc)
