import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import comic_projects
from app.security.security import get_current_user


class FakeCursorOwnerMismatch:
    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchone(self):
        return {"user_id": 999}

    def close(self):
        return None


class FakeConnectionOwnerMismatch:
    def cursor(self, dictionary=False):
        return FakeCursorOwnerMismatch()

    def close(self):
        return None


class ComicProjectsApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = FastAPI()
        app.include_router(comic_projects.router)

        def override_user():
            return {"id": 1, "username": "test_user", "email": "test@example.com"}

        app.dependency_overrides[get_current_user] = override_user
        cls.client = TestClient(app)

    def test_delete_project_forbidden_when_session_owned_by_other_user(self):
        with patch("app.services.comic.session_access.get_mysql_connection", return_value=FakeConnectionOwnerMismatch()):
            response = self.client.delete("/comic/projects/session-foreign")

        self.assertEqual(response.status_code, 403)
        self.assertIn("không có quyền", response.json().get("detail", "").lower())

    def test_get_projects_returns_fallback_when_db_error(self):
        with patch("app.db.query_helpers.get_mysql_connection", side_effect=Exception("db down")):
            response = self.client.get("/comic/projects")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload.get("projects"), [])
        self.assertEqual(payload.get("total"), 0)
        self.assertEqual(payload.get("user_id"), 1)


if __name__ == "__main__":
    unittest.main()
