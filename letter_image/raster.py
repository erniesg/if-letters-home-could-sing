"""Dependency-free RGB raster and PNG helpers for letter fixtures."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PIXELS = 8_294_400
MAX_EDGE = 3840


class RasterError(ValueError):
    """Raised when an image cannot be decoded safely."""


@dataclass(frozen=True)
class RasterImage:
    width: int
    height: int
    pixels: bytes

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise RasterError("image dimensions must be positive")
        if len(self.pixels) != self.width * self.height * 3:
            raise RasterError("RGB payload length does not match image dimensions")

    def pixel(self, x: int, y: int) -> tuple[int, int, int]:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError("pixel coordinate is outside the image")
        offset = (y * self.width + x) * 3
        return tuple(self.pixels[offset : offset + 3])


def decode_png(payload: bytes) -> RasterImage:
    """Decode a non-interlaced 8-bit PNG into opaque RGB pixels."""
    if not payload.startswith(PNG_SIGNATURE):
        raise RasterError("asset is not a PNG")

    width = height = color_type = None
    compressed = bytearray()
    position = len(PNG_SIGNATURE)
    saw_end = False
    while position < len(payload):
        if position + 12 > len(payload):
            raise RasterError("PNG chunk is truncated")
        length = struct.unpack(">I", payload[position : position + 4])[0]
        chunk_type = payload[position + 4 : position + 8]
        chunk_end = position + 12 + length
        if chunk_end > len(payload):
            raise RasterError("PNG chunk length is invalid")
        data = payload[position + 8 : position + 8 + length]
        expected_crc = struct.unpack(">I", payload[position + 8 + length : chunk_end])[0]
        if zlib.crc32(chunk_type + data) & 0xFFFFFFFF != expected_crc:
            raise RasterError("PNG chunk checksum does not match")

        if chunk_type == b"IHDR":
            if length != 13 or width is not None:
                raise RasterError("PNG header is invalid")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", data
            )
            if width <= 0 or height <= 0 or max(width, height) > MAX_EDGE:
                raise RasterError("PNG dimensions are outside supported bounds")
            if width * height > MAX_PIXELS:
                raise RasterError("PNG pixel count is outside supported bounds")
            if bit_depth != 8 or color_type not in {0, 2, 4, 6}:
                raise RasterError("PNG must use 8-bit grayscale, RGB, or RGBA pixels")
            if compression != 0 or filtering != 0 or interlace != 0:
                raise RasterError("PNG uses an unsupported encoding")
        elif chunk_type == b"IDAT":
            compressed.extend(data)
        elif chunk_type == b"IEND":
            saw_end = True
            break
        position = chunk_end

    if width is None or height is None or not compressed or not saw_end:
        raise RasterError("PNG is missing required chunks")

    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    stride = width * channels
    expected_length = height * (stride + 1)
    try:
        decompressor = zlib.decompressobj()
        filtered = decompressor.decompress(bytes(compressed), expected_length + 1)
    except zlib.error as error:
        raise RasterError("PNG pixel data is invalid") from error
    if (
        len(filtered) != expected_length
        or not decompressor.eof
        or decompressor.unconsumed_tail
        or decompressor.unused_data
    ):
        raise RasterError("PNG pixel data length does not match its dimensions")

    rows: list[bytes] = []
    previous = bytes(stride)
    for row_index in range(height):
        start = row_index * (stride + 1)
        filter_type = filtered[start]
        encoded = filtered[start + 1 : start + 1 + stride]
        decoded = _unfilter(encoded, previous, channels, filter_type)
        rows.append(decoded)
        previous = decoded

    rgb = bytearray(width * height * 3)
    output = 0
    for row in rows:
        for offset in range(0, len(row), channels):
            if color_type == 0:
                red = green = blue = row[offset]
                alpha = 255
            elif color_type == 2:
                red, green, blue = row[offset : offset + 3]
                alpha = 255
            elif color_type == 4:
                red = green = blue = row[offset]
                alpha = row[offset + 1]
            else:
                red, green, blue, alpha = row[offset : offset + 4]
            for component in (red, green, blue):
                rgb[output] = (component * alpha + 255 * (255 - alpha) + 127) // 255
                output += 1
    return RasterImage(width, height, bytes(rgb))


def encode_png(image: RasterImage) -> bytes:
    """Encode RGB pixels as a deterministic non-interlaced PNG."""
    stride = image.width * 3
    scanlines = b"".join(
        b"\x00" + image.pixels[offset : offset + stride]
        for offset in range(0, len(image.pixels), stride)
    )
    header = struct.pack(">IIBBBBB", image.width, image.height, 8, 2, 0, 0, 0)
    return PNG_SIGNATURE + _chunk(b"IHDR", header) + _chunk(
        b"IDAT", zlib.compress(scanlines, level=9)
    ) + _chunk(b"IEND", b"")


def _chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


def _unfilter(encoded: bytes, previous: bytes, bytes_per_pixel: int, filter_type: int) -> bytes:
    decoded = bytearray(len(encoded))
    for index, value in enumerate(encoded):
        left = decoded[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        above = previous[index]
        upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        if filter_type == 0:
            predictor = 0
        elif filter_type == 1:
            predictor = left
        elif filter_type == 2:
            predictor = above
        elif filter_type == 3:
            predictor = (left + above) // 2
        elif filter_type == 4:
            predictor = _paeth(left, above, upper_left)
        else:
            raise RasterError("PNG uses an unknown row filter")
        decoded[index] = (value + predictor) & 0xFF
    return bytes(decoded)


def _paeth(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    left_distance = abs(estimate - left)
    above_distance = abs(estimate - above)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left
