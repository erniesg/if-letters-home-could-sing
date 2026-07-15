"""Full-bleed native correspondence packet contracts and renderer."""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .contracts import Review
from .review_layout import layout_review


PROFILE_DIMENSIONS = {
    "ferrari_3.28.0.162": (1696, 954),
    "chiappa_3.28.0.162": (2160, 1620),
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

    def build_initial_packet(self, image_path: Path, *, profile_id: str) -> bytes:
        """Render an edge-to-edge incoming page followed by deterministic huipi paper."""

        try:
            from PIL import Image, ImageOps
            from reportlab.lib.colors import HexColor
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfgen import canvas
        except ImportError as error:
            raise RuntimeError("trusted Mac image/PDF dependencies are unavailable") from error
        width, height = self._dimensions(profile_id)
        image_path = Path(image_path)
        if not image_path.is_file():
            raise ValueError("incoming image does not exist")
        rendered = ImageOps.fit(
            Image.open(image_path).convert("RGB"),
            (width, height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )
        rendered_stream = io.BytesIO()
        rendered.save(rendered_stream, format="PNG", optimize=True)
        output = io.BytesIO()
        drawing = canvas.Canvas(output, pagesize=(width, height), pageCompression=1)
        drawing.drawImage(
            ImageReader(io.BytesIO(rendered_stream.getvalue())),
            0,
            0,
            width,
            height,
            preserveAspectRatio=False,
        )
        drawing.showPage()

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
    ) -> tuple[bytes, int]:
        try:
            from pypdf import PdfReader, PdfWriter
            from reportlab.lib.colors import Color, HexColor
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            from reportlab.pdfgen import canvas
        except ImportError as error:
            raise RuntimeError("trusted Mac PDF dependencies are unavailable") from error

        width, height = self._dimensions(profile_id)
        pages = layout_review(review, width=width, height=height)
        font_name = "Helvetica"
        for candidate in (
            Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        ):
            if candidate.is_file():
                try:
                    pdfmetrics.registerFont(TTFont("LettersHomeCJK", str(candidate)))
                    font_name = "LettersHomeCJK"
                    break
                except Exception:
                    continue

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

            review_stream = io.BytesIO()
            drawing = canvas.Canvas(review_stream, pagesize=(width, height), pageCompression=1)
            for page_number, page in enumerate(pages, start=1):
                preview_geometry = None
                drawing.setFillColor(HexColor("#f3ead7"))
                drawing.rect(0, 0, width, height, fill=1, stroke=0)
                drawing.setFillColor(HexColor("#33475b"))
                drawing.setFont(font_name, max(22, round(height * 0.038)))
                drawing.drawString(
                    round(width * 0.025),
                    height - round(height * 0.05),
                    "回批 · A reading of your reply",
                )
                drawing.setFont(font_name, max(12, round(height * 0.018)))
                drawing.drawRightString(width - round(width * 0.025), height - round(height * 0.05), f"{page_number}/{len(pages)}")
                for box in page.boxes:
                    pdf_y = height - box.y - box.height
                    if box.kind == "reply-preview" and preview_path.is_file():
                        scale = min(box.width / width, box.height / height)
                        preview_width = width * scale
                        preview_height = height * scale
                        preview_x = box.x + (box.width - preview_width) / 2
                        preview_y = pdf_y + (box.height - preview_height) / 2
                        drawing.drawImage(
                            ImageReader(str(preview_path)),
                            preview_x,
                            preview_y,
                            preview_width,
                            preview_height,
                            preserveAspectRatio=False,
                        )
                        drawing.setStrokeColor(Color(0.35, 0.25, 0.2, alpha=0.35))
                        drawing.rect(
                            preview_x,
                            preview_y,
                            preview_width,
                            preview_height,
                            fill=0,
                            stroke=1,
                        )
                        preview_geometry = (preview_x, preview_y, preview_width, preview_height)
                        continue
                    if (
                        box.kind == "annotation"
                        and preview_geometry
                        and box.anchor_x is not None
                        and box.anchor_y is not None
                        and box.annotation_number is not None
                    ):
                        preview_x, preview_y, preview_width, preview_height = preview_geometry
                        marker_x = preview_x + box.anchor_x * preview_width
                        marker_y = preview_y + (1 - box.anchor_y) * preview_height
                        drawing.setStrokeColor(HexColor("#a04d46"))
                        drawing.setLineWidth(max(1.5, width / 900))
                        drawing.line(marker_x, marker_y, box.x, pdf_y + box.height / 2)
                        radius = max(11, round(height * 0.014))
                        drawing.setFillColor(HexColor("#a04d46"))
                        drawing.circle(marker_x, marker_y, radius, fill=1, stroke=0)
                        drawing.setFillColor(HexColor("#fffaf0"))
                        drawing.setFont(font_name, max(11, round(height * 0.015)))
                        drawing.drawCentredString(
                            marker_x,
                            marker_y - radius * 0.38,
                            str(box.annotation_number),
                        )
                    fill = "#fffaf0" if box.kind != "question" else "#e8dec8"
                    drawing.setFillColor(HexColor(fill))
                    drawing.roundRect(box.x, pdf_y, box.width, box.height, 14, fill=1, stroke=0)
                    drawing.setFillColor(HexColor("#243746"))
                    drawing.setFont(font_name, max(15, round(height * 0.022)))
                    line_height = max(24, round(height * 0.031))
                    text_y = pdf_y + box.height - max(18, round(width * 0.012)) - line_height
                    if box.kind == "question":
                        drawing.drawString(box.x + 18, text_y, "留给下一封信的问题")
                        text_y -= line_height
                    for line in box.lines:
                        drawing.drawString(box.x + 18, text_y, line)
                        text_y -= line_height
                drawing.showPage()
            drawing.save()

        source_reader = PdfReader(io.BytesIO(source_pdf))
        review_reader = PdfReader(io.BytesIO(review_stream.getvalue()))
        if len(source_reader.pages) < 2:
            raise RuntimeError("source packet must contain incoming and huipi pages")
        writer = PdfWriter()
        for page in source_reader.pages:
            writer.add_page(page)
        for page in review_reader.pages:
            writer.add_page(page)
        output = io.BytesIO()
        writer.write(output)
        return output.getvalue(), len(source_reader.pages)
