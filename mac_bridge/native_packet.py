"""Full-bleed native correspondence packet contracts and renderer."""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path

from .contracts import Letter, Review


PROFILE_DIMENSIONS = {
    "ferrari_3.28.0.162": (954, 1696),
    "chiappa_3.28.0.162": (1620, 2160),
}


@dataclass(frozen=True)
class PacketPage:
    kind: str
    x: int
    y: int
    width: int
    height: int
    chrome_margin: int = 0


@dataclass(frozen=True)
class PacketSpec:
    profile_id: str
    width: int
    height: int
    pages: tuple[PacketPage, ...]


@dataclass(frozen=True)
class CorrectionMark:
    shape: str
    color: str
    label: str
    x1: float
    y1: float
    x2: float
    y2: float


def correction_marks(review: Review, *, width: int, height: int) -> tuple[CorrectionMark, ...]:
    """Map only high-confidence glyph corrections into page coordinates."""

    marks = []
    for annotation in review.annotations:
        if annotation.kind != "correction" or annotation.confidence < 0.8:
            continue
        anchor = annotation.anchor
        marks.append(
            CorrectionMark(
                shape="ellipse",
                color="#b52222",
                label=annotation.suggested_text[:4],
                x1=anchor.x * width,
                y1=height - (anchor.y + anchor.height) * height,
                x2=(anchor.x + anchor.width) * width,
                y2=height - anchor.y * height,
            )
        )
    return tuple(marks)


def packet_spec(profile_id: str) -> PacketSpec:
    try:
        width, height = PROFILE_DIMENSIONS[profile_id]
    except KeyError as error:
        raise ValueError("unknown render profile") from error
    return PacketSpec(
        profile_id,
        width,
        height,
        (
            PacketPage("incoming", 0, 0, width, height),
            PacketPage("huipi", 0, 0, width, height),
        ),
    )


class NativePacketRenderer:
    """Trusted-Mac adapter for PNG/PDF rendering; imported lazily for portable tests."""

    def __init__(self, *, profile_id: str = "ferrari_3.28.0.162", work_dir: Path | None = None):
        self.profile_id = profile_id
        self.work_dir = Path(work_dir or Path.home() / ".local/share/letters-home/rendered")

    def _dimensions(self, profile_id: str | None = None) -> tuple[int, int]:
        return PROFILE_DIMENSIONS[profile_id or self.profile_id]

    @staticmethod
    def _font_name():
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_name = "Helvetica"
        for candidate in (
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        ):
            if not candidate.is_file():
                continue
            try:
                pdfmetrics.registerFont(TTFont("LettersHomeCJK", str(candidate)))
                return "LettersHomeCJK"
            except Exception:
                continue
        return font_name

    @staticmethod
    def _draw_paper(drawing, *, width: int, height: int) -> None:
        from reportlab.lib.colors import HexColor

        drawing.setFillColor(HexColor("#f3ead7"))
        drawing.rect(0, 0, width, height, fill=1, stroke=0)
        inset = max(24, round(width * 0.02))
        drawing.setStrokeColor(HexColor("#c98f87"))
        drawing.setLineWidth(max(1, width / 1600))
        drawing.rect(inset, inset, width - inset * 2, height - inset * 2, fill=0, stroke=1)
        drawing.setStrokeColor(HexColor("#d9aca2"))
        drawing.setLineWidth(max(0.5, width / 2800))
        guide_gap = max(72, round(width * 0.065))
        x = width - inset - guide_gap
        while x > inset + guide_gap:
            drawing.line(x, inset * 1.5, x, height - inset * 1.5)
            x -= guide_gap
        drawing.setStrokeColor(HexColor("#dfcdb4"))
        drawing.line(width * 0.5, inset, width * 0.5, height - inset)

    @staticmethod
    def _draw_vertical_letter(drawing, letter: Letter, *, width: int, height: int, font_name: str) -> None:
        from reportlab.lib.colors import HexColor

        glyphs = [character for character in letter.body if not character.isspace()]
        font_size = max(28, round(height * 0.023))
        line_gap = round(font_size * 1.45)
        column_gap = max(68, round(width * 0.075))
        top = round(height * 0.075)
        bottom = round(height * 0.07)
        right = round(width * 0.08)
        characters_per_column = max(1, (height - top - bottom) // line_gap)
        drawing.setFillColor(HexColor("#263d52"))
        drawing.setFont(font_name, font_size)
        for index, glyph in enumerate(glyphs):
            column, row = divmod(index, characters_per_column)
            x = width - right - column * column_gap
            if x < round(width * 0.07):
                break
            y = height - top - row * line_gap
            drawing.drawCentredString(x, y, glyph)

    def build_initial_packet(self, letter: Letter | None, *, profile_id: str) -> bytes:
        """Render deterministic incoming paper and a blank writable huipi page."""

        try:
            from reportlab.pdfgen import canvas
        except ImportError as error:
            raise RuntimeError("trusted Mac image/PDF dependencies are unavailable") from error
        width, height = self._dimensions(profile_id)
        output = io.BytesIO()
        drawing = canvas.Canvas(output, pagesize=(width, height), pageCompression=1)
        font_name = self._font_name()
        self._draw_paper(drawing, width=width, height=height)
        if letter is not None:
            self._draw_vertical_letter(
                drawing,
                letter,
                width=width,
                height=height,
                font_name=font_name,
            )
        drawing.showPage()
        self._draw_paper(drawing, width=width, height=height)
        drawing.showPage()
        drawing.save()
        return output.getvalue()

    def render_reply_page(self, source_pdf: bytes, *, page_index: int, session_id: str) -> Path:
        if not shutil.which("pdftoppm"):
            raise RuntimeError("pdftoppm is required on the trusted Mac")
        width, height = self._dimensions()
        session_dir = self.work_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        source_path = session_dir / "annotated-source.pdf"
        source_path.write_bytes(source_pdf)
        output_prefix = session_dir / "huipi"
        command = [
            "pdftoppm",
            "-f",
            str(page_index + 1),
            "-l",
            str(page_index + 1),
            "-singlefile",
            "-png",
            "-scale-to-x",
            str(width),
            "-scale-to-y",
            str(height),
            str(source_path),
            str(output_prefix),
        ]
        result = subprocess.run(command, capture_output=True, check=False, timeout=60)
        output = output_prefix.with_suffix(".png")
        if result.returncode != 0 or not output.is_file():
            raise RuntimeError("reply_page_render_failed")
        return output

    def build_reviewed_packet(
        self,
        source_pdf: bytes,
        review: Review,
        *,
        profile_id: str,
        incoming_letter: Letter,
    ) -> tuple[bytes, int]:
        try:
            from pypdf import PdfReader, PdfWriter
            from reportlab.lib.colors import HexColor
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas
        except ImportError as error:
            raise RuntimeError("trusted Mac PDF dependencies are unavailable") from error

        width, height = self._dimensions(profile_id)
        font_name = self._font_name()

        with tempfile.TemporaryDirectory(prefix="letters-home-review-") as temporary_directory:
            temp = Path(temporary_directory)
            source_path = temp / "source.pdf"
            source_path.write_bytes(source_pdf)
            preview = temp / "reply-preview"
            if shutil.which("pdftoppm"):
                subprocess.run(
                    [
                        "pdftoppm",
                        "-f",
                        "2",
                        "-l",
                        "2",
                        "-singlefile",
                        "-png",
                        "-scale-to-x",
                        str(width),
                        "-scale-to-y",
                        str(height),
                        str(source_path),
                        str(preview),
                    ],
                    capture_output=True,
                    check=False,
                    timeout=60,
                )
            preview_path = preview.with_suffix(".png")

            if not preview_path.is_file():
                raise RuntimeError("reply_page_render_failed")

            final_incoming = self.build_initial_packet(incoming_letter, profile_id=profile_id)
            additions_stream = io.BytesIO()
            drawing = canvas.Canvas(additions_stream, pagesize=(width, height), pageCompression=1)

            # Page 3: full-size marked copy. Original page 2 remains untouched in the packet.
            drawing.drawImage(
                ImageReader(str(preview_path)),
                0,
                0,
                width,
                height,
                preserveAspectRatio=False,
            )
            mark_font_size = max(30, round(height * 0.026))
            drawing.setFont(font_name, mark_font_size)
            for mark in correction_marks(review, width=width, height=height):
                drawing.setStrokeColor(HexColor(mark.color))
                drawing.setFillColor(HexColor(mark.color))
                drawing.setLineWidth(max(3, width / 210))
                drawing.ellipse(mark.x1, mark.y1, mark.x2, mark.y2, fill=0, stroke=1)
                label_x = mark.x2 + max(8, width * 0.012)
                if label_x + mark_font_size * max(1, len(mark.label)) > width:
                    label_x = max(0, mark.x1 - mark_font_size * max(1, len(mark.label)) - 8)
                drawing.drawString(
                    label_x,
                    (mark.y1 + mark.y2) / 2 - mark_font_size * 0.35,
                    mark.label,
                )
            for annotation in review.annotations:
                if annotation.kind != "uncertain-reading":
                    continue
                anchor = annotation.anchor
                x1 = anchor.x * width
                x2 = (anchor.x + anchor.width) * width
                y1 = height - (anchor.y + anchor.height) * height
                y2 = height - anchor.y * height
                drawing.setStrokeColor(HexColor("#6f6a63"))
                drawing.setLineWidth(max(1.5, width / 450))
                drawing.setDash(8, 6)
                drawing.ellipse(x1, y1, x2, y2, fill=0, stroke=1)
                drawing.setDash()
            drawing.showPage()

            # Page 4: the correspondent writes back on the shared paper system.
            self._draw_paper(drawing, width=width, height=height)
            self._draw_vertical_letter(
                drawing,
                Letter(review.response_letter),
                width=width,
                height=height,
                font_name=font_name,
            )
            drawing.showPage()

            # Compact teacher notes only; no card grid or unused annotation box.
            if review.annotations or review.summary:
                self._draw_paper(drawing, width=width, height=height)
                margin = round(width * 0.07)
                font_size = max(20, round(height * 0.018))
                line_height = round(font_size * 1.55)
                drawing.setFillColor(HexColor("#263d52"))
                drawing.setFont(font_name, max(28, round(height * 0.027)))
                drawing.drawString(margin, height - margin - line_height, "回批小记")
                drawing.setFont(font_name, font_size)
                y = height - margin - line_height * 2.4
                note_texts = [review.summary]
                note_texts.extend(
                    f"{index}. {item.observed_text} → {item.suggested_text}　{item.explanation}"
                    for index, item in enumerate(review.annotations, start=1)
                )
                note_texts.append(f"问：{review.reflective_question}")
                for note in note_texts:
                    for line in textwrap.wrap(note, width=max(12, round(width / font_size) - 8)) or [""]:
                        if y < margin + line_height:
                            drawing.showPage()
                            self._draw_paper(drawing, width=width, height=height)
                            drawing.setFillColor(HexColor("#263d52"))
                            drawing.setFont(font_name, font_size)
                            y = height - margin - line_height
                        drawing.drawString(margin, y, line)
                        y -= line_height
                    y -= line_height * 0.35
                drawing.showPage()
            drawing.save()

        source_reader = PdfReader(io.BytesIO(source_pdf))
        incoming_reader = PdfReader(io.BytesIO(final_incoming))
        additions_reader = PdfReader(io.BytesIO(additions_stream.getvalue()))
        if len(source_reader.pages) < 2:
            raise RuntimeError("source packet must contain incoming and huipi pages")
        writer = PdfWriter()
        writer.add_page(incoming_reader.pages[0])
        writer.add_page(source_reader.pages[1])
        for page in additions_reader.pages:
            writer.add_page(page)
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue(), len(source_reader.pages)
