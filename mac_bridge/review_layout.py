"""Deterministic, bounded review layout independent of PDF rendering."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass

from .contracts import Review


@dataclass(frozen=True)
class LayoutBox:
    kind: str
    x: int
    y: int
    width: int
    height: int
    lines: tuple[str, ...]
    anchor_x: float | None = None
    anchor_y: float | None = None
    annotation_number: int | None = None


@dataclass(frozen=True)
class ReviewPage:
    width: int
    height: int
    boxes: tuple[LayoutBox, ...]


def _wrap(text: str, characters: int) -> tuple[str, ...]:
    return tuple(
        textwrap.wrap(
            text,
            width=max(8, characters),
            break_long_words=True,
            break_on_hyphens=False,
            replace_whitespace=True,
        )
    ) or ("",)


def layout_review(review: Review, *, width: int, height: int) -> tuple[ReviewPage, ...]:
    """Lay out page-three marginalia and paginate overflow without clipping."""

    if width < 800 or height < 600:
        raise ValueError("review canvas is too small")
    margin = max(32, round(width * 0.025))
    top = max(48, round(height * 0.07))
    bottom = margin
    gap = max(20, round(width * 0.015))
    preview_width = round(width * 0.61)
    column_x = margin + preview_width + gap
    column_width = width - column_x - margin
    line_height = max(24, round(height * 0.031))
    box_padding = max(16, round(width * 0.012))
    character_width = max(12, column_width // max(18, round(width / 55)))

    first_boxes = [
        LayoutBox(
            "reply-preview",
            margin,
            top,
            preview_width,
            height - top - bottom,
            ("Original huipi preserved",),
        )
    ]
    summary_lines = _wrap(review.summary, character_width)
    summary_height = box_padding * 2 + line_height * (len(summary_lines) + 1)
    first_boxes.append(
        LayoutBox("summary", column_x, top, column_width, summary_height, summary_lines)
    )
    y = top + summary_height + gap

    pages: list[list[LayoutBox]] = [first_boxes]
    current_page = 0
    for index, annotation in enumerate(review.annotations, start=1):
        prefix = f"{index}. {annotation.observed_text} → {annotation.suggested_text}".rstrip(" →")
        uncertainty = "（不确定）" if annotation.kind == "uncertain-reading" else ""
        lines = _wrap(f"{prefix}{uncertainty}\n{annotation.explanation}", character_width)
        box_height = box_padding * 2 + line_height * len(lines)
        if y + box_height > height - bottom:
            current_page += 1
            pages.append([])
            y = top
        page_x = column_x if current_page == 0 else margin
        page_width = column_width if current_page == 0 else width - margin * 2
        if current_page > 0:
            lines = _wrap(f"{prefix}{uncertainty}\n{annotation.explanation}", max(character_width, 64))
            box_height = box_padding * 2 + line_height * len(lines)
        pages[current_page].append(
            LayoutBox(
                "annotation",
                page_x,
                y,
                page_width,
                box_height,
                lines,
                anchor_x=annotation.anchor.x,
                anchor_y=annotation.anchor.y,
                annotation_number=index,
            )
        )
        y += box_height + gap

    question_lines = _wrap(review.reflective_question, character_width if current_page == 0 else 64)
    question_height = box_padding * 2 + line_height * (len(question_lines) + 1)
    if y + question_height > height - bottom:
        current_page += 1
        pages.append([])
        y = top
    question_x = column_x if current_page == 0 else margin
    question_width = column_width if current_page == 0 else width - margin * 2
    pages[current_page].append(
        LayoutBox("question", question_x, y, question_width, question_height, question_lines)
    )
    return tuple(ReviewPage(width, height, tuple(boxes)) for boxes in pages)
