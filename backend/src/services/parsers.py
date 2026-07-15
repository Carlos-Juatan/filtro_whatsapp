"""
File parser services for the Extrator e Filtro de P&R (Local) tool.

Design (research.md §3 – Factory Pattern):
  - BaseParser: abstract base class defining the parse() contract.
  - TxtParser: concrete implementation for UTF-8 plain-text files.
  - ParserFactory: static factory that returns the appropriate parser by file extension.

Extending support for future formats (e.g. .csv, .md) only requires:
  1. Adding a new concrete class that inherits BaseParser.
  2. Registering the extension in ParserFactory._REGISTRY.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


# ──────────────────────────────────────────────────────────────────────────────
# Abstract base parser
# ──────────────────────────────────────────────────────────────────────────────


class BaseParser(ABC):
    """Contract that every file-format parser must fulfil."""

    @abstractmethod
    def parse(self, file_content: bytes) -> str:
        """
        Decode *file_content* bytes and return the full text as a Python str.

        Args:
            file_content: Raw bytes of the uploaded file.

        Returns:
            The decoded, cleaned text ready for chunking.
        """


# ──────────────────────────────────────────────────────────────────────────────
# Concrete parsers
# ──────────────────────────────────────────────────────────────────────────────


class TxtParser(BaseParser):
    """Parser for plain-text (.txt) files encoded in UTF-8 (with fallback)."""

    def parse(self, file_content: bytes) -> str:
        """
        Decode bytes as UTF-8, replacing any unrecognised sequences, and
        normalise Windows-style CRLF line endings to LF.

        Args:
            file_content: Raw bytes of the .txt file.

        Returns:
            The decoded, CRLF-normalised text string.
        """
        text = file_content.decode("utf-8", errors="ignore")
        # Normalise Windows CRLF → LF for consistent downstream splitting
        return text.replace("\r\n", "\n").replace("\r", "\n")


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────


class ParserFactory:
    """
    Returns the appropriate BaseParser subclass for a given file extension.

    Usage:
        parser = ParserFactory.get_parser(".txt")
        text   = parser.parse(file_bytes)
    """

    # Extension → parser class mapping.  All extensions must be lowercase
    # and include the leading dot (e.g. ".txt").
    _REGISTRY: dict[str, type[BaseParser]] = {
        ".txt": TxtParser,
    }

    @staticmethod
    def get_parser(file_extension: str) -> BaseParser:
        """
        Instantiate and return a parser for *file_extension*.

        Args:
            file_extension: File extension including the dot, e.g. ".txt".
                            Case-insensitive.

        Returns:
            An instance of the matching BaseParser subclass.

        Raises:
            ValueError: If no parser is registered for the given extension.
        """
        normalised = file_extension.lower().strip()
        cls = ParserFactory._REGISTRY.get(normalised)
        if cls is None:
            supported = ", ".join(sorted(ParserFactory._REGISTRY))
            raise ValueError(
                f"Unsupported file format: '{file_extension}'. "
                f"Supported formats: {supported}"
            )
        return cls()

    @staticmethod
    def supported_extensions() -> list[str]:
        """Return a sorted list of supported file extensions (e.g. ['.txt'])."""
        return sorted(ParserFactory._REGISTRY)
