"""Deterministic vertical glyph placement for the Ferrari correspondence page."""

from __future__ import annotations

import re
from dataclasses import dataclass


TERMINATORS = frozenset("。！？")
ATTACHED_PUNCTUATION = frozenset("，。、；：！？）】》”’")
_COMPLETE_SENTENCE = re.compile(r".*?[。！？]", re.DOTALL)


@dataclass(frozen=True)
class GridSpec:
    width: int = 954
    height: int = 1696
    columns: int = 10
    rows: int = 18
    left: float = 72
    top: float = 104
    right: float = 882
    bottom: float = 1592

    @property
    def capacity(self) -> int:
        return self.columns * self.rows


@dataclass(frozen=True)
class GlyphPlacement:
    glyph: str
    index: int
    column: int
    row: int
    x: float
    y: float
    punctuation: bool


FERRARI_GRID = GridSpec()


def _place_glyph(
    glyph: str,
    *,
    index: int,
    cell: int,
    spec: GridSpec,
) -> GlyphPlacement:
    column, row = divmod(cell, spec.rows)
    if column >= spec.columns:
        raise ValueError("letter_grid_overflow")
    cell_width = (spec.right - spec.left) / spec.columns
    cell_height = (spec.bottom - spec.top) / spec.rows
    x = spec.right - (column + 0.5) * cell_width
    y = spec.top + (row + 0.5) * cell_height
    punctuation = glyph in ATTACHED_PUNCTUATION
    if punctuation:
        x += cell_width * 0.18
        y -= cell_height * 0.18
    return GlyphPlacement(glyph, index, column, row, x, y, punctuation)


def place_vertical(
    text: str,
    spec: GridSpec = FERRARI_GRID,
) -> tuple[GlyphPlacement, ...]:
    """Place one glyph per cell, reserving cells to avoid leading punctuation."""

    if not isinstance(text, str):
        raise TypeError("letter must be text")
    if len(text) > spec.capacity:
        raise ValueError("letter_grid_overflow")

    result: list[GlyphPlacement] = []
    next_cell = 0
    for index, glyph in enumerate(text):
        if glyph in ATTACHED_PUNCTUATION and next_cell % spec.rows == 0:
            if not result:
                raise ValueError("letter_grid_leading_punctuation")
            move_start = len(result) - 1
            while move_start > 0 and result[move_start].punctuation:
                move_start -= 1
            moving = result[move_start:]
            del result[move_start:]
            if len(moving) + 1 > spec.rows:
                raise ValueError("letter_grid_overflow")
            for prior in moving:
                result.append(
                    _place_glyph(
                        prior.glyph,
                        index=prior.index,
                        cell=next_cell,
                        spec=spec,
                    )
                )
                next_cell += 1

        result.append(_place_glyph(glyph, index=index, cell=next_cell, spec=spec))
        next_cell += 1

    return tuple(result)


class SentenceStream:
    """Publish cumulative, immutable complete-sentence prefixes."""

    def __init__(self, spec: GridSpec = FERRARI_GRID, *, minimum: int):
        if minimum < 0 or minimum > spec.capacity:
            raise ValueError("letter_grid_invalid_minimum")
        self.spec = spec
        self.minimum = minimum
        self._pending = ""
        self._published = ""
        self._sealed = False

    @property
    def published(self) -> str:
        return self._published

    def append(self, delta: str) -> str:
        if not isinstance(delta, str):
            raise TypeError("letter delta must be text")
        if not delta or self._sealed:
            return self._published
        self._pending += delta
        while True:
            match = _COMPLETE_SENTENCE.match(self._pending)
            if match is None:
                break
            sentence = match.group(0)
            candidate = self._published + sentence
            try:
                place_vertical(candidate, self.spec)
            except ValueError as error:
                if str(error) not in {
                    "letter_grid_overflow",
                    "letter_grid_leading_punctuation",
                }:
                    raise
                self._sealed = True
                break
            self._published = candidate
            self._pending = self._pending[len(sentence) :]
        return self._published

    def finalize(self) -> str:
        if len(self._published) < self.minimum:
            raise ValueError("letter_grid_underflow")
        return self._published


def glyph_dicts(
    text: str,
    spec: GridSpec = FERRARI_GRID,
) -> tuple[dict[str, object], ...]:
    """Return a JSON-safe render model for the non-interactive QML layer."""

    return tuple(
        {
            "glyph": item.glyph,
            "index": item.index,
            "column": item.column,
            "row": item.row,
            "x": item.x,
            "y": item.y,
            "punctuation": item.punctuation,
        }
        for item in place_vertical(text, spec)
    )
