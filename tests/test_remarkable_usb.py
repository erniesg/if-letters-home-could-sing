import unittest
from unittest.mock import patch

from mac_bridge.remarkable_usb import RemarkableUsbDocuments


class UploadResponse:
    status = 201

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class RemarkableUsbDocumentsTests(unittest.TestCase):
    def test_upload_accepts_ferrari_visible_name_with_pdf_extension(self):
        tablet = RemarkableUsbDocuments(timeout_seconds=0.01)
        snapshots = iter(
            (
                [{"ID": "existing-document"}],
                [
                    {"ID": "existing-document"},
                    {
                        "ID": "new-document",
                        "VisibleName": "Letters Home fixture.pdf",
                        "VissibleName": "Letters Home fixture.pdf",
                    },
                ],
            )
        )
        tablet._documents = lambda: next(snapshots)

        with patch(
            "mac_bridge.remarkable_usb.urllib.request.urlopen",
            return_value=UploadResponse(),
        ):
            document_id = tablet.upload_pdf(
                b"%PDF-1.4 fixture",
                filename="Letters Home fixture.pdf",
            )

        self.assertEqual(document_id, "new-document")


if __name__ == "__main__":
    unittest.main()
