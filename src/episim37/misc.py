"""Miscellaneous code."""

from __future__ import annotations

import attrs
import rich
import rich.markup


@attrs.define
class SourcePosition:
    """Position in source."""

    source: str
    source_bytes: bytes
    start: tuple[int, int]  # line, col: zero indexed
    end: tuple[int, int]  # line, col: zero indexed
    byte_range: tuple[int, int]  # zero indexed

    @property
    def line(self):
        return self.start[0] + 1

    @property
    def col(self):
        return self.start[1] + 1

    @property
    def bytes(self) -> bytes:
        return self.source_bytes[self.byte_range[0] : self.byte_range[1]]

    @property
    def text(self) -> str:
        return self.bytes.decode()


class EslError(Exception):
    """Error attributable to a section of the code."""

    def __init__(self, short: str, long: str, pos: SourcePosition):
        """
        Initialize.

        :param short: short description of error.
        :param long: longer description of error.
        :param pos: position in source.
        """

        super().__init__()
        self.short = short
        self.long = long
        self.pos = pos

    def __str__(self):
        return self.short

    def rich_print(self):
        etype = f"[red]{self.short}[/red]"
        fpath = f"[yellow]{self.pos.source}[/yellow]"
        line = self.pos.line
        col = self.pos.col
        expl = rich.markup.escape(self.long)

        rich.print(f"{etype}:{fpath}:{line}:{col}:{expl}")
        print(self.pos.text)
