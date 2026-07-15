"""Bounded adapter for reMarkable's enabled USB web interface."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
import uuid
from typing import Any


class RemarkableUsbDocuments:
    def __init__(self, *, base_url: str = "http://10.11.99.1", timeout_seconds: float = 45):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _open(self, request: urllib.request.Request) -> bytes:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            raise RuntimeError("remarkable_usb_unreachable") from error

    def _documents(self) -> list[dict[str, Any]]:
        payload = self._open(urllib.request.Request(f"{self.base_url}/documents/", method="GET"))
        decoded = json.loads(payload)
        if not isinstance(decoded, list):
            raise RuntimeError("remarkable_documents_invalid")
        return [item for item in decoded if isinstance(item, dict)]

    def export_pdf(self, document_id: str) -> bytes:
        if not document_id or any(character not in "0123456789abcdef-" for character in document_id.lower()):
            raise ValueError("invalid document id")
        return self._open(
            urllib.request.Request(
                f"{self.base_url}/download/{document_id}/pdf",
                method="GET",
            )
        )

    def upload_pdf(self, payload: bytes, *, filename: str) -> str:
        if not payload.startswith(b"%PDF-"):
            raise ValueError("upload is not a PDF")
        if not filename.endswith(".pdf") or "/" in filename or "\\" in filename:
            raise ValueError("invalid upload filename")
        before = {item.get("ID") for item in self._documents() if isinstance(item.get("ID"), str)}
        boundary = f"letters-home-{uuid.uuid4().hex}"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8") + payload + f"\r\n--{boundary}--\r\n".encode("ascii")
        request = urllib.request.Request(
            f"{self.base_url}/upload",
            data=body,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                if response.status != 201:
                    raise RuntimeError("remarkable_upload_failed")
        except (urllib.error.URLError, TimeoutError) as error:
            raise RuntimeError("remarkable_upload_failed") from error

        expected_names = {filename, filename[:-4]}
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            matches = [
                item["ID"]
                for item in self._documents()
                if isinstance(item.get("ID"), str)
                and item["ID"] not in before
                and (item.get("VissibleName") or item.get("VisibleName")) in expected_names
            ]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise RuntimeError("remarkable_upload_ambiguous")
            time.sleep(0.25)
        raise RuntimeError("remarkable_upload_not_visible")
