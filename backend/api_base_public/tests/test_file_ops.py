import tempfile
import unittest

from fastapi import HTTPException

from app.services.comic.file_ops import (
    allowed_file,
    validate_magic_bytes,
    validate_session,
    resolve_safe_file,
    create_media_access_token,
    verify_media_access_token,
)


class FileOpsTests(unittest.TestCase):
    def test_allowed_file(self):
        self.assertTrue(allowed_file("page.jpg"))
        self.assertTrue(allowed_file("cover.PNG"))
        self.assertFalse(allowed_file("archive.zip"))
        self.assertFalse(allowed_file("no_extension"))

    def test_validate_magic_bytes(self):
        self.assertTrue(validate_magic_bytes(b"\xff\xd8\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00", "jpg"))
        self.assertFalse(validate_magic_bytes(b"not_an_image", "png"))
        self.assertTrue(validate_magic_bytes(b"RIFF1234WEBPabcd", "webp"))

    def test_validate_session_rejects_path_traversal(self):
        with self.assertRaises(HTTPException):
            validate_session("../escape")

    def test_resolve_safe_file_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(HTTPException):
                resolve_safe_file(tmpdir, "../secret.txt")

    def test_media_token_roundtrip(self):
        secret_key = "unit-test-secret"
        token = create_media_access_token("session123", 99, secret_key)

        verify_media_access_token("session123", token, secret_key)

        with self.assertRaises(HTTPException):
            verify_media_access_token("another-session", token, secret_key)


if __name__ == "__main__":
    unittest.main()
