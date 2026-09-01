import io
import shutil
import tempfile
from pathlib import Path
import pytest
from app import create_app
from app.config import Config
from tests.test_converter import SAMPLE_VALID_PS, SAMPLE_INVALID_PS


class TestConfig(Config):
    TESTING = True
    DEBUG = False


@pytest.fixture
def app():
    temp_dir = tempfile.mkdtemp()
    TestConfig.UPLOAD_FOLDER = temp_dir
    app = create_app(TestConfig)
    yield app
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Conversor" in response.data or b"PostScript" in response.data


def test_system_status_api(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "status" in data


def test_convert_missing_file_payload(client):
    response = client.post("/api/convert", data={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
    assert "no se envi" in data["error"].lower()


def test_convert_invalid_extension(client):
    data = {
        "file": (io.BytesIO(b"Hello world"), "document.txt")
    }
    response = client.post("/api/convert", data=data, content_type="multipart/form-data")
    assert response.status_code == 400
    res = response.get_json()
    assert res["success"] is False
    assert "no permitida" in res["error"].lower()


def test_convert_invalid_postscript_content(client):
    data = {
        "file": (io.BytesIO(SAMPLE_INVALID_PS), "corrupted.ps")
    }
    response = client.post("/api/convert", data=data, content_type="multipart/form-data")
    assert response.status_code == 422
    res = response.get_json()
    assert res["success"] is False
    assert "rechazado" in res["error"].lower()


def test_download_nonexistent_file(client):
    response = client.get("/download/non-existent-uuid-12345")
    assert response.status_code == 404
    data = response.get_json()
    assert data["success"] is False


def test_favicon_route(client):
    response = client.get("/favicon.ico")
    assert response.status_code == 200
    assert "svg" in response.content_type
